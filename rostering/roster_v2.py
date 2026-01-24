from ortools.sat.python import cp_model
import pandas as pd
import argparse
import os
from datetime import datetime, time

# ============================================================================
# PARAMETERS
# ============================================================================
days = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun']

# Shift times (decimal hours)
shifts = {
    'ShiftA': (5.5, 13.5, 8),       # 5:30-13:30, 8 hours
    'ShiftB': (7.0, 14.0, 7),       # 7:00-14:00, 7 hours
    'ShiftC': (16.75, 21.5, 4.75),  # 16:45-21:30, 4.75 hours
    'ShiftD': (14.0, 21.5, 7.5),    # 14:00-21:30, 7.5 hours
}

# Flexible shift for "Both" role
flexible_shift = (8.0, 13.0, 5)  # 8:00-13:00, 5 hours

# Manager shifts (5:30-1:30 and 1:30-9:30)
manager_shifts = {
    'Morn_Manager': (5.5, 13.5, 8),    # 5:30-13:30, 8 hours
    'Aft_Manager': (13.5, 21.5, 8),    # 13:30-21:30, 8 hours
}

# Day demand levels
day_demand = {
    'Mon': 'Red',
    'Tue': 'Yellow',
    'Wed': 'Red',
    'Thu': 'Green',
    'Fri': 'Red',
    'Sat': 'Yellow',
    'Sun': 'Green'
}

# Staffing requirements per shift type
# ShiftA (5:30-13:30): Early crew + Manager
# ShiftB (7:00-14:00): Main morning crew (joins at 7am)
# ShiftC (16:45-21:30): Evening crew
# ShiftD (14:00-21:30): Bridge/afternoon crew
# Aft: Afternoon manager (13:30-21:30)
staffing_rules = {
    'Red': {
        # 5:30 start: 1 crew (manager optional, covered via soft constraint)
        'ShiftA': {'FOH': 1},
        'ShiftB': {'FOH': 2, 'BOH': 2},                   # 7:00 join: 4 more crew
        'ShiftC': {'FOH': 2, 'BOH': 1},                   # 16:45 start
        'ShiftD': {'FOH': 1},                             # 14:00 bridge (single crew)
    },
    'Yellow': {
        # 5:30 start: 1 crew
        'ShiftA': {'FOH': 1},
        'ShiftB': {'FOH': 2, 'BOH': 1},                   # 7:00 join: 3 crew
        'ShiftC': {'FOH': 2, 'BOH': 1},                   # 16:45 start (3 crew)
        'ShiftD': {'FOH': 1, 'BOH': 1},                   # 14:00 bridge (2 crew)
    },
    'Green': {
        # 5:30 start: 1 crew
        'ShiftA': {'FOH': 1},
        'ShiftB': {'FOH': 2, 'BOH': 1},                   # 7:00 join: 3 crew
        'ShiftC': {'FOH': 2, 'BOH': 1},                   # 16:45 start (3 crew)
        'ShiftD': {'FOH': 1, 'BOH': 1},                   # 14:00 bridge (2 crew)
    }
}

# Pay rates
crew_pay_by_age = {
    16: 12.00, 17: 12.50, 18: 13.00, 19: 13.50, 20: 14.00,
    21: 15.00, 22: 16.00, 23: 17.00, 24: 18.00, 25: 19.00
}
manager_pay = 30
manager_weekend_multiplier = {'Sat': 1.2, 'Sun': 1.5}

# Constraints
MAX_WEEKLY_HOURS = 38  # Crew max hours per week
MAX_WEEKLY_COST = 20000
UNCOVERED_PENALTY = 1_000_000
MIN_STAFF_PER_DAY = 10

# Daily hour targets (soft)
RED_HOUR_CAP = 80               # prefer under 80 hours on red days
GREENYELLOW_HOUR_LOWER = 70     # prefer 70-75 hours on green/yellow
GREENYELLOW_HOUR_UPPER = 75
RED_HOUR_PENALTY = 1_000        # weight for each hour (scaled) over cap
GREENYELLOW_HOUR_PENALTY = 1_000

