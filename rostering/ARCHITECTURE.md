# System Architecture

## Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                         roster_solver.py                        │
│                      (Main Orchestrator)                        │
└────────────┬───────────────────────────────────────────┬────────┘
             │                                           │
             ▼                                           ▼
    ┌────────────────┐                          ┌────────────────┐
    │ data_loader.py │                          │ validation.py  │
    │   Load Excel   │                          │  Diagnostics   │
    └────────┬───────┘                          └────────────────┘
             │
             ▼
    ┌────────────────┐
    │   config.py    │◄─────────────┐
    │  Parameters    │               │
    │   & Rules      │               │
    └────────┬───────┘               │
             │                       │
             ▼                       │
    ┌────────────────┐               │
    │ constraints.py │───────────────┤
    │  Build Model   │               │
    └────────┬───────┘               │
             │                       │
             ▼                       │
    ┌────────────────┐               │
    │  OR-Tools      │               │
    │    Solver      │               │
    └────────┬───────┘               │
             │                       │
             ├─────► Success? ───────┤
             │          │            │
             │          ▼            ▼
             │   ┌─────────────┐  ┌────────────┐
             │   │ output_     │  │ validation │
             │   │ generator   │  │   report   │
             │   └─────────────┘  └────────────┘
             │          │
             │          ▼
             │   generated_roster.xlsx
             │
             └───► utils.py (used by all modules)
                   - to_hour()
                   - hour_to_time()
```

## Module Dependencies

```
roster_solver.py
    ├── imports: data_loader, constraints, output_generator, validation
    │
    ├─► data_loader.py
    │       ├── imports: config (days), utils (to_hour)
    │       └── outputs: DataFrame
    │
    ├─► constraints.py
    │       ├── imports: config (all params), utils (to_hour)
    │       └── creates: model, variables, constraints
    │
    ├─► output_generator.py
    │       ├── imports: config (shifts, pay), utils (hour_to_time)
    │       └── outputs: Excel file
    │
    └─► validation.py
            ├── imports: config (days, shifts), utils (to_hour)
            └── outputs: Console report

config.py
    └── No imports (pure data)

utils.py
    └── imports: pandas, datetime
```

## Execution Flow

```
1. START
   │
2. Load availability data
   │  [data_loader.py]
   │  - Read Excel file
   │  - Normalize columns
   │  - Return DataFrame
   │
3. Build optimization model
   │  [constraints.py]
   │  - Create shift variables
   │  - Add hard constraints
   │  - Add soft constraints (with penalties)
   │
4. Solve model
   │  [OR-Tools CP-SAT Solver]
   │  - Minimize penalties
   │  - Find optimal assignment
   │
5. Check status
   │
   ├─► FEASIBLE/OPTIMAL
   │   │
   │   └─► Generate output
   │       [output_generator.py]
   │       - Format roster data
   │       - Calculate summaries
   │       - Save to Excel
   │       - Print success message
   │
   └─► INFEASIBLE
       │
       └─► Generate validation report
           [validation.py]
           - Analyze manager coverage
           - Check crew availability
           - Show gaps by day
           - Print diagnostic report
```

## Configuration Flow

```
┌──────────────────────────────────────────────────┐
│            config.py (Single Source)             │
│                                                  │
│  • Days                                          │
│  • Shifts (crew + manager)                       │
│  • Day demand (Red/Yellow/Green)                 │
│  • Staffing rules                                │
│  • Pay rates                                     │
│  • Constraints (hours, cost, penalties)          │
└──────────────────────────────────────────────────┘
                    │
        ┌───────────┼───────────┬───────────┐
        │           │           │           │
        ▼           ▼           ▼           ▼
   data_loader  constraints  output    validation
                                       
   → All modules read from same config
   → Changes propagate automatically
   → No duplication of parameters
```
