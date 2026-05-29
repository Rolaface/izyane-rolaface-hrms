import frappe

def before_validate(doc, method):

    default_cost_center = frappe.db.get_value("Company", doc.company, "cost_center")
    
    if doc.expenses:
        for expense in doc.expenses:
            if not expense.cost_center:
                expense.cost_center = default_cost_center