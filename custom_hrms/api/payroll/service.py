import json
import frappe
from frappe import _

from hrms.payroll.doctype.payroll_entry.payroll_entry import (
    create_salary_slips_for_employees,
    submit_salary_slips_for_employees,
)


def get_payroll_employee(filters):
    doc = frappe.new_doc("Payroll Entry")

    doc.company = filters.get("company")
    doc.start_date = filters.get("start_date")
    doc.end_date = filters.get("end_date")
    doc.payroll_frequency = filters.get("payroll_frequency")
    doc.payroll_payable_account = filters.get("payroll_payable_account")
    doc.currency = filters.get("currency")
    doc.salary_slip_based_on_timesheet = filters.get(
        "salary_slip_based_on_timesheet", 0
    )

    doc.fill_employee_details()

    return [
        {
            "value": emp.employee,
            "label": emp.employee_name,
            "description": (emp.department or emp.designation or emp.employee),
        }
        for emp in doc.employees
    ]


@frappe.whitelist()
def run_payroll(payroll_entry: str) -> dict:
    try:
        doc = frappe.get_doc("Payroll Entry", payroll_entry)

        if doc.docstatus != 0:
            return get_error_response(_("Payroll Entry must be in Draft state to run."))

        if not doc.payment_account:
            frappe.db.rollback()
            return get_error_response(
                _(
                    "Payment Account is required on the Payroll Entry to generate a Bank Entry."
                )
            )

        def sync_create_slips():
            process_salary_slips_creation(doc)

        doc.create_salary_slips = sync_create_slips

        doc.submit()
        doc.reload()

        if doc.status == "Failed":
            return get_error_response(
                doc.error_message or _("Salary Slip creation failed.")
            )

        process_salary_slips_submission(doc)
        doc.reload()

        if doc.status == "Failed":
            return get_error_response(
                doc.error_message or _("Salary Slip submission failed.")
            )

        bank_entry = process_bank_entry(doc)

        frappe.db.commit()

        submitted_slips = frappe.get_all(
            "Salary Slip",
            filters={"payroll_entry": doc.name, "docstatus": 1},
            pluck="name",
        )

        return {
            "payroll_entry": doc.name,
            "total_submitted_slips": len(submitted_slips),
            "submitted_salary_slips": submitted_slips,
            "bank_entry": bank_entry.name if bank_entry else None,
        }

    except Exception as e:
        frappe.db.rollback()
        return handle_payroll_exception(e)


def process_salary_slips_creation(doc) -> None:
    employees = [emp.employee for emp in doc.employees]

    if not employees:
        return

    args = frappe._dict(
        {
            "salary_slip_based_on_timesheet": doc.salary_slip_based_on_timesheet,
            "payroll_frequency": doc.payroll_frequency,
            "start_date": doc.start_date,
            "end_date": doc.end_date,
            "company": doc.company,
            "posting_date": doc.posting_date,
            "deduct_tax_for_unsubmitted_tax_exemption_proof": doc.deduct_tax_for_unsubmitted_tax_exemption_proof,
            "payroll_entry": doc.name,
            "exchange_rate": doc.exchange_rate,
            "currency": doc.currency,
        }
    )

    create_salary_slips_for_employees(employees, args, publish_progress=False)


def process_salary_slips_submission(doc) -> None:
    salary_slips = doc.get_sal_slip_list(ss_status=0)

    if salary_slips:
        submit_salary_slips_for_employees(doc, salary_slips, publish_progress=False)


def process_bank_entry(doc):
    has_bank_entry_dict = doc.has_bank_entries()
    if has_bank_entry_dict.get("has_bank_entries"):
        return None

    return doc.make_bank_entry()


def handle_payroll_exception(error: Exception) -> dict:
    error_message = str(error)

    if frappe.message_log:
        messages = []
        for msg in frappe.message_log:
            try:
                if isinstance(msg, str):
                    parsed_msg = json.loads(msg)
                    if (
                        parsed_msg.get("indicator") != "green"
                        and parsed_msg.get("title") != "Success"
                    ):
                        if parsed_msg.get("message"):
                            messages.append(parsed_msg.get("message"))
                else:
                    messages.append(msg.get("message", str(msg)))
            except ValueError, TypeError, AttributeError:
                messages.append(str(msg))

        if messages:
            error_message = " | ".join(messages)

    return get_error_response(error_message, frappe.get_traceback())


def get_error_response(message: str, traceback: str | None = None) -> dict:
    response = {
        "status": "error",
        "message": message,
    }

    if traceback:
        response["traceback"] = traceback

    return response
