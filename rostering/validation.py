"""
Validation and reporting functions for roster scheduling.
"""
from config import days, manager_shifts
from utils import to_hour


def generate_coverage_validation_report(df):
    """
    Analyze and report potential coverage issues when solution is infeasible.
    
    Args:
        df: Staff availability dataframe
    """
    print("\n" + "="*70)
    print("COVERAGE VALIDATION REPORT")
    print("="*70)
    
    # Check manager availability
    managers = df[df['Role'].isin(['Manager', 'RM'])]
    print(f"\n📋 MANAGER AVAILABILITY:")
    print(f"   Total Managers/RMs: {len(managers)}")
    
    if len(managers) == 0:
        print("   ⚠️  WARNING: No managers available at all!")
        return
    
    manager_availability = {}
    for _, manager in managers.iterrows():
        staff = manager['Staff']
        available_days = []
        for day in days:
            start = to_hour(manager[f"{day}_start"])
            end = to_hour(manager[f"{day}_end"])
            if start is not None and end is not None:
                available_days.append(day)
        manager_availability[staff] = available_days
        print(f"   • {staff}: Available {len(available_days)}/7 days ({', '.join(available_days) if available_days else 'NONE'})")
    
    # Check morning manager coverage
    print(f"\n🌅 MORNING MANAGER COVERAGE (Morn_Manager: 5:30-13:30):")
    morn_start, morn_end, _ = manager_shifts['Morn_Manager']
    morning_capable = []
    for staff, avail_days in manager_availability.items():
        manager_row = df[df['Staff'] == staff].iloc[0]
        for day in avail_days:
            start = to_hour(manager_row[f"{day}_start"])
            end = to_hour(manager_row[f"{day}_end"])
            if start <= morn_start and end >= morn_end:
                morning_capable.append((staff, day))
    
    print(f"   Total capable assignments: {len(morning_capable)}")
    for day in days:
        day_capable = [s for s, d in morning_capable if d == day]
        status_icon = "✓" if day_capable else "✗"
        print(f"   {status_icon} {day}: {len(day_capable)} manager(s) available ({', '.join(day_capable) if day_capable else 'NONE'})")
    
    # Check afternoon manager coverage
    print(f"\n🌆 AFTERNOON MANAGER COVERAGE (Aft_Manager: 13:30-21:30):")
    aft_start, aft_end, _ = manager_shifts['Aft_Manager']
    afternoon_capable = []
    for staff, avail_days in manager_availability.items():
        manager_row = df[df['Staff'] == staff].iloc[0]
        for day in avail_days:
            start = to_hour(manager_row[f"{day}_start"])
            end = to_hour(manager_row[f"{day}_end"])
            if start <= aft_start and end >= aft_end:
                afternoon_capable.append((staff, day))
    
    print(f"   Total capable assignments: {len(afternoon_capable)}")
    for day in days:
        day_capable = [s for s, d in afternoon_capable if d == day]
        status_icon = "✓" if day_capable else "✗"
        print(f"   {status_icon} {day}: {len(day_capable)} manager(s) available ({', '.join(day_capable) if day_capable else 'NONE'})")
    
    # Check crew availability for staffing requirements
    print(f"\n👥 CREW AVAILABILITY:")
    for role in ['FOH', 'BOH']:
        crew = df[df['Role'] == role]
        print(f"   {role}: {len(crew)} staff")
        for _, person in crew.iterrows():
            available_days = sum(1 for day in days if to_hour(person[f"{day}_start"]) is not None)
            print(f"      • {person['Staff']}: Available {available_days}/7 days")
    
    print("\n" + "="*70 + "\n")
