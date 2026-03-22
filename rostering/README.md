# Roster Scheduling System - Modular Structure

## 📁 File Structure

```
rostering/
├── config.py              # Configuration: shifts, pay rates, staffing rules
├── utils.py               # Helper functions: time conversions
├── data_loader.py         # Load and normalize availability data
├── constraints.py         # All constraint definitions (hard & soft)
├── validation.py          # Coverage validation reports
├── output_generator.py    # Roster formatting and Excel generation
├── roster_solver.py       # Main entry point - orchestrates everything
└── roster_v2.py          # Legacy monolithic version (for reference)
```

## 🎯 Purpose of Each File

### config.py
Contains all business configuration:
- Days of the week
- Shift definitions (times, durations)
- Manager vs crew shifts
- Day demand levels (Red/Yellow/Green)
- Staffing requirements per demand level
- Pay rates and multipliers
- Constraint parameters (max hours, costs, penalties)

**Edit this file to adjust**: shift times, staffing levels, pay rates, demand patterns

### utils.py
Utility functions used across modules:
- `to_hour()`: Convert various time formats to decimal hours
- `hour_to_time()`: Convert decimal hours back to HH:MM format

### data_loader.py
Handles data input:
- Loads staff availability from Excel
- Normalizes column names (handles "Tue" vs "Tues", etc.)
- Standardizes role names ("Manger" → "Manager")
- Supports command-line argument for custom availability file

### constraints.py
Core optimization logic:
- `create_shift_variables()`: Creates decision variables for the model
- `add_hard_constraints()`: Adds mandatory constraints (one shift per day, max hours, cost limits)
- `add_soft_constraints()`: Adds penalty-based constraints (staffing requirements, manager coverage)

**Edit this file to**: add new constraint types, modify business rules

### validation.py
Diagnostic reporting:
- `generate_coverage_validation_report()`: Analyzes why a solution is infeasible
- Shows manager availability by day
- Shows which shifts lack coverage
- Lists crew availability

**Called automatically** when solver fails to find a solution

### output_generator.py
Results formatting:
- `generate_roster_output()`: Converts solver results to structured DataFrame
- Creates Excel file with multiple sheets (Roster, Daily Summary, Weekly Summary)
- Calculates costs and hours

**Edit this file to**: change output format, add new summary sheets

### roster_solver.py
Main orchestrator - **RUN THIS FILE**:
```bash
python roster_solver.py
# or with custom availability file:
python roster_solver.py --availability path/to/file.xlsx
```

## 🚀 Usage

### Basic Usage
```bash
python roster_solver.py
```

### With Custom Availability File
```bash
python roster_solver.py --availability /path/to/custom_availability.xlsx
```

### Output
- **Success**: Creates `generated_roster.xlsx` with complete schedule
- **Failure**: Shows detailed coverage validation report explaining why

## 🔧 Making Changes

### Change Shift Times
Edit [config.py](config.py#L13-L18)

### Change Staffing Requirements
Edit [config.py](config.py#L42-L66)

### Change Pay Rates
Edit [config.py](config.py#L71-L75)

### Adjust Manager Coverage Penalty
Edit [config.py](config.py#L83) - `UNCOVERED_PENALTY`

### Add New Constraints
Edit [constraints.py](constraints.py) - add to `add_hard_constraints()` or `add_soft_constraints()`

## ✅ Benefits of Modular Structure

1. **Easy Configuration**: Change business rules without touching code logic
2. **Clear Separation**: Each file has one clear purpose
3. **Easier Testing**: Can test individual components
4. **Better Maintenance**: Find and fix issues faster
5. **Team Collaboration**: Multiple people can work on different modules
6. **Reusability**: Validation and output modules can be used independently

## 🔄 Migration from roster_v2.py

The new modular system has **identical functionality** to roster_v2.py, just better organized:

| Old (roster_v2.py) | New (Modular) |
|-------------------|---------------|
| All in one file | Separated by concern |
| 500+ lines | ~100 lines per file |
| Hard to navigate | Easy to find things |
| All or nothing testing | Module-level testing |

**roster_v2.py is kept** for backwards compatibility but should not be edited.

## 📊 Dependencies

- `ortools` - Constraint programming solver
- `pandas` - Data manipulation
- `openpyxl` - Excel file generation

Install with:
```bash
pip install ortools pandas openpyxl
```
