from datetime import datetime, date
import csv
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# datetime: This module helps us work with dates and times
# - datetime: For working with both date and time together
# - date: For working with just dates (year, month, day)
# 
# csv: This module helps us read CSV (Comma Separated Values) files
#
# smtplib: Sends emails using SMTP (Simple Mail Transfer Protocol)
# MIMEText: Creates the email message text content
# MIMEMultipart: Allows email with multiple parts (subject, body, etc.)
# 
# WHY: We need to compare today's date with birthdays, and calculate ages


def load_staff_data(filename):
    """
    Load staff names and birthdays from a CSV file
    
    HOW IT WORKS:
    1. Opens the CSV file
    2. Reads each row (Name, Birthday)
    3. Converts birthday string to a date object
    4. Stores in a list of dictionaries
    
    WHY THIS CODE:
    - csv.DictReader: Automatically reads the first row as column headers
      and creates a dictionary for each row. Makes it easy to access data
      by column name instead of position.
    - datetime.strptime: Converts text like "1995-01-24" into a real date object
      Format "%Y-%m-%d" means Year-Month-Day (2024-01-24)
    - List of dictionaries: Easy to loop through later when checking birthdays
    
    Returns: List of staff with their info
    Example: [{'name': 'John', 'birthday': date(1995, 1, 24)}, ...]
    """
    staff_list = []
    
    with open(filename, 'r') as file:
        # DictReader treats first row as headers (Name, Birthday)
        csv_reader = csv.DictReader(file)
        
        for row in csv_reader:
            # Each row is a dictionary: {'Name': 'John', 'Birthday': '1995-01-24'}
            staff = {
                'name': row['Name'],
                # Convert text birthday to actual date object
                'birthday': datetime.strptime(row['Birthday'], '%Y-%m-%d').date()
            }
            staff_list.append(staff)
    
    return staff_list


def check_birthdays_today(staff_list):
    """
    Check which staff members have birthdays today
    
    HOW IT WORKS:
    1. Get today's date
    2. Loop through all staff
    3. Compare month and day (ignore year!) with today
    4. Collect matches in a list
    
    WHY THIS CODE:
    - date.today(): Gets today's date from your computer
    - .month and .day: Extract just the month and day parts
      Example: If birthday is 1995-01-24, we only care about 01-24
      We DON'T compare the year because birthdays repeat every year!
    - List comprehension: A compact way to filter a list
      [item for item in list if condition]
    
    WHY NOT COMPARE YEARS?
    - If someone was born in 1995-01-24, their birthday is EVERY January 24
    - We only check if today's month and day match the birthday's month and day
    
    Returns: List of staff with birthdays today
    """
    today = date.today()
    
    # Find all staff whose birthday month and day match today
    birthdays_today = [
        staff for staff in staff_list 
        if staff['birthday'].month == today.month 
        and staff['birthday'].day == today.day
    ]
    
    return birthdays_today


def calculate_age(birth_date):
    """
    Calculate a person's current age from their birth date
    
    HOW IT WORKS:
    1. Get today's date
    2. Subtract birth year from current year
    3. Check if birthday has happened this year yet
    4. If not, subtract 1 from age
    
    WHY THIS CODE:
    - Simple subtraction: 2026 - 1995 = 31
    - But wait! If birthday hasn't happened yet this year, they're still 30
    - We check: Has (today's month, day) passed (birthday's month, day)?
    - If not yet, subtract 1
    
    EXAMPLE:
    - Born: 1995-03-15 (March 15, 1995)
    - Today: 2026-01-24 (January 24, 2026)
    - Math: 2026 - 1995 = 31
    - Check: Is Jan 24 >= March 15? NO! Birthday hasn't happened yet
    - Real age: 31 - 1 = 30 years old
    
    WHY IMPORTANT FOR ROSTERING:
    - Age affects hourly rate/cost
    - Age updates automatically on birthday
    - You can use this in your roster system to update worker cost!
    
    Returns: Age as integer
    """
    today = date.today()
    
    # Calculate age by subtracting years
    age = today.year - birth_date.year
    
    # Check if birthday hasn't happened yet this year
    # Compare (month, day) tuple: (1, 24) < (3, 15) means birthday is later
    if (today.month, today.day) < (birth_date.month, birth_date.day):
        age -= 1  # Subtract 1 because birthday hasn't happened yet
    
    return age


