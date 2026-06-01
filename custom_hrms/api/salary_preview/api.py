import frappe
from frappe import _

from .service import (
    validate_inputs,
   
    get_salary_structure_assignment,
    build_preview_salary_slip,
    serialize,
)
from custom_hrms.utils.response import send_response


@frappe.whitelist(allow_guest=False, methods=["GET"])
def get_salary_breakdown():
    try:
        return _handle_request()
    except frappe.PermissionError:
        raise
    except frappe.ValidationError as exc:
        return send_response(status="fail", message=str(exc), status_code=422, http_status=422)
    except Exception:
        frappe.log_error(title="Salary Preview Error", message=frappe.get_traceback())
        return send_response(
            status="error",
            message=_("Something went wrong ."),
            status_code=500,
            http_status=500,
        )


def _handle_request():
    employee       = frappe.request.args.get("employee", "").strip()
    effective_date = frappe.request.args.get("effective_date", "").strip()

    error, effective_date = validate_inputs(employee, effective_date)
    if error:
        return send_response(status="fail", message=error, status_code=400, http_status=400)

   
    assignment = get_salary_structure_assignment(employee, effective_date)
    if not assignment:
        return send_response(
            status="fail",
            message=_(
                "No submitted Salary Structure Assignment found for employee {0} on or before {1}."
            ).format(employee, effective_date),
            status_code=404,
            http_status=404,
        )

    salary_slip = build_preview_salary_slip(
        salary_structure=assignment["salary_structure"],
        employee=employee,
        posting_date=effective_date,
    )

    return send_response(
        status="success",
        message="Salary breakdown retrieved successfully.",
        data=serialize(salary_slip, assignment, effective_date),
        status_code=200,
        http_status=200,
    )