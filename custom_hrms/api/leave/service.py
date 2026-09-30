import math
import frappe
from frappe.utils import flt, nowdate, getdate, add_months, get_first_day, get_last_day, nowdate

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
            L.leave_type, 
            COALESCE(SUM(CASE WHEN L.is_carry_forward = 1 AND L.leaves > 0 THEN L.leaves ELSE 0 END), 0) AS opening_balance,
            COALESCE(SUM(CASE WHEN L.transaction_type = 'Leave Allocation' AND L.is_carry_forward = 0 AND L.leaves > 0 THEN L.leaves ELSE 0 END), 0) AS new_leaves_allocated,
            COALESCE(SUM(CASE WHEN L.transaction_type = 'Leave Application' AND L.leaves < 0 THEN ABS(L.leaves) ELSE 0 END), 0) AS leaves_taken,
            COALESCE(SUM(CASE WHEN L.is_expired = 1 AND L.leaves < 0 THEN ABS(L.leaves) ELSE 0 END), 0) AS leaves_expired,
            COALESCE(SUM(leaves), 0) AS balance,
            T.include_holiday
        FROM `tabLeave Ledger Entry` L, `tabLeave Type` T
        WHERE L.employee = %(employee)s
        AND L.leave_type = T.name
        GROUP BY L.leave_type
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


def get_all_employee_leave_details(filters=None, page=1, page_size=20):
    filters = filters or {}

    # ---------------------------------------------------------
    # 1. Build Employee filters
    # ---------------------------------------------------------

    employee_filters = {}

    if filters.get("employee"):
        employee_filters["name"] = filters.get("employee")

    if filters.get("department"):
        employee_filters["department"] = filters.get("department")

    if filters.get("status"):
        employee_filters["status"] = filters.get("status")
    else:
        employee_filters["status"] = "Active"

    company = (
        frappe.defaults.get_user_default("Company")
        or frappe.get_default("Company")
    )

    if company:
        employee_filters["company"] = company

    # ---------------------------------------------------------
    # 2. Get employees
    # ---------------------------------------------------------

    employees = frappe.get_all(
        "Employee",
        filters=employee_filters,
        fields=[
            "name",
            "employee_name",
            "department",
            "designation",
            "status",
            "company",
            "date_of_joining",
        ],
        order_by="employee_name asc",
    )

    if not employees:
        return [], 0, 0

    # Get Employee IDs
    employee_names = [employee.name for employee in employees]

    # ---------------------------------------------------------
    # 3. Get leave balances for all employees
    # ---------------------------------------------------------

    leave_balances = frappe.db.sql(
        """
        SELECT
            L.employee,
            L.leave_type,

            COALESCE(
                SUM(
                    CASE
                        WHEN L.is_carry_forward = 1
                        AND L.leaves > 0
                        THEN L.leaves
                        ELSE 0
                    END
                ),
                0
            ) AS opening_balance,

            COALESCE(
                SUM(
                    CASE
                        WHEN L.transaction_type = 'Leave Allocation'
                        AND L.is_carry_forward = 0
                        AND L.leaves > 0
                        THEN L.leaves
                        ELSE 0
                    END
                ),
                0
            ) AS new_leaves_allocated,

            COALESCE(
                SUM(
                    CASE
                        WHEN L.transaction_type = 'Leave Application'
                        AND L.leaves < 0
                        THEN ABS(L.leaves)
                        ELSE 0
                    END
                ),
                0
            ) AS leaves_taken,

            COALESCE(
                SUM(
                    CASE
                        WHEN L.is_expired = 1
                        AND L.leaves < 0
                        THEN ABS(L.leaves)
                        ELSE 0
                    END
                ),
                0
            ) AS leaves_expired,

            COALESCE(
                SUM(L.leaves),
                0
            ) AS balance,

            T.include_holiday

        FROM `tabLeave Ledger Entry` L

        JOIN `tabLeave Type` T
            ON L.leave_type = T.name

        WHERE L.employee IN %(employees)s

        GROUP BY
            L.employee,
            L.leave_type,
            T.include_holiday

        ORDER BY
            L.employee,
            L.leave_type
        """,
        {
            "employees": employee_names
        },
        as_dict=True,
    )

    # ---------------------------------------------------------
    # 4. Group leave balances by employee
    # ---------------------------------------------------------

    leave_balance_map = {}

    for balance in leave_balances:

        employee = balance.employee

        if employee not in leave_balance_map:
            leave_balance_map[employee] = []

        leave_balance_map[employee].append({
            "leave_type": balance.leave_type,
            "opening_balance": flt(balance.opening_balance),
            "new_leaves_allocated": flt(balance.new_leaves_allocated),
            "leaves_taken": flt(balance.leaves_taken),
            "leaves_expired": flt(balance.leaves_expired),
            "balance": flt(balance.balance),
            "include_holiday": balance.include_holiday,
        })

    # ---------------------------------------------------------
    # 5. Build final employee response
    # ---------------------------------------------------------

    employee_data = []

    for employee in employees:

        employee_data.append({
            "employeeInfo": {
                "name": employee.name,
                "employee_name": employee.employee_name,
                "department": employee.department,
                "designation": employee.designation,
                "status": employee.status,
                "company": employee.company,
                "date_of_joining": employee.date_of_joining,
            },

            "leaveBalances": leave_balance_map.get(
                employee.name,
                []
            ),
        })

    # ---------------------------------------------------------
    # 6. Employee-level pagination
    # ---------------------------------------------------------

    total = len(employee_data)

    total_pages = (
        math.ceil(total / page_size)
        if page_size > 0
        else 0
    )

    start = (page - 1) * page_size
    end = start + page_size

    paginated_data = employee_data[start:end]

    return paginated_data, total, total_pages

