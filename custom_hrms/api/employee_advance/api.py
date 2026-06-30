from frappe import _
from custom_hrms.api.employee_advance.service import get_employee_advance_by_id_with_claims
import frappe
from custom_hrms.utils.response import send_response
from frappe.utils.pdf import get_pdf

@frappe.whitelist(allow_guest=False, methods=["GET"])
def get_by_id(id, from_date=None, to_date=None,page=1, page_size=10):
    try:

        employee_advance_doc = get_employee_advance_by_id_with_claims(id, from_date, to_date, page, page_size)

        return send_response(
                                status="success",
                                message=None,
                                data = employee_advance_doc,
                            )

    except Exception as e:
        frappe.log_error("Error in Employee Advance By id: ", str(e))

        return send_response(
            status="error",
            message=str(e),
            data=None,
            status_code=500,
            http_status=500,
        )

@frappe.whitelist(allow_guest=False, methods=["GET"])
def generate_advance_statement_pdf():
    id = frappe.form_dict.get("id")
    from_date = frappe.form_dict.get("from_date")
    to_date = frappe.form_dict.get("to_date")

    if not id:
        frappe.throw(_("Advance ID must not be null"))

    if not frappe.db.exists("Employee Advance", id):
        frappe.throw(_(f"Advance {id} not found"))

    statement_data = get_employee_advance_by_id_with_claims(id, from_date, to_date)
    ADVANCE_STATEMENT_TEMPLATE = "custom_hrms/templates/employee_advance_statement.html"
    html = frappe.render_template(ADVANCE_STATEMENT_TEMPLATE, {
                                                    "doc": statement_data,
                                                    "from_date": from_date,
                                                    "to_date": to_date,
                                                    "frappe": frappe
                                                })

    pdf_options = {
        "page-size": "A4",
        "margin-top": "15mm",
        "margin-right": "10mm",
        "margin-bottom": "10mm",
        "margin-left": "15mm",
        "encoding": "UTF-8",
        "no-outline": None
    }

    pdf = get_pdf(html, options=pdf_options)

    frappe.local.response.filename = f"{statement_data.get('name')}.pdf"
    frappe.local.response.filecontent = pdf
    frappe.local.response.type = "download"