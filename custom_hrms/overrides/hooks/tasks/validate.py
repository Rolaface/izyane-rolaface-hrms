import frappe

def validate_task(doc, method=None):
    if not doc.type:
        frappe.throw("Task type is required.")    
