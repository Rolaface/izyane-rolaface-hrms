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
        for claim in expense_claim_advance:
            claim_doc = frappe.get_doc("Expense Claim", claim.parent).as_dict()
            if claim_doc:
                expenses = claim_doc.get("expenses", [])
                claim.claim_title = expenses[0].get("expense_type") if expenses else None
                claim.description = claim_doc.get("remark")

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