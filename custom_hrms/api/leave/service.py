import math
import frappe
from frappe.utils import flt

from hrms.hr.doctype.department_approver.department_approver import (
    get_approvers,
)

def get_leave_approvers(filters, page=1, page_size=20):
    approvers = list(
        get_approvers(
            txt="",
            doctype="User",
            searchfield="name",
            start=0,
            page_len=999999,
            filters=filters,
        )
    )

    total_approvers = len(approvers)
    total_pages = math.ceil(total_approvers / page_size)

    start = (page - 1) * page_size
    end = start + page_size

    paginated_approvers = approvers[start:end]

    data = [
        {
            "value": approver[0],
            "label": " ".join(filter(None, approver[1:])).strip(),
            "description": approver[0],
        }
        for approver in paginated_approvers
    ]

    return data, total_approvers, total_pages

def get_employee_details_data(employee_id):
    # Fetch core employee information
    employee_info = frappe.db.get_value(
        "Employee", 
        employee_id, 
        ["name", "employee_name", "department", "designation", "status", "company", "date_of_joining"], 
        as_dict=True
    )

    if not employee_info:
        return None

    # Fetch leave balances
    leave_balances_data = frappe.db.sql("""
        SELECT 
            leave_type, 
            COALESCE(SUM(CASE WHEN is_carry_forward = 1 AND leaves > 0 THEN leaves ELSE 0 END), 0) AS opening_balance,
            COALESCE(SUM(CASE WHEN transaction_type = 'Leave Allocation' AND is_carry_forward = 0 AND leaves > 0 THEN leaves ELSE 0 END), 0) AS new_leaves_allocated,
            COALESCE(SUM(CASE WHEN transaction_type = 'Leave Application' AND leaves < 0 THEN ABS(leaves) ELSE 0 END), 0) AS leaves_taken,
            COALESCE(SUM(CASE WHEN is_expired = 1 AND leaves < 0 THEN ABS(leaves) ELSE 0 END), 0) AS leaves_expired,
            COALESCE(SUM(leaves), 0) AS balance
        FROM `tabLeave Ledger Entry`
        WHERE employee = %(employee)s
        GROUP BY leave_type
    """, {"employee": employee_id}, as_dict=True)

    # Fetch recent timesheets
    recent_timesheets = frappe.db.get_all(
        "Timesheet",
        filters={"employee": employee_id, "docstatus": 1},
        fields=["name", "start_date", "end_date", "total_hours", "status"],
        order_by="start_date desc",
        limit=10,
    )

    # Fetch total logged hours
    total_hours_query = frappe.db.sql("""
        SELECT 
            COALESCE(SUM(total_hours), 0) AS total_logged_hours
        FROM `tabTimesheet`
        WHERE employee = %(employee)s
          AND docstatus = 1
    """, {"employee": employee_id}, as_dict=True)
    
    total_logged_hours = total_hours_query[0].total_logged_hours if total_hours_query else 0.0

    # Format and return the combined data
    return {
        "employeeInfo": employee_info,
        "leaveBalances": leave_balances_data,
        "timesheetDetails": {
            "totalLoggedHours": flt(total_logged_hours),
            "recentTimesheets": recent_timesheets
        }
    }