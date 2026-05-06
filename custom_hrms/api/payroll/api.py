import frappe
from custom_hrms.utils.response import send_response
from . import service


@frappe.whitelist(allow_guest=False, methods=["POST"])
def run_payroll(id=None):
    try:
        payroll_entry_id = (
            id or frappe.request.args.get("id") or frappe.local.form_dict.get("id")
        )

        if not payroll_entry_id:
            return send_response(
                status="fail",
                message="'id' is required.",
                status_code=400,
                http_status=400,
            )

        if not frappe.db.exists("Payroll Entry", payroll_entry_id):
            return send_response(
                status="fail",
                message="Payroll Entry not found.",
                status_code=404,
                http_status=404,
            )

        result = service.run_payroll(payroll_entry_id)

        frappe.db.commit()

        return send_response(
            status="success",
            message="Payroll processed successfully.",
            data=result,
            status_code=200,
            http_status=200,
        )

    except frappe.ValidationError as e:
        frappe.db.rollback()

        return send_response(
            status="fail",
            message=str(e),
            status_code=400,
            http_status=400,
        )

    except Exception as e:
        frappe.db.rollback()

        frappe.log_error(
            frappe.get_traceback(),
            "Run Payroll API Error",
        )

        return send_response(
            status="error",
            message="Failed to run payroll.",
            data={"error": str(e)},
            status_code=500,
            http_status=500,
        )
