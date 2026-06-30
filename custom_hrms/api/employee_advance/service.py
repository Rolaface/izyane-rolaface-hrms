import frappe

def get_employee_advance_by_id_with_claims(id, from_date, to_date, page, page_size):
    
    employee_advance_doc = frappe.get_doc("Employee Advance", id).as_dict()
    filters = {"employee_advance": id}
        
    if from_date:
        filters["posting_date"] = [">=", from_date]
    if to_date:
        filters["posting_date"] = ["<=", to_date]
    if from_date and to_date:
        filters["posting_date"] = ["between", [from_date, to_date]]

    page = int(page) if page else 1
    page_size = int(page_size) if page_size else 10
    start = (page - 1) * page_size
    total_count = frappe.db.count("Expense Claim Advance", filters=filters)
    total_pages = (total_count + page_size - 1) // page_size

    expense_claim_advance = frappe.get_all(
                                            "Expense Claim Advance",
                                            filters=filters,
                                            fields=["*"],
                                            start=start,
                                            page_length=page_size,
                                            order_by="posting_date desc"
                                        )
    for claim in expense_claim_advance:
        claim_doc = frappe.get_doc("Expense Claim", claim.parent).as_dict()
        if claim_doc:
            expenses = claim_doc.get("expenses", [])
            claim.claim_title = expenses[0].get("expense_type") if expenses else None
            claim.description = claim_doc.get("remark")

    employee_advance_doc["expense_claims"] = expense_claim_advance

    employee_advance_doc["pagination"] = {
        "page": page,
        "page_size": page_size,
        "total_count": total_count,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1
    }
    return employee_advance_doc