# Helper: convert time to decimal hours
def to_hour(v):
    if pd.isna(v):
        return None
    if isinstance(v, time):
        return v.hour + v.minute/60 + v.second/3600
    if isinstance(v, datetime):
        return v.hour + v.minute/60 + v.second/3600
    if isinstance(v, (int, float)):
        return v * 24 if 0 <= v <= 1 else float(v)
    if isinstance(v, str):
        try:
            parts = [float(p) for p in v.split(":")]
            if len(parts) >= 2:
                return parts[0] + parts[1]/60 + (parts[2]/3600 if len(parts) > 2 else 0)
            return float(v)
        except:
            return None
    return None

# Helper: convert decimal hours to HH:MM
def hour_to_time(h):
    if h is None:
        return "N/A"
    hours = int(h)
    mins = int((h - hours) * 60)
    return f"{hours:02d}:{mins:02d}"

# ============================================================================
# READ AVAILABILITY
# ============================================================================
parser = argparse.ArgumentParser()
default_path = os.path.join(os.path.dirname(__file__), "AvailabilityHJ-3.xlsx")
parser.add_argument("--availability", default=default_path)
args = parser.parse_args()

df = pd.read_excel(args.availability)

# Normalize day headers
alt_day_keys = {'Tue': ['Tues'], 'Thu': ['Thus']}
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

# Standardize "Manger" to "Manager"
df['Role'] = df['Role'].replace('Manger', 'Manager')

# ============================================================================
# MODEL SETUP
# ============================================================================
model = cp_model.CpModel()
x = {}  # (staff, day, shift) -> BoolVar
penalties = []

# Create variables for all valid (staff, day, shift) combinations
for _, row in df.iterrows():
    staff = row['Staff']
    role = row['Role']
    
    for day in days:
        start = to_hour(row[f"{day}_start"])
        end = to_hour(row[f"{day}_end"])
        if start is None or end is None:
            continue
        
        # Managers and RMs can ONLY do manager shifts
        if role in ['Manager', 'Manger', 'RM']:
            for m_shift, (m_start, m_end, _) in manager_shifts.items():
                if start <= m_start and end >= m_end:
                    x[(staff, day, m_shift)] = model.NewBoolVar(f"{staff}_{day}_{m_shift}")
        
        # Non-managers do crew shifts
        else:
            # Regular crew shifts
            for c_shift, (c_start, c_end, _) in shifts.items():
                if start <= c_start and end >= c_end:
                    x[(staff, day, c_shift)] = model.NewBoolVar(f"{staff}_{day}_{c_shift}")
            
            # Flexible shift for "Both" role
            if role == 'Both':
                f_start, f_end, _ = flexible_shift
                if start <= f_start and end >= f_end:
                    x[(staff, day, 'Flex')] = model.NewBoolVar(f"{staff}_{day}_Flex")

# Precheck removed to allow solver to find any feasible roster

# ============================================================================
# HARD CONSTRAINTS
# ============================================================================

# 1. One shift per person per day
for staff in df['Staff']:
    for day in days:
        vars_today = [v for (s, d, _), v in x.items() if s == staff and d == day]
        if vars_today:
            model.Add(sum(vars_today) <= 1)

# 2. Staffing requirements per shift (SOFT CONSTRAINTS with penalties)
# Build role->staff mapping
role_staff = {}
for r in ['FOH', 'BOH', 'Manager', 'Flex', 'Both']:
    role_staff[r] = [s for s in df[df['Role'] == r]['Staff']]

# Penalty weights for understaffing
UNDERSTAFFED_SHIFT_PENALTY = 10000
UNDERSTAFFED_DAY_PENALTY = 5000

