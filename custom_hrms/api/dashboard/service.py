import math
import frappe
from frappe.utils import flt, nowdate, getdate, add_months, get_first_day, get_last_day, nowdate
from datetime import date


def get_employee_status_counts():
    company = frappe.defaults.get_user_default("Company") or frappe.get_default("Company")
    today = nowdate()

    total_active = frappe.db.count(
        "Employee", 
        filters={
            "status": "Active", 
            "company": company
        }
    )

    total_inactive = frappe.db.count(
        "Employee", 
        filters={
            "status": ["!=", "Active"], 
            "company": company
        }
    )

    leaves_today = frappe.get_all(
        "Leave Application",
        filters={
            "docstatus": 1,
            "status": "Approved",
            "company": company,
            "from_date": ["<=", today],
            "to_date": [">=", today]
        },
        fields=["employee"]
    )
    
    on_leave_employees = set([leave.employee for leave in leaves_today])
    on_leave_count = len(on_leave_employees)

    active_working = max(0, total_active - on_leave_count)

    total_leaves = frappe.db.count(
        "Leave Application",
        filters={
            "company": company,
            "docstatus": ["<", 2]  
        }
    )

    total_leave_types = frappe.db.count("Leave Type")
    attended_today = frappe.db.get_list(
        "Attendance",
        filters={
            "attendance_date": today,
            "docstatus": 1,
            "company": company
        },
        fields=["employee", "status"],
    )

    attended_set = set([a.employee for a in attended_today])

    present_today = sum(1 for a in attended_today if a.status == "Present")
    wfh_today = sum(1 for a in attended_today if a.status == "Work From Home")
    half_day_today = sum(1 for a in attended_today if a.status == "Half Day")

    all_active_employees = frappe.db.get_list(
        "Employee",
        filters={"status": "Active", "company": company},
        fields=["name"],
    )

    all_active_set = set([e.name for e in all_active_employees])

    # Effectively absent = active, no attendance record today, not on leave
    effectively_absent = all_active_set - attended_set - on_leave_employees
    absent_today = len(effectively_absent)

    pending_leaves = frappe.db.count(
        "Leave Application",
        filters={
            "company": company,
            "status": "Open",
            "docstatus": 0
        }
    )
    approved_leaves = frappe.db.count(
        "Leave Application",
        filters={
            "company": company,
            "status": "Approved",
            "docstatus": 1
        }
    )
    rejected_leaves = frappe.db.count(
        "Leave Application",
        filters={
            "company": company,
            "status": "Rejected",
            "docstatus": 1
        }
    )
    # --- Upcoming Birthdays Logic ---
    birthdays = frappe.db.get_all(
        "Employee",
        filters={
            "status": "Active",
            "company": company,
            "date_of_birth": ["is", "set"]
        },
        fields=["employee_name", "date_of_birth"],
    )

    today_date = getdate(nowdate())
    upcoming_birthdays_list = []

    for emp in birthdays:
        dob = getdate(emp.date_of_birth)
        next_birthday = date(
            today_date.year,
            dob.month,
            dob.day    
        )

        if next_birthday < today_date:
            next_birthday = date(
                today_date.year + 1,
                dob.month,
                dob.day
            )
        
        days_left = (next_birthday - today_date).days

        upcoming_birthdays_list.append({
            "employeeName": emp.employee_name,
            "dateOfBirth": str(emp.date_of_birth),
            "daysLeft": days_left
        })

    upcoming_birthdays_list.sort(key=lambda x: x["daysLeft"])

    return {
        "total_active": total_active,
        "active_working": active_working,
        "on_leave": on_leave_count,
        "inactive": total_inactive,
        "total_leaves": total_leaves,
        "total_leave_types": total_leave_types,
        "approved_leaves": approved_leaves,
        "rejected_leaves": rejected_leaves,
        "pending_leaves": pending_leaves, 
        "present_today": present_today,
        "wfh_today": wfh_today,
        "half_day_today": half_day_today,
        "absent_today": absent_today,
        "upcoming_birthdays": upcoming_birthdays_list[:4]
    }