def send_email_reminder(birthday_staff, sender_email, sender_password, recipient_email):
    """
    Send an email reminder about today's birthdays
    
    HOW IT WORKS:
    1. Create the email message with subject and body
    2. Connect to Gmail's email server
    3. Login with your credentials
    4. Send the email
    5. Close the connection
    
    WHY THIS CODE:
    - MIMEMultipart: Creates an email with multiple parts (subject, body, attachments)
    - MIMEText: Converts text into proper email format
    - smtplib.SMTP: Connects to email server (Gmail uses smtp.gmail.com on port 587)
    - TLS encryption: Keeps your email secure during sending
    - login(): Authenticates you with Gmail
    - sendmail(): Actually sends the email
    
    IMPORTANT - Gmail Setup:
    You need an "App Password" (NOT your regular Gmail password):
    1. Go to Google Account settings
    2. Enable 2-Factor Authentication
    3. Go to Security > App Passwords
    4. Generate password for "Mail"
    5. Use that 16-character password here
    
    WHY APP PASSWORD?
    - Google blocks regular passwords for security
    - App passwords are specific to each application
    - If compromised, you can revoke just that password
    
    Parameters:
    - birthday_staff: List of staff with birthdays today
    - sender_email: Your Gmail address (example@gmail.com)
    - sender_password: Your Gmail App Password (16 characters)
    - recipient_email: Where to send the reminder (can be same as sender)
    """
    
    # If no birthdays, don't send email
    if not birthday_staff:
        print("No birthdays today - no email sent.")
        return
    
    # Create email message
    message = MIMEMultipart()
    message['From'] = sender_email
    message['To'] = recipient_email
    message['Subject'] = f"🎂 Birthday Reminder - {date.today().strftime('%B %d, %Y')}"
    
    # Build email body with all birthday people
    body = "Birthday Reminders for Today:\n\n"
    for staff in birthday_staff:
        age = calculate_age(staff['birthday'])
        body += f"🎉 {staff['name']} - Turning {age} years old today!\n"
        body += f"   Born: {staff['birthday'].strftime('%B %d, %Y')}\n\n"
    
    body += "\nDon't forget to wish them a happy birthday! 🎈"
    
    # Attach body to email
    message.attach(MIMEText(body, 'plain'))
    
    try:
        # Connect to Gmail's SMTP server
        # smtp.gmail.com is Google's email server, port 587 is for TLS encryption
        server = smtplib.SMTP('smtp.gmail.com', 587)
        
        # Start TLS encryption (secure connection)
        server.starttls()
        
        # Login to your email account
        server.login(sender_email, sender_password)
        
        # Send the email
        server.sendmail(sender_email, recipient_email, message.as_string())
        
        # Close connection
        server.quit()
        
        print(f"✓ Email sent successfully to {recipient_email}")
        
    except Exception as e:
        print(f"✗ Error sending email: {e}")
        print("Check your email and app password settings.")


def main():
    """
    Main function - runs the entire birthday reminder system
    
    HOW IT WORKS:
    1. Set up email configuration (YOUR INFO HERE!)
    2. Load staff data from CSV file
    3. Check who has birthdays today
    4. Send email reminder if anyone has a birthday
    
    WHY THIS STRUCTURE:
    - main() is the entry point - it orchestrates everything
    - Calls all other functions in the right order
    - Separates configuration from logic (easy to modify)
    - if __name__ == "__main__": ensures this only runs when you execute
      the file directly, not when you import it
    
    TO USE THIS PROGRAM:
    1. Replace YOUR_EMAIL@gmail.com with your Gmail address
    2. Replace YOUR_APP_PASSWORD with your 16-character Gmail App Password
    3. Replace RECIPIENT_EMAIL with where you want reminders sent
    4. Update the CSV filename if different
    5. Run: python birthday_Reminder.py
    """
    
    # ============ CONFIGURATION - SET VIA ENV VARS! ============
    # Keep secrets out of source control; load from environment instead.
    SENDER_EMAIL = os.getenv("BIRTHDAY_SENDER_EMAIL")
    SENDER_PASSWORD = os.getenv("BIRTHDAY_SENDER_PASSWORD")
    RECIPIENT_EMAIL = os.getenv("BIRTHDAY_RECIPIENT_EMAIL")
    STAFF_FILE = os.getenv("BIRTHDAY_STAFF_FILE", "staff_birthdays.csv")
    # ============================================================
    # Basic validation so the scheduled job fails loudly if misconfigured.
    if not all([SENDER_EMAIL, SENDER_PASSWORD, RECIPIENT_EMAIL]):
        print("✗ Missing email configuration. Set BIRTHDAY_SENDER_EMAIL, "
              "BIRTHDAY_SENDER_PASSWORD, and BIRTHDAY_RECIPIENT_EMAIL.")
        return
    
    print("=" * 50)
    print("🎂 Birthday Reminder System")
    print(f"📅 Checking birthdays for: {date.today().strftime('%B %d, %Y')}")
    print("=" * 50)
    
    # Step 1: Load staff data
    print("\n1. Loading staff data...")
    try:
        staff_list = load_staff_data(STAFF_FILE)
        print(f"   ✓ Loaded {len(staff_list)} staff members")
    except FileNotFoundError:
        print(f"   ✗ Error: Could not find '{STAFF_FILE}'")
        return
    except Exception as e:
        print(f"   ✗ Error loading file: {e}")
        return
    
    # Step 2: Check for today's birthdays
    print("\n2. Checking for birthdays today...")
    birthdays_today = check_birthdays_today(staff_list)
    
    if birthdays_today:
        print(f"   🎉 Found {len(birthdays_today)} birthday(s) today!")
        for staff in birthdays_today:
            age = calculate_age(staff['birthday'])
            print(f"      • {staff['name']} - Turning {age} years old")
    else:
        print("   No birthdays today.")
    
    # Step 3: Send email reminder
    print("\n3. Sending email reminder...")
    send_email_reminder(birthdays_today, SENDER_EMAIL, SENDER_PASSWORD, RECIPIENT_EMAIL)
    
    print("\n" + "=" * 50)
    print("✓ Birthday check complete!")
    print("=" * 50)


# This runs when you execute the file directly
# WHY: Allows you to import functions from this file without auto-running main()
if __name__ == "__main__":
    main()
