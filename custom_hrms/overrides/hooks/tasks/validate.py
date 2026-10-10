import frappe

def validate_task(doc, method=None):
    if not doc.custom_activity_type:
        frappe.throw("Activity Type is required.")