import frappe
from frappe.utils import cint
from custom_hrms.utils.response import send_response, send_response_list

from . import service
import json

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

    response_data = service.get_assignment_list(
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

@frappe.whitelist(allow_guest=False, methods=["POST"])
def sync_condition_and_formula():
    try:
        salary_component = frappe.request.args.get("salary_component")

        if not salary_component:
            return send_response(
                status="fail",
                message="salary_component is required.",
                status_code=400,
                http_status=400,
            )

        result = service.sync_condition_and_formula(
            salary_component=salary_component
        )

        frappe.db.commit()

        return send_response(
            status="success",
            message="Condition and formula synced successfully.",
            data=result,
            status_code=200,
            http_status=200,
        )

    except Exception:
        frappe.db.rollback()

        traceback = frappe.get_traceback()

        frappe.log_error(
            message=traceback,
            title="Sync Condition And Formula Error",
        )

        return send_response(
            status="error",
            message=traceback,
            status_code=500,
            http_status=500,
        )