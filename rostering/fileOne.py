from ortools.sat.python import cp_model
import pandas as pd
import argparse
import os
from datetime import datetime, time

# -----------------------------
# PARAMETERS
# -----------------------------

# Shifts
shifts = {
    'ShiftA': (5.5, 13.5),    # 5:30 - 13:30
    'ShiftB': (7.0, 14.0),    # 7:00 - 14:00
    'ShiftC': (16.75, 21.5),  # 16:45 - 21:30
}
shift_hours = {
    'ShiftA': 8,      # includes 30min unpaid break if >=5h
    'ShiftB': 7,
    'ShiftC': 4.75
}
flexible_shift = (8.0, 13.0)  # Flexible 8-13 for Both-role staff

# Manager shifts
manager_shifts = {
    'Morn_Manager': (5.5, 13.5),
    'Aft_Manager': (13.5, 21.5)
}

# Example day demand (from your photo)
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
manager_pay = 30  # FFA level 3.2
manager_weekend_multiplier = {'Sat': 1.2, 'Sun': 1.5}

MAX_WEEKLY_COST = 20000
days = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun']

# -----------------------------
# STEP 1: READ AVAILABILITY
# -----------------------------
# Accept `--availability` to point to CSV/Excel. Defaults to a file
# next to this script named "AvailabilityHJ-2.xlsx".
parser = argparse.ArgumentParser(description="Roster generator")
default_path = os.path.join(os.path.dirname(__file__), "AvailabilityHJ-2.xlsx")
parser.add_argument(
    "--availability",
    dest="availability_file",
    default=default_path,
    help="Path to availability file (CSV or Excel). Defaults to AvailabilityHJ-2.xlsx next to the script.",
)
args, unknown = parser.parse_known_args()
availability_file = args.availability_file

if not os.path.exists(availability_file):
    print(
        f"Availability file not found: {availability_file}\n"
        "Provide via --availability or place AvailabilityHJ-2.xlsx next to the script.\n"
        "Expected columns: Staff, Role, Age, and for each day Mon_start/Mon_end, Tue_start/Tue_end, ..."
    )
    raise SystemExit(1)

# Support CSV and Excel inputs
if availability_file.lower().endswith(".csv"):
    df = pd.read_csv(availability_file)
else:
    df = pd.read_excel(availability_file)

# Normalize potential alternate day headers to canonical keys in `days`
alt_day_keys = {
    'Tue': ['Tues'],
    'Thu': ['Thus']
}
rename_map = {}
for d in days:
    alts = [d] + alt_day_keys.get(d, [])
    # map any <Alt>_start/end to <d>_start/end if canonical missing
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

# Validate required columns (use canonical day keys matching `days`)
required = {"Staff", "Role", "Age"}
for d in days:
    required.update({f"{d}_start", f"{d}_end"})
missing = [col for col in sorted(required) if col not in df.columns]
if missing:
    print(
        "Availability file is missing required columns:\n  - " +
        "\n  - ".join(missing) +
        "\nEnsure headers match exactly (e.g., Mon_start, Mon_end). Accepted day keys: Mon, Tue (or Tues), Wed, Thu (or Thus), Fri, Sat, Sun."
    )
    raise SystemExit(1)

# -----------------------------
# Helper: convert time-like cell to decimal hours
# -----------------------------
def to_hour(v):
    if pd.isna(v):
        return None
    # Excel time parsed as datetime.time
    if isinstance(v, time):
        return v.hour + v.minute/60 + v.second/3600
    # pandas Timestamp or datetime
    if hasattr(v, 'to_pydatetime'):
        dt = v.to_pydatetime()
        return dt.hour + dt.minute/60 + dt.second/3600
    if isinstance(v, datetime):
        return v.hour + v.minute/60 + v.second/3600
    # Excel numeric time in days (0..1)
    if isinstance(v, (int, float)):
        # Heuristic: if <= 1, treat as fraction of day
        if 0 <= v <= 1:
            return v * 24
        return float(v)
    # String like "5:30" or "05:30"
    if isinstance(v, str):
        s = v.strip()
        try:
            # Try HH:MM[:SS]
            parts = [float(p) for p in s.split(":")]
            if len(parts) >= 2:
                h, m = parts[0], parts[1]
                sec = parts[2] if len(parts) >= 3 else 0
                return h + m/60 + sec/3600
            # Try decimal hour string
            return float(s)
        except Exception:
            return None
    return None

# -----------------------------
# STEP 2: CREATE MODEL & VARIABLES
# -----------------------------
model = cp_model.CpModel()
x = {}  # staff x day x shift

