import frappe

def before_validate(doc, method):

    default_cost_center = frappe.db.get_value("Company", doc.company, "cost_center")
    
    if doc.expenses:
        for expense in doc.expenses:
            if not expense.cost_center:
                expense.cost_center = default_cost_center
    if doc.advances:
        for advance in doc.advances:
            if not advance.advance_account:
                advance_account = frappe.db.get_value("Employee Advance", advance.employee_advance, "advance_account")
                advance.advance_account = advance_account