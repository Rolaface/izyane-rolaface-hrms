import frappe
from custom_hrms.utils.response import send_response

@frappe.whitelist(allow_guest=False, methods=["GET"])
def get_by_id(id):
    try:
        employee_advance_doc = frappe.get_doc("Employee Advance", id).as_dict()
        expense_claim_advance = frappe.get_all(
                                                "Expense Claim Advance",
                                                filters={
                                                    "employee_advance": id
                                                },
                                                fields=["*"]
                                            )
        employee_advance_doc["expense_claims"] = expense_claim_advance
        return send_response(
                                status="success",
                                message=None,
                                data = employee_advance_doc,
                            )

    except Exception as e:
        frappe.log_error("Error in Emoplyee Advance By id: ", str(e))

        return send_response(
            status="error",
            message=str(e),
            data=None,
            status_code=500,
            http_status=500,
        )