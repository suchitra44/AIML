"""
Configuration file for roster scheduling system.
Contains all parameters, shift definitions, staffing rules, and constraints.
"""

# ============================================================================
# DAYS & SHIFTS
# ============================================================================
days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

# Shift times (decimal hours): (start, end, duration)
shifts = {
    'ShiftA': (5.5, 13.5, 8),       # 5:30-13:30, 8 hours
    'ShiftB': (7.0, 14.0, 7),       # 7:00-14:00, 7 hours
    'ShiftC': (16.75, 21.5, 4.75),  # 16:45-21:30, 4.75 hours
    'ShiftD': (14.0, 21.5, 7.5),    # 14:00-21:30, 7.5 hours
}

# Flexible shift for "Both" role
flexible_shift = (8.0, 13.0, 5)  # 8:00-13:00, 5 hours

# Manager shifts
manager_shifts = {
    'Morn_Manager': (5.5, 13.5, 8),    # 5:30-13:30, 8 hours
    'Aft_Manager': (13.5, 21.5, 8),    # 13:30-21:30, 8 hours
}

# ============================================================================
# DEMAND & STAFFING RULES
# ============================================================================
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
staffing_rules = {
    'Red': {
        'ShiftA': {'FOH': 1},
        'ShiftB': {'FOH': 2, 'BOH': 2},
        'ShiftC': {'FOH': 2, 'BOH': 1},
        'ShiftD': {'FOH': 1},
    },
    'Yellow': {
        'ShiftA': {'FOH': 1},
        'ShiftB': {'FOH': 2, 'BOH': 1},
        'ShiftC': {'FOH': 2, 'BOH': 1},
        'ShiftD': {'FOH': 1, 'BOH': 1},
    },
    'Green': {
        'ShiftA': {'FOH': 1},
        'ShiftB': {'FOH': 2, 'BOH': 1},
        'ShiftC': {'FOH': 2, 'BOH': 1},
        'ShiftD': {'FOH': 1, 'BOH': 1},
    }
}

# ============================================================================
# PAY RATES
# ============================================================================
crew_pay_by_age = {
    16: 12.00, 17: 12.50, 18: 13.00, 19: 13.50, 20: 14.00,
    21: 15.00, 22: 16.00, 23: 17.00, 24: 18.00, 25: 19.00
}
manager_pay = 30
manager_weekend_multiplier = {'Sat': 1.2, 'Sun': 1.5}

# ============================================================================
# CONSTRAINTS
# ============================================================================
MAX_WEEKLY_HOURS = 38  # Crew max hours per week
MAX_WEEKLY_COST = 20000
UNCOVERED_PENALTY = 100_000_000  # Ultra-high penalty for non-negotiable manager coverage
MIN_STAFF_PER_DAY = 10

# Penalty weights
UNDERSTAFFED_SHIFT_PENALTY = 10000
UNDERSTAFFED_DAY_PENALTY = 5000

# Daily hour targets (soft)
RED_HOUR_CAP = 80
GREENYELLOW_HOUR_LOWER = 70
GREENYELLOW_HOUR_UPPER = 75
RED_HOUR_PENALTY = 1_000
GREENYELLOW_HOUR_PENALTY = 1_000
