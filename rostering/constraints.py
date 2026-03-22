"""
Constraint definitions for roster scheduling model.
"""
from ortools.sat.python import cp_model
from config import (
    days, shifts, flexible_shift, manager_shifts, day_demand, staffing_rules,
    crew_pay_by_age, manager_pay, manager_weekend_multiplier,
    MAX_WEEKLY_HOURS, MAX_WEEKLY_COST, UNCOVERED_PENALTY,
    UNDERSTAFFED_SHIFT_PENALTY, UNDERSTAFFED_DAY_PENALTY, MIN_STAFF_PER_DAY
)
from utils import to_hour


def create_shift_variables(model, df):
    """
    Create decision variables for all valid (staff, day, shift) combinations.
    
    Args:
        model: CP-SAT model
        df: Staff availability dataframe
        
    Returns:
        dict: Mapping of (staff, day, shift) -> BoolVar
    """
    x = {}
    
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
    
    return x


def add_hard_constraints(model, x, df):
    """
    Add hard constraints that must be satisfied.
    
    Args:
        model: CP-SAT model
        x: Decision variables
        df: Staff availability dataframe
    """
    # 1. One shift per person per day
    for staff in df['Staff']:
        for day in days:
            vars_today = [v for (s, d, _), v in x.items() if s == staff and d == day]
            if vars_today:
                model.Add(sum(vars_today) <= 1)
    
    # 2. RM weekly constraint: at most 5 days
    for staff in df[df['Role'] == 'RM']['Staff']:
        days_assigned = []
        for (s, d, _), v in x.items():
            if s == staff:
                days_assigned.append(v)
        if days_assigned:
            model.Add(sum(days_assigned) <= 5)
    
    # 3. Crew max 38 hours/week (exclude managers and RMs)
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


def add_soft_constraints(model, x, df):
    """
    Add soft constraints (with penalties) for staffing requirements.
    
    Args:
        model: CP-SAT model
        x: Decision variables
        df: Staff availability dataframe
        
    Returns:
        list: Penalty terms for objective function
    """
    penalties = []
    
    # Helper to get FOH/BOH candidates
    def get_candidates(day, shift, role_type):
        if role_type == 'FOH':
            return [v for (s, d, sh), v in x.items()
                    if d == day and sh == shift and df[df['Staff']==s]['Role'].iloc[0] in ['FOH', 'Both']]
        elif role_type == 'BOH':
            return [v for (s, d, sh), v in x.items()
                    if d == day and sh == shift and df[df['Staff']==s]['Role'].iloc[0] in ['BOH', 'Both']]
        else:
            return []
    
    # Staffing requirements per shift
    for day in days:
        demand_level = day_demand[day]
        required = staffing_rules[demand_level]
        
        # ShiftA (5:30-13:30): Early morning crew
        for role_type, count in required['ShiftA'].items():
            candidates = []
            if role_type == 'Manager':
                candidates = [v for (s, d, sh), v in x.items()
                             if d == day and sh == 'Morn_Manager']
            elif role_type in ['FOH', 'BOH']:
                candidates = get_candidates(day, 'ShiftA', role_type)
            if candidates:
                understaffed = model.NewIntVar(0, count, f"understaffed_{day}_ShiftA_{role_type}")
                model.Add(count - sum(candidates) == understaffed)
                penalties.append(understaffed * UNDERSTAFFED_SHIFT_PENALTY)
        
        # ShiftB (7:00-14:00): Main morning crew
        for role_type, count in required['ShiftB'].items():
            candidates = []
            if role_type in ['FOH', 'BOH']:
                candidates = get_candidates(day, 'ShiftB', role_type)
            if candidates:
                understaffed = model.NewIntVar(0, count, f"understaffed_{day}_ShiftB_{role_type}")
                model.Add(count - sum(candidates) == understaffed)
                penalties.append(understaffed * UNDERSTAFFED_SHIFT_PENALTY)
        
        # ShiftC (16:45-21:30): Evening crew
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
        
        # Minimum staff per day
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
    
    # Manager coverage (ultra-high penalty = non-negotiable)
    for day in days:
        for m_shift in manager_shifts:
            vars_m = [v for (s, d, sh), v in x.items() if d == day and sh == m_shift]
            u = model.NewBoolVar(f"Uncovered_{day}_{m_shift}")
            if vars_m:
                model.Add(sum(vars_m) + u == 1)
            penalties.append(u * UNCOVERED_PENALTY)
    
    return penalties