for day in days:
    demand_level = day_demand[day]
    required = staffing_rules[demand_level]

    # Helper to get FOH/BOH candidates (now includes 'Both' for all shifts)
    def get_candidates(day, shift, role_type):
        if role_type == 'FOH':
            return [v for (s, d, sh), v in x.items()
                    if d == day and sh == shift and df[df['Staff']==s]['Role'].iloc[0] in ['FOH', 'Both']]
        elif role_type == 'BOH':
            return [v for (s, d, sh), v in x.items()
                    if d == day and sh == shift and df[df['Staff']==s]['Role'].iloc[0] in ['BOH', 'Both']]
        else:
            return []

    # ShiftA (5:30-13:30): Early morning crew + manager
    for role_type, count in required['ShiftA'].items():
        candidates = []
        if role_type == 'Manager':
            candidates = [v for (s, d, sh), v in x.items()
                         if d == day and sh == 'Morn_Manager']
        elif role_type in ['FOH', 'BOH']:
            candidates = get_candidates(day, 'ShiftA', role_type)
        if candidates:
            # Understaffed penalty (soft constraint)
            understaffed = model.NewIntVar(0, count, f"understaffed_{day}_ShiftA_{role_type}")
            model.Add(count - sum(candidates) == understaffed)
            penalties.append(understaffed * UNDERSTAFFED_SHIFT_PENALTY)

    # ShiftB (7:00-14:00): Main morning crew (joins at 7am)
    for role_type, count in required['ShiftB'].items():
        candidates = []
        if role_type in ['FOH', 'BOH']:
            candidates = get_candidates(day, 'ShiftB', role_type)
        if candidates:
            understaffed = model.NewIntVar(0, count, f"understaffed_{day}_ShiftB_{role_type}")
            model.Add(count - sum(candidates) == understaffed)
            penalties.append(understaffed * UNDERSTAFFED_SHIFT_PENALTY)

    # ShiftC (16:45-21:30)
    if 'ShiftC' in required:
        for role_type, count in required['ShiftC'].items():
            candidates = []
            if role_type in ['FOH', 'BOH']:
                candidates = get_candidates(day, 'ShiftC', role_type)
            if candidates:
                understaffed = model.NewIntVar(0, count, f"understaffed_{day}_ShiftC_{role_type}")
                model.Add(count - sum(candidates) == understaffed)
                penalties.append(understaffed * UNDERSTAFFED_SHIFT_PENALTY)

    # ShiftD (14:00-21:30): Bridge shift
    for role_type, count in required['ShiftD'].items():
        candidates = []
        if role_type in ['FOH', 'BOH']:
            candidates = get_candidates(day, 'ShiftD', role_type)
        if candidates:
            understaffed = model.NewIntVar(0, count, f"understaffed_{day}_ShiftD_{role_type}")
            model.Add(count - sum(candidates) == understaffed)
            penalties.append(understaffed * UNDERSTAFFED_SHIFT_PENALTY)

    # SOFT constraint: Minimum staff per day, depends on day type
    if demand_level == 'Red':
        min_staff_req = 14
    elif demand_level == 'Yellow':
        min_staff_req = 12
    elif demand_level == 'Green':
        min_staff_req = 10
    else:
        min_staff_req = MIN_STAFF_PER_DAY
    staff_today = [v for (s, d, sh), v in x.items() if d == day]
    min_staff_short = model.NewIntVar(0, min_staff_req, f"min_staff_short_{day}")
    model.Add(min_staff_req - sum(staff_today) == min_staff_short)
    penalties.append(min_staff_short * UNDERSTAFFED_DAY_PENALTY)

# 3. RM weekly constraint: at most 5 days to avoid infeasibility
for staff in df[df['Role'] == 'RM']['Staff']:
    days_assigned = []
    for (s, d, _), v in x.items():
        if s == staff:
            days_assigned.append(v)
    if days_assigned:
        model.Add(sum(days_assigned) <= 5)

# 4. Crew max 38 hours/week (exclude managers and RMs)
for staff in df[(df['Role'] != 'Manager') & (df['Role'] != 'RM')]['Staff']:
    hours = []
    for (s, _, sh), v in x.items():
        if s == staff:
            if sh in shifts:
                h = shifts[sh][2]
            elif sh == 'Flex':
                h = flexible_shift[2]
            else:
                continue
            hours.append(v * int(h * 1000))
    
    if hours:
        model.Add(sum(hours) <= MAX_WEEKLY_HOURS * 1000)

