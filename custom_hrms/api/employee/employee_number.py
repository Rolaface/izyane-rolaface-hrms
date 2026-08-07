import frappe
from custom_hrms.utils.response import send_response
from . import employee_number_service as service


@frappe.whitelist(allow_guest=False, methods=["GET"])
def get_next_employee_number():
    try:
        next_number = service.get_next_employee_number()

        return send_response(
            status="success",
            message="Next employee number generated successfully.",
            data={"employee_number": next_number},
            status_code=200,
            http_status=200,
        )

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Get Next Employee Number API Error")
        return send_response(
            status="error",
            message=str(e),
            status_code=500,
            http_status=500,
        )


@frappe.whitelist(allow_guest=False, methods=["GET"])
def check_employee_number():
    try:
        args = frappe.local.form_dict
        employee_number = args.get("employee_number")
        exclude_employee_id = args.get("exclude_employee_id")

        result = service.check_employee_number_availability(
            employee_number=employee_number,
            exclude_employee_id=exclude_employee_id,
        )

        if not result["is_available"]:
            return send_response(
                status="fail",
                message=f"Employee Number '{result['employee_number']}' is already in use.",
                data=result,
                status_code=409,
                http_status=409,
            )

        return send_response(
            status="success",
            message="Employee Number is available.",
            data=result,
            status_code=200,
            http_status=200,
        )

    except frappe.ValidationError as e:
        return send_response(
            status="fail",
            message=str(e),
            status_code=400,
            http_status=400,
        )

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Check Employee Number API Error")
        return send_response(
            status="error",
            message=str(e),
            status_code=500,
            http_status=500,
        )