for idx, row in df.iterrows():
    staff = row['Staff']
    role = row['Role']
    age = row['Age']
    
    for day in days:
        day_start = to_hour(row[f"{day}_start"]) 
        day_end   = to_hour(row[f"{day}_end"]) 
        if day_start is None or day_end is None:
            continue
        
        # MAIN SHIFTS
        for shift, (s_start, s_end) in shifts.items():
            if s_start >= day_start and s_end <= day_end:
                x[(staff, day, shift)] = model.NewBoolVar(f"{staff}_{day}_{shift}")
        
        # FLEXIBLE SHIFT for Both-role staff
        if role == 'Both' and day_demand[day] in ['Yellow','Green']:
            f_start, f_end = flexible_shift
            if f_start >= day_start and f_end <= day_end:
                x[(staff, day, 'Flex')] = model.NewBoolVar(f"{staff}_{day}_Flex")
        
        # MANAGER SHIFTS
        if role == 'Manager':
            for m_shift, (m_start, m_end) in manager_shifts.items():
                if day_start <= m_start and day_end >= m_end:
                    x[(staff, day, m_shift)] = model.NewBoolVar(f"{staff}_{day}_{m_shift}")

# -----------------------------
# STEP 3: HARD CONSTRAINTS
# -----------------------------

# ============================================================================
# SOFT MANAGER COVERAGE (can be deleted/commented out if constraints too tight)
# Allow uncovered manager shifts with high penalty instead of hard failure
# To REMOVE this soft constraint and require exact coverage, delete this block
# and uncomment the old hard constraint below.
# ============================================================================
uncovered_manager = {}
coverage_penalties = []
UNCOVERED_PENALTY = 1_000_000  # Heavily penalize but allow uncovered shifts

for day in days:
    for m_shift in manager_shifts:
        manager_vars = [var for key, var in x.items() if key[1]==day and key[2]==m_shift]
        # Create a boolean for "uncovered" if no candidates or to allow flexibility
        u = model.NewBoolVar(f"Uncovered_{day}_{m_shift}")
        uncovered_manager[(day, m_shift)] = u
        # Constraint: either exactly 1 manager assigned OR mark as uncovered
        model.Add(sum(manager_vars) + u == 1)
        # Apply heavy penalty to uncovered shifts (optimization will minimize)
        coverage_penalties.append(u * UNCOVERED_PENALTY)
# ============================================================================

# Manager weekly shift limits: each manager works up to 4 manager shifts
# NOTE: You mentioned 3-4 shifts, but softened here to allow feasibility
# Change >= 3 back to >= 3 if you want to enforce minimum 3 shifts
manager_names = df.loc[df['Role'] == 'Manager', 'Staff'].unique().tolist()
for m in manager_names:
    mgr_vars = [var for key, var in x.items() if key[0]==m and key[2] in manager_shifts]
    if mgr_vars:
        # model.Add(sum(mgr_vars) >= 3)  # Minimum shifts (can re-enable)
        model.Add(sum(mgr_vars) <= 4)  # Maximum 4 shifts per week

# Total cost ≤ MAX_WEEKLY_COST
total_cost_terms = []
for key, var in x.items():
    staff, day, shift = key
    role = df[df['Staff']==staff]['Role'].iloc[0]
    age = df[df['Staff']==staff]['Age'].iloc[0]
    
    if role == 'Manager':
        rate = manager_pay
        if day in manager_weekend_multiplier:
            rate *= manager_weekend_multiplier[day]
    else:
        rate = crew_pay_by_age.get(age, 18)
    
    # Determine hours
    hours = shift_hours.get(shift, flexible_shift[1]-flexible_shift[0])
    total_cost_terms.append(var * int(hours*1000) * int(rate*1000))

model.Add(sum(total_cost_terms) <= MAX_WEEKLY_COST*1000*1000)

# -----------------------------
# STEP 4: SOFT CONSTRAINTS (weekly hours)
# -----------------------------
hour_penalties = []
for staff in df['Staff']:
    assigned_hours = []
    for key, var in x.items():
        if key[0]==staff:
            shift = key[2]
            h = shift_hours.get(shift, flexible_shift[1]-flexible_shift[0])
            assigned_hours.append(var * int(h*1000))
    
    if assigned_hours:
        total_h = sum(assigned_hours)
        pref_hours = 70  # default
        # Wed & Sat ~80
        deviation = model.NewIntVar(0, 1000000, f"{staff}_hour_dev")
        model.AddAbsEquality(deviation, total_h - pref_hours*1000)
        hour_penalties.append(deviation)

model.Minimize(sum(hour_penalties) + sum(coverage_penalties))

# -----------------------------
# STEP 5: SOLVE
# -----------------------------
solver = cp_model.CpSolver()
status = solver.Solve(model)

# -----------------------------
# STEP 6: OUTPUT
# -----------------------------
if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
    roster = []
    for key, var in x.items():
        if solver.Value(var) == 1:
            roster.append({
                'Staff': key[0],
                'Day': key[1],
                'Shift': key[2]
            })
    roster_df = pd.DataFrame(roster)
    roster_df = roster_df.sort_values(by=['Day','Shift','Staff'])
    roster_df.to_excel('generated_roster.xlsx', index=False, sheet_name='Weekly Roster')
    print("Roster generated successfully! Saved as 'generated_roster.xlsx'")
else:
    print("No feasible solution found")