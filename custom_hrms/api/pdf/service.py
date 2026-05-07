import frappe

from frappe.utils.pdf import get_pdf

from .utils import resolve_print_format


def generate_document_pdf(
    doctype: str,
    name: str,
    print_format: str | None = None,
):
    if not frappe.has_permission(doctype, "read", doc=name):
        frappe.throw("Not permitted")

    resolved_print_format = resolve_print_format(
        doctype=doctype,
        print_format=print_format,
    )

    html = frappe.get_print(
        doctype=doctype,
        name=name,
        print_format=resolved_print_format,
        no_letterhead=1,
    )

    pdf = get_pdf(html)

    frappe.local.response.filename = f"{name}.pdf"
    frappe.local.response.filecontent = pdf
    frappe.local.response.type = "pdf"
