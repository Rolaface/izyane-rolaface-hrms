import frappe
from custom_hrms.utils.response import send_response, send_response_list
from . import service


def validate_payroll(payroll_entry_id):
    doc = frappe.get_doc("Payroll Entry", payroll_entry_id)

    if doc.docstatus != 0:
        return "Payroll Entry must be in Draft state to run."

    if not doc.payment_account:
        return (
            "Payment Account is required on the Payroll Entry to generate a Bank Entry."
        )

    payroll_period = frappe.db.get_value(
        "Payroll Period",
        {
            "company": doc.company,
            "start_date": ("<=", doc.start_date),
            "end_date": (">=", doc.end_date),
        },
        "name",
    )

    if not payroll_period:
        return (
            f"No Payroll Period is set for {doc.company} covering the dates "
            f"from {doc.start_date} to {doc.end_date}."
        )

    return None


@frappe.whitelist(allow_guest=False, methods=["GET"])
def get_payroll_employee(page=1, page_size=20):
    try:
        page = int(page)
        page_size = int(page_size)

        company = frappe.request.args.get(
            "company"
        ) or frappe.defaults.get_user_default("Company")

        sort_by = frappe.request.args.get(
            "sort_by",
            "label",
        )

        sort_order = frappe.request.args.get(
            "sort_order",
            "asc",
        )

        filters = frappe._dict(
            {
                "company": company,
                "start_date": frappe.request.args.get("start_date"),
                "end_date": frappe.request.args.get("end_date"),
                "payroll_frequency": (
                    frappe.request.args.get("payroll_frequency") or "Monthly"
                ),
                "payroll_payable_account": (
                    frappe.request.args.get("payroll_payable_account")
                    or frappe.db.get_value(
                        "Company",
                        company,
                        "default_payroll_payable_account",
                    )
                ),
                "currency": (
                    frappe.request.args.get("currency")
                    or frappe.db.get_value(
                        "Company",
                        company,
                        "default_currency",
                    )
                ),
                "department": frappe.request.args.get("department"),
                "branch": frappe.request.args.get("branch"),
                "designation": frappe.request.args.get("designation"),
                "grade": frappe.request.args.get("grade"),
                "salary_slip_based_on_timesheet": frappe.utils.cint(
                    frappe.request.args.get(
                        "salary_slip_based_on_timesheet",
                        0,
                    )
                ),
            }
        )

        (
            employees,
            total_employees,
            total_pages,
        ) = service.get_payroll_employee(
            filters=filters,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        response_data = {
            "success": True,
            "message": ("Payroll employees retrieved successfully"),
            "data": employees,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total_employees,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
            },
        }

        return send_response_list(
            status="success",
            message="Success",
            status_code=200,
            data=response_data,
            http_status=200,
        )

    except Exception as e:
        frappe.log_error(
            frappe.get_traceback(),
            "Get Payroll Employees API Error",
        )

        return send_response(
            status="error",
            message=f"Internal Server Error: {str(e)}",
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
