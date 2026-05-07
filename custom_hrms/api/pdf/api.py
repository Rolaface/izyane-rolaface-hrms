import frappe

from .service import generate_document_pdf


@frappe.whitelist()
def get_document_pdf(
    doctype: str,
    name: str,
    print_format: str | None = None,
):
    return generate_document_pdf(
        doctype=doctype,
        name=name,
        print_format=print_format,
    )
