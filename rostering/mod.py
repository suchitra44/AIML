from ortools.sat.python import cp_model
import pandas as pd
import argparse
import os
from datetime import datetime, time

# -----------------------------
# PARAMETERS
# -----------------------------

days = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun']

# Crew shifts
shifts = {
    'ShiftA': (5.5, 13.5),
    'ShiftB': (7.0, 14.0),
    'ShiftC': (16.75, 21.5),
}
shift_hours = {
    'ShiftA': 8,
    'ShiftB': 7,
    'ShiftC': 4.75,
}

# Flexible shift (quiet days)
flexible_shift = (8.0, 13.0)
flex_hours = 5

# Manager shifts
manager_shifts = {
    'Morn_Manager': (5.5, 13.5),
    'Aft_Manager': (13.5, 21.5),
}
manager_shift_hours = {
    'Morn_Manager': 8,
    'Aft_Manager': 8,
}

# Demand forecast
day_demand = {
    'Mon': 'Red',
    'Tue': 'Yellow',
    'Wed': 'Red',
    'Thu': 'Green',
    'Fri': 'Red',
    'Sat': 'Yellow',
    'Sun': 'Green'
}

# Pay rates (prototype)
crew_pay_by_age = {
    16: 12.00, 17: 12.50, 18: 13.00, 19: 13.50, 20: 14.00,
    21: 15.00, 22: 16.00, 23: 17.00, 24: 18.00, 25: 19.00
}

manager_pay = 30
manager_weekend_multiplier = {'Sat': 1.2, 'Sun': 1.5}

MAX_WEEKLY_COST = 20000
UNCOVERED_MANAGER_PENALTY = 1_000_000

# -----------------------------
# READ AVAILABILITY
# Use absolute path based on script location
parser = argparse.ArgumentParser()
default_path = os.path.join(os.path.dirname(__file__), "AvailabilityHJ-2.xlsx")
parser.add_argument("--availability", default=default_path)
args = parser.parse_args()

df = pd.read_excel(args.availability)

# Normalize alternate day headers (Tues -> Tue, Thus -> Thu)
alt_day_keys = {
    'Tue': ['Tues'],
    'Thu': ['Thus']
}
rename_map = {}
for d in days:
    alts = [d] + alt_day_keys.get(d, [])
    for suffix in ('start', 'end'):
        canonical = f"{d}_{suffix}"
        if canonical in df.columns:
            continue
        for alt in alts:
            alt_col = f"{alt}_{suffix}"
            if alt_col in df.columns:
                rename_map[alt_col] = canonical
                break
if rename_map:
    df = df.rename(columns=rename_map)
def to_hour(v):
    if pd.isna(v): return None
    if isinstance(v, time):
        return v.hour + v.minute/60
    if isinstance(v, datetime):
        return v.hour + v.minute/60
    if isinstance(v, (int, float)):
        return v * 24 if 0 <= v <= 1 else float(v)
    if isinstance(v, str):
        h, m = v.split(":")
        return int(h) + int(m)/60
    return None

# -----------------------------
# MODEL
# -----------------------------
model = cp_model.CpModel()
x = {}

# -----------------------------
# VARIABLES
# -----------------------------
for _, row in df.iterrows():
    staff, role, age = row['Staff'], row['Role'], row['Age']

    for day in days:
        start = to_hour(row[f"{day}_start"])
        end   = to_hour(row[f"{day}_end"])
        if start is None or end is None:
            continue

        # Crew shifts
        for s, (a, b) in shifts.items():
            if a >= start and b <= end:
                x[(staff, day, s)] = model.NewBoolVar(f"{staff}_{day}_{s}")

        # Flexible shift
        if role == 'Both' and day_demand[day] in ['Yellow','Green']:
            if flexible_shift[0] >= start and flexible_shift[1] <= end:
                x[(staff, day, 'Flex')] = model.NewBoolVar(f"{staff}_{day}_Flex")

        # Manager shifts
        if role == 'Manager':
            for m, (a, b) in manager_shifts.items():
                if a >= start and b <= end:
                    x[(staff, day, m)] = model.NewBoolVar(f"{staff}_{day}_{m}")

# -----------------------------
# ONE SHIFT PER DAY PER STAFF
# -----------------------------
for staff in df['Staff']:
    for day in days:
        vars_today = [v for (s,d,_),v in x.items() if s==staff and d==day]
        if vars_today:
            model.Add(sum(vars_today) <= 1)

# -----------------------------
# MANAGER COVERAGE (SOFT)
# -----------------------------
penalties = []

for day in days:
    for m in manager_shifts:
        vars_m = [v for (s,d,sh),v in x.items() if d==day and sh==m]
        u = model.NewBoolVar(f"Uncovered_{day}_{m}")
        model.Add(sum(vars_m) + u == 1)
        penalties.append(u * UNCOVERED_MANAGER_PENALTY)

# Manager weekly limit
for m in df[df['Role']=='Manager']['Staff']:
    mgr_vars = [v for (s,_,sh),v in x.items() if s==m and sh in manager_shifts]
    if mgr_vars:
        model.Add(sum(mgr_vars) <= 4)

# -----------------------------
# COST CONSTRAINT
# -----------------------------
cost_terms = []

for (staff, day, shift), var in x.items():
    role = df[df['Staff']==staff]['Role'].iloc[0]
    age  = df[df['Staff']==staff]['Age'].iloc[0]

    if shift in manager_shift_hours:
        hours = manager_shift_hours[shift]
        rate = manager_pay * manager_weekend_multiplier.get(day, 1)
    elif shift == 'Flex':
        hours = flex_hours
        rate = crew_pay_by_age.get(age, 18)
    else:
        hours = shift_hours[shift]
        rate = crew_pay_by_age.get(age, 18)

    cost_terms.append(var * int(hours*1000) * int(rate*1000))

model.Add(sum(cost_terms) <= MAX_WEEKLY_COST * 1_000_000)

# -----------------------------
# WEEKLY HOURS (SOFT)
# -----------------------------
hour_penalties = []

for staff in df['Staff']:
    hours = []
    for (s,_,sh),v in x.items():
        if s == staff:
            if sh in manager_shift_hours:
                h = manager_shift_hours[sh]
            elif sh == 'Flex':
                h = flex_hours
            else:
                h = shift_hours[sh]
            hours.append(v * int(h*1000))

    if hours:
        total = sum(hours)
        dev = model.NewIntVar(0, 100_000_000, f"{staff}_hour_dev")
        model.AddAbsEquality(dev, total - 70*1000)
        hour_penalties.append(dev)

model.Minimize(sum(hour_penalties) + sum(penalties))

# -----------------------------
# SOLVE
# -----------------------------
solver = cp_model.CpSolver()
status = solver.Solve(model)

# -----------------------------
# OUTPUT
# -----------------------------
if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
    out = []
    for (s,d,sh),v in x.items():
        if solver.Value(v):
            out.append({'Staff':s,'Day':d,'Shift':sh})
    pd.DataFrame(out).to_excel("generated_roster.xlsx", index=False)
    print("✅ Roster generated: generated_roster.xlsx")
else:
    print("❌ No feasible solution found")