# 4. Cost constraint
cost_terms = []
for (staff, day, shift), var in x.items():
    role = df[df['Staff'] == staff]['Role'].iloc[0]
    age = df[df['Staff'] == staff]['Age'].iloc[0]
    
    if shift in manager_shifts:
        hours = manager_shifts[shift][2]
        rate = manager_pay * manager_weekend_multiplier.get(day, 1)
    elif shift == 'Flex':
        hours = flexible_shift[2]
        rate = crew_pay_by_age.get(age, 18)
    else:
        hours = shifts[shift][2]
        rate = crew_pay_by_age.get(age, 18)
    
    cost_terms.append(var * int(hours * 1000) * int(rate * 1000))

model.Add(sum(cost_terms) <= MAX_WEEKLY_COST * 1_000_000)

# ============================================================================
# SOFT CONSTRAINTS (for feasibility if coverage gaps exist)
# ============================================================================
# (penalties list already defined above)

# Manager coverage (soft): prefer one morning and one afternoon manager per day
for day in days:
    for m_shift in manager_shifts:
        vars_m = [v for (s, d, sh), v in x.items() if d == day and sh == m_shift]
        u = model.NewBoolVar(f"Uncovered_{day}_{m_shift}")
        if vars_m:
            model.Add(sum(vars_m) + u == 1)
        penalties.append(u * UNCOVERED_PENALTY)

# ============================================================================
# OBJECTIVE
# ============================================================================
model.Minimize(sum(penalties))

# ============================================================================
# SOLVE
# ============================================================================
solver = cp_model.CpSolver()
status = solver.Solve(model)

# ============================================================================
# OUTPUT
# ============================================================================
if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
    # Collect roster
    roster = []
    for (staff, day, shift), var in x.items():
        if solver.Value(var) == 1:
            role = df[df['Staff'] == staff]['Role'].iloc[0]
            age = df[df['Staff'] == staff]['Age'].iloc[0]
            
            if shift in manager_shifts:
                start_h, end_h, hours = manager_shifts[shift]
                rate = manager_pay * manager_weekend_multiplier.get(day, 1)
            elif shift == 'Flex':
                start_h, end_h, hours = flexible_shift
                rate = crew_pay_by_age.get(age, 18)
            else:
                start_h, end_h, hours = shifts[shift]
                rate = crew_pay_by_age.get(age, 18)
            
            cost = hours * rate
            
            roster.append({
                'Staff': staff,
                'Role': role,
                'Day': day,
                'Shift': shift,
                'Start Time': hour_to_time(start_h),
                'End Time': hour_to_time(end_h),
                'Hours': hours,
                'Pay Rate': f"${rate:.2f}",
                'Daily Cost': f"${cost:.2f}"
            })
    
    roster_df = pd.DataFrame(roster)
    roster_df = roster_df.sort_values(by=['Day', 'Start Time', 'Staff']).reset_index(drop=True)
    
    # Calculate daily totals and weekly summary
    daily_summary = roster_df.groupby('Day').agg({
        'Staff': 'count',  # Count staff per day
        'Hours': 'sum',
        'Daily Cost': lambda x: sum(float(c.replace('$', '')) for c in x)
    }).reset_index()
    daily_summary.rename(columns={'Staff': 'Total Staff'}, inplace=True)
    daily_summary['Daily Cost'] = daily_summary['Daily Cost'].apply(lambda x: f"${x:.2f}")
    
    total_hours = roster_df['Hours'].sum()
    total_cost = sum(float(row['Daily Cost'].replace('$', '')) for _, row in roster_df.iterrows())
    
    # Save to Excel (in rostering directory)
    output_file = os.path.join(os.path.dirname(__file__), 'generated_roster.xlsx')
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        roster_df.to_excel(writer, sheet_name='Roster', index=False)
        daily_summary.to_excel(writer, sheet_name='Daily Summary', index=False)
        
        # Add weekly summary
        summary_df = pd.DataFrame([
            {'Metric': 'Total Weekly Hours', 'Value': f"{total_hours:.2f}"},
            {'Metric': 'Total Weekly Cost', 'Value': f"${total_cost:.2f}"}
        ])
        summary_df.to_excel(writer, sheet_name='Weekly Summary', index=False)
    
    print(f"✅ Roster generated: {output_file}")
    print(f"   Total Hours: {total_hours:.2f}")
    print(f"   Total Cost: ${total_cost:.2f}")
else:
    print("❌ No feasible solution found")
