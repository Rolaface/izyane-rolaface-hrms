import frappe
from frappe.email.doctype.email_template.email_template import get_email_template

def trigger_email_notification(doc, method):
    if not doc.expense_approver:
        return

    template = get_email_template(
        "Expense Claim",
        doc.as_dict()
    )

    frappe.sendmail(
        recipients=[doc.expense_approver],
        subject=template.get("subject"),
        message=template.get("message"),
        reference_doctype=doc.doctype,
        reference_name=doc.name,
        now=False,
    )