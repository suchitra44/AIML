# Quick Reference Guide

## 🎯 Common Tasks

### Run the Roster Solver
```bash
python roster_solver.py
```

### Change Shift Times
**File:** [config.py](config.py)  
**Lines:** 13-27
```python
shifts = {
    'ShiftA': (5.5, 13.5, 8),    # Change times here
    # ...
}
```

### Change Staffing Requirements
**File:** [config.py](config.py)  
**Lines:** 42-66
```python
staffing_rules = {
    'Red': {
        'ShiftA': {'FOH': 1},    # Change counts here
        # ...
    }
}
```

### Adjust Manager Coverage Enforcement
**File:** [config.py](config.py)  
**Line:** 83
```python
UNCOVERED_PENALTY = 100_000_000  # Higher = more strict
```

### Change Pay Rates
**File:** [config.py](config.py)  
**Lines:** 71-75
```python
crew_pay_by_age = {
    16: 12.00,  # Adjust rates here
    # ...
}
manager_pay = 30  # Manager hourly rate
```

### Change Weekly Hour/Cost Limits
**File:** [config.py](config.py)  
**Lines:** 80-81
```python
MAX_WEEKLY_HOURS = 38
MAX_WEEKLY_COST = 20000
```

## 📊 Understanding Output

### Success Output
```
✅ SOLUTION FOUND
Roster generated: /path/to/generated_roster.xlsx
   📊 Total Weekly Hours: 245.50
   💰 Total Weekly Cost: $4,892.00
   👥 Total Shifts Assigned: 35
```

### Failure Output
```
❌ NO FEASIBLE SOLUTION FOUND
📊 Analyzing coverage constraints...

COVERAGE VALIDATION REPORT
======================================================================
📋 MANAGER AVAILABILITY:
   Total Managers/RMs: 2
   • John: Available 7/7 days (Mon, Tue, Wed, Thu, Fri, Sat, Sun)
   • Sarah: Available 5/7 days (Mon, Wed, Fri, Sat, Sun)

🌅 MORNING MANAGER COVERAGE (Morn_Manager: 5:30-13:30):
   ✗ Mon: 0 manager(s) available (NONE)
   ✓ Tue: 1 manager(s) available (John)
   ...
```

## 🔍 Troubleshooting

### Problem: "No feasible solution found"
**Check:**
1. Coverage validation report (printed automatically)
2. Are managers available for all days?
3. Is weekly cost constraint too tight?
4. Are there enough staff for demand level?

**Solutions:**
- Increase `MAX_WEEKLY_COST` in config.py
- Add more staff or adjust availability
- Reduce staffing requirements for some shifts

### Problem: Manager coverage issues
**Check:**
- `UNCOVERED_PENALTY` value (config.py line 83)
- Manager availability windows in Excel file

**Solutions:**
- Lower penalty if you want more flexibility
- Adjust manager availability times
- Add more managers

### Problem: Cost overruns
**Check:**
- `MAX_WEEKLY_COST` setting
- Pay rates in config.py
- Total hours being scheduled

**Solutions:**
- Increase cost limit
- Adjust pay rates
- Reduce staffing requirements

## 📝 File Summary

| File | Lines | Purpose | Edit Frequency |
|------|-------|---------|----------------|
| config.py | ~100 | Business rules | Often |
| constraints.py | ~230 | Constraint logic | Rarely |
| roster_solver.py | ~50 | Main entry point | Never |
| data_loader.py | ~50 | Data loading | Rarely |
| output_generator.py | ~80 | Output formatting | Sometimes |
| validation.py | ~80 | Diagnostics | Rarely |
| utils.py | ~30 | Helper functions | Never |

## 🎨 Customization Examples

### Add a new shift type
1. Add to `shifts` dict in config.py
2. Update staffing_rules in config.py
3. Constraints will automatically include it

### Change demand levels
1. Update `day_demand` dict in config.py
2. Update staffing_rules if needed

### Add new role type
1. Update staffing_rules in config.py
2. Modify constraint logic in constraints.py if special rules needed

### Adjust penalties
All penalty values are in config.py:
- `UNCOVERED_PENALTY`: Manager coverage (line 83)
- `UNDERSTAFFED_SHIFT_PENALTY`: Shift understaffing (line 87)
- `UNDERSTAFFED_DAY_PENALTY`: Daily minimum (line 88)

## 📚 For More Details

- **Full documentation:** [README.md](README.md)
- **System architecture:** [ARCHITECTURE.md](ARCHITECTURE.md)
- **Legacy code:** [roster_v2.py](roster_v2.py) (for reference only)
