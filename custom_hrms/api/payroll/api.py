import frappe
from custom_hrms.utils.response import send_response
from . import service


def validate_payroll(payroll_entry_id):
    doc = frappe.get_doc("Payroll Entry", payroll_entry_id)

    if doc.docstatus != 0:
        return "Payroll Entry must be in Draft state to run."

    if not doc.payment_account:
        return (
            "Payment Account is required on the Payroll Entry to generate a Bank Entry."
        )

    return None


@frappe.whitelist(allow_guest=False, methods=["GET"])
def get_payroll_employee():
    try:
        filters = frappe._dict(
            {
                "company": frappe.request.args.get("company"),
                "start_date": frappe.request.args.get("start_date"),
                "end_date": frappe.request.args.get("end_date"),
                "payroll_frequency": frappe.request.args.get("payroll_frequency"),
                "payroll_payable_account": frappe.request.args.get(
                    "payroll_payable_account"
                ),
                "currency": frappe.request.args.get("currency"),
                "salary_slip_based_on_timesheet": frappe.utils.cint(
                    frappe.request.args.get("salary_slip_based_on_timesheet", 0)
                ),
            }
        )

        data = service.get_payroll_employee(filters)

        return send_response(
            status="success",
            message="Payroll employees fetched successfully.",
            data=data,
            status_code=200,
            http_status=200,
        )

    except Exception as e:
        frappe.log_error(
            frappe.get_traceback(),
            "Get Payroll Employees API Error",
        )

        return send_response(
            status="error",
            message="Failed to fetch payroll employees.",
            data={"error": str(e)},
            status_code=500,
            http_status=500,
        )


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

        validation_error = validate_payroll(payroll_entry_id)
        if validation_error:
            return send_response(
                status="fail",
                message=validation_error,
                status_code=400,
                http_status=400,
            )

        result = service.run_payroll(payroll_entry_id)

        if isinstance(result, dict) and result.get("status") == "error":
            frappe.db.rollback()
            return send_response(
                status="error",
                message=result.get("message", "Payroll processing failed."),
                data=result,
                status_code=400,
                http_status=400,
            )

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
