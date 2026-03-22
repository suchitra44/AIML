#!/usr/bin/env python3
"""
Main roster scheduling solver.
Orchestrates the entire roster generation process using modular components.
"""
from ortools.sat.python import cp_model
from data_loader import load_availability_data
from constraints import create_shift_variables, add_hard_constraints, add_soft_constraints
from output_generator import generate_roster_output
from validation import generate_coverage_validation_report


def solve_roster():
    """
    Main function to solve roster scheduling problem.
    """
    print("🔄 Loading availability data...")
    df = load_availability_data()
    print(f"   Loaded {len(df)} staff members")
    
    print("\n🔨 Building optimization model...")
    model = cp_model.CpModel()
    
    # Create decision variables
    x = create_shift_variables(model, df)
    print(f"   Created {len(x)} shift assignment variables")
    
    # Add hard constraints
    print("\n⚙️  Adding hard constraints...")
    add_hard_constraints(model, x, df)
    
    # Add soft constraints and collect penalties
    print("⚙️  Adding soft constraints...")
    penalties = add_soft_constraints(model, x, df)
    
    # Set objective: minimize penalties
    model.Minimize(sum(penalties))
    
    # Solve
    print("\n🚀 Solving optimization problem...")
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    
    # Process results
    print("\n" + "="*70)
    if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        print("✅ SOLUTION FOUND")
        print("="*70)
        
        roster_df, total_hours, total_cost, output_file = generate_roster_output(solver, x, df)
        
        print(f"\n📄 Roster generated: {output_file}")
        print(f"   📊 Total Weekly Hours: {total_hours:.2f}")
        print(f"   💰 Total Weekly Cost: ${total_cost:.2f}")
        print(f"   👥 Total Shifts Assigned: {len(roster_df)}")
        
    else:
        print("❌ NO FEASIBLE SOLUTION FOUND")
        print("="*70)
        print("\n📊 Analyzing coverage constraints...")
        generate_coverage_validation_report(df)


if __name__ == "__main__":
    solve_roster()
