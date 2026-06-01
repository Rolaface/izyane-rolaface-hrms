import frappe
from frappe.utils import cint
from custom_hrms.utils.response import send_response, send_response_list

from .service import get_assignment_list


@frappe.whitelist(allow_guest=False, methods=["GET"])
def get_salary_structure_assignment_list():
    try:
        return _handle_request()
    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            "Salary Structure Assignment API Error",
        )
        return send_response(
            status="error",
            message="Internal Server Error",
            status_code=500,
            http_status=500,
        )


def _handle_request():
    employee  = frappe.request.args.get("employee")
    company   = frappe.request.args.get("company") or frappe.defaults.get_user_default("Company")
    from_date = frappe.request.args.get("from_date")
    to_date   = frappe.request.args.get("to_date")
    page      = max(cint(frappe.request.args.get("page", 1)), 1)
    page_size = min(max(cint(frappe.request.args.get("page_size", 20)), 1), 100)

    if not employee:
        return send_response(
            status="fail",
            message="Employee is required.",
            status_code=400,
            http_status=400,
        )

    response_data = get_assignment_list(
        employee=employee,
        company=company,
        from_date=from_date,
        to_date=to_date,
        page=page,
        page_size=page_size,
    )

    return send_response_list(
        status="success",
        message="Salary Structure Assignments retrieved successfully.",
        status_code=200,
        data=response_data,
        http_status=200,
    )