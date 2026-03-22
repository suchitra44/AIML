"""
Output generation and formatting for roster scheduling.
"""
import pandas as pd
import os
from config import shifts, flexible_shift, manager_shifts, crew_pay_by_age, manager_pay, manager_weekend_multiplier
from utils import hour_to_time


def generate_roster_output(solver, x, df, output_dir=None):
    """
    Generate roster output from solver results and save to Excel.
    
    Args:
        solver: Solved CP-SAT solver
        x: Decision variables
        df: Staff availability dataframe
        output_dir: Directory to save output (defaults to script directory)
        
    Returns:
        tuple: (roster_df, total_hours, total_cost, output_file)
    """
    # Collect roster data
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
        'Staff': 'count',
        'Hours': 'sum',
        'Daily Cost': lambda x: sum(float(c.replace('$', '')) for c in x)
    }).reset_index()
    daily_summary.rename(columns={'Staff': 'Total Staff'}, inplace=True)
    daily_summary['Daily Cost'] = daily_summary['Daily Cost'].apply(lambda x: f"${x:.2f}")
    
    total_hours = roster_df['Hours'].sum()
    total_cost = sum(float(row['Daily Cost'].replace('$', '')) for _, row in roster_df.iterrows())
    
    # Determine output directory
    if output_dir is None:
        output_dir = os.path.dirname(__file__)
    
    # Save to Excel
    output_file = os.path.join(output_dir, 'generated_roster.xlsx')
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        roster_df.to_excel(writer, sheet_name='Roster', index=False)
        daily_summary.to_excel(writer, sheet_name='Daily Summary', index=False)
        
        # Add weekly summary
        summary_df = pd.DataFrame([
            {'Metric': 'Total Weekly Hours', 'Value': f"{total_hours:.2f}"},
            {'Metric': 'Total Weekly Cost', 'Value': f"${total_cost:.2f}"}
        ])
        summary_df.to_excel(writer, sheet_name='Weekly Summary', index=False)
    
    return roster_df, total_hours, total_cost, output_file