def get_hr_dashboard_data(year=None):
    # Default to the current year if no year is provided in the API call
    if not year:
        year = getdate(nowdate()).year

    # 1. Query Department Wise Payroll (filtered by year)
    # Assuming 'start_date' dictates the year of the salary slip
    payroll_data = frappe.db.sql("""
        SELECT 
            department, 
            SUM(base_net_pay) AS `base net pay`
        FROM 
            `tabSalary Slip`
        WHERE 
            docstatus IN (0, 1) /* <--- Updated line: Includes Drafts (0) and Submitted (1) */
            AND department IS NOT NULL
            AND YEAR(start_date) = %(year)s
        GROUP BY 
            department
    """, {"year": year}, as_dict=True)

    # 2. Query Attendance Pattern (filtered by year)
    attendance_raw = frappe.db.sql("""
        SELECT 
            status, 
            COUNT(name) AS count
        FROM 
            `tabAttendance`
        WHERE 
            docstatus = 1
            AND YEAR(attendance_date) = %(year)s
        GROUP BY 
            status
    """, {"year": year}, as_dict=True)

    # Format Attendance Pattern
    attendance_pattern = {
        "Present": 0,
        "Absent": 0,
        "Late": 0
    }
    
    for row in attendance_raw:
        if row.status in attendance_pattern:
            attendance_pattern[row.status] = row.count

    return payroll_data, attendance_pattern

def get_employee_trend_data(year=None, visible_months=6):
    # Set default values if not provided
    if not year:
        year = getdate(nowdate()).year
    
    year = int(year)
    visible_months = int(visible_months)

    # Determine the anchor date. 
    # If checking the current year, end at the current month.
    # If checking a past year, end at December of that year.
    current_date = getdate(nowdate())
    if year == current_date.year:
        base_date = current_date
    else:
        base_date = getdate(f"{year}-12-31")

    # Initialize data structures
    trend = []
    summary = {"hired": 0, "resigned": 0, "fired": 0, "net_growth": 0}
    month_buckets = []

    # 1. Build the timeline buckets for the requested visible months
    for i in range(visible_months - 1, -1, -1):
        target_month = add_months(base_date, -i)
        month_buckets.append({
            "month_name": target_month.strftime("%B"),
            "start": get_first_day(target_month),
            "end": get_last_day(target_month),
            "hired": 0,
            "resigned": 0,
            "fired": 0
        })

    # Define the absolute minimum and maximum dates for our ORM queries
    min_date = month_buckets[0]["start"]
    max_date = month_buckets[-1]["end"]

    # 2. ORM Query: Fetch all employees hired in this timeframe
    hired_employees = frappe.get_all(
        "Employee",
        filters={"date_of_joining": ["between", [min_date, max_date]]},
        fields=["date_of_joining"]
    )

    # 3. ORM Query: Fetch all employees who left/resigned/fired in this timeframe
    left_employees = frappe.get_all(
        "Employee",
        filters={
            "relieving_date": ["between", [min_date, max_date]],
            "status": ["in", ["Left", "Resigned", "Fired"]]
        },
        fields=["relieving_date", "status"]
    )

    # 4. Populate the buckets with the queried data
    for bucket in month_buckets:
        b_start = bucket["start"]
        b_end = bucket["end"]

        # Count hires for this month
        bucket["hired"] = sum(
            1 for emp in hired_employees 
            if b_start <= getdate(emp.date_of_joining) <= b_end
        )

        # Count resignations/terminations for this month based on status
        for emp in left_employees:
            if b_start <= getdate(emp.relieving_date) <= b_end:
                status = (emp.status or "").lower()
                if status == "fired":
                    bucket["fired"] += 1
                else:
                    # Default standard 'Left' or explicit 'Resigned' to the resigned bucket
                    bucket["resigned"] += 1

        # Aggregate into summary
        summary["hired"] += bucket["hired"]
        summary["resigned"] += bucket["resigned"]
        summary["fired"] += bucket["fired"]

        # Format for final JSON trend array
        trend.append({
            "month": bucket["month_name"],
            "hired": bucket["hired"],
            "resigned": bucket["resigned"],
            "fired": bucket["fired"]
        })

    # Calculate net growth
    summary["net_growth"] = summary["hired"] - (summary["resigned"] + summary["fired"])

    filter_data = {
        "view_type": "monthly",
        "year": year,
        "visible_months": visible_months
    }

    return filter_data, summary, trend