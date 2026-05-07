import frappe


def resolve_print_format(
    doctype: str,
    print_format: str | None = None,
) -> str:

    if print_format:
        return print_format

    default_print_format = frappe.db.get_value(
        "Property Setter",
        {
            "doc_type": doctype,
            "property": "default_print_format",
        },
        "value",
    )

    return default_print_format or "Standard"
