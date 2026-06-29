import frappe

def get_employee_advance_by_id_with_claims(id, from_date, to_date, ):
    
    employee_advance_doc = frappe.get_doc("Employee Advance", id).as_dict()
    filters = {"employee_advance": id}
        
    if from_date:
        filters["posting_date"] = [">=", from_date]
    if to_date:
        filters["posting_date"] = ["<=", to_date]
    if from_date and to_date:
        filters["posting_date"] = ["between", [from_date, to_date]]

    expense_claim_advance = frappe.get_all(
                                            "Expense Claim Advance",
                                            filters=filters,
                                            fields=["*"]
                                        )
    for claim in expense_claim_advance:
        claim_doc = frappe.get_doc("Expense Claim", claim.parent).as_dict()
        if claim_doc:
            expenses = claim_doc.get("expenses", [])
            claim.claim_title = expenses[0].get("expense_type") if expenses else None
            claim.description = claim_doc.get("remark")

    employee_advance_doc["expense_claims"] = expense_claim_advance
    return employee_advance_doc