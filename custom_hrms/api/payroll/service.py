import json
import frappe
from frappe import _
import math
from .utils import PAYROLL_ENTRY_FIELDS, SALARY_SLIP_FIELDS, SALARY_DETAIL_FIELDS

from hrms.payroll.doctype.payroll_entry.payroll_entry import (
    create_salary_slips_for_employees,
    submit_salary_slips_for_employees,
    employee_query,
)

def get_payroll_employee(
    filters,
    page=1,
    page_size=20,
    sort_by="label",
    sort_order="asc",
):
    employees = employee_query(
        txt="",
        doctype="Employee",
        searchfield="name",
        start=0,
        page_len=999999,
        filters=filters,
    )

    data = [
        {
            "value": emp[0],
            "label": emp[1],
            "description": (emp[1] if len(emp) > 1 else emp[0]),
        }
        for emp in employees
    ]

    allowed_sort_fields = {
        "value",
        "label",
        "description",
    }

    sort_by = sort_by if sort_by in allowed_sort_fields else "label"

    reverse = str(sort_order).lower() == "desc"

    data.sort(
        key=lambda x: (x.get(sort_by) or "").lower(),
        reverse=reverse,
    )

    total_employees = len(data)

    total_pages = math.ceil(total_employees / page_size)

    start = (page - 1) * page_size
    end = start + page_size

    paginated_employees = data[start:end]

    return (
        paginated_employees,
        total_employees,
        total_pages,
    )


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


def extract_allowed_fields(raw_dict, allowed_fields):
    return {key: raw_dict[key] for key in allowed_fields if key in raw_dict}


def calculate_payroll_entry_payable(payroll_entry_id):
    doc = frappe.get_doc("Payroll Entry", payroll_entry_id)

    existing_slips = frappe.get_all(
        "Salary Slip", filters={"payroll_entry": payroll_entry_id}, pluck="name"
    )

    if existing_slips:
        total_gross_payable = 0.0
        total_net_payable = 0.0
        total_deduction = 0.0
        breakdown = []

        for slip_name in existing_slips:
            slip_doc = frappe.get_doc("Salary Slip", slip_name)

            # Use rounded_total for net if available, otherwise exact net_pay
            net_payable = slip_doc.rounded_total or slip_doc.net_pay or 0.0
            gross = slip_doc.gross_pay or 0.0
            deduction = slip_doc.total_deduction or 0.0

            total_gross_payable += gross
            total_net_payable += net_payable
            total_deduction += deduction

            raw_slip = slip_doc.as_dict()
            slip_dict = extract_allowed_fields(raw_slip, SALARY_SLIP_FIELDS)

            slip_dict["earnings"] = [
                extract_allowed_fields(e, SALARY_DETAIL_FIELDS)
                for e in raw_slip.get("earnings", [])
            ]
            slip_dict["deductions"] = [
                extract_allowed_fields(d, SALARY_DETAIL_FIELDS)
                for d in raw_slip.get("deductions", [])
            ]

            if slip_doc.docstatus == 1:
                slip_status = "Submitted"
            elif slip_doc.docstatus == 2:
                slip_status = "Cancelled"
            else:
                slip_status = "Draft"

            slip_dict["status"] = slip_status
            slip_dict["net_payable"] = net_payable
            breakdown.append(slip_dict)

        return {
            "payroll_entry": payroll_entry_id,
            "currency": doc.currency,
            "total_gross_payable": total_gross_payable,
            "total_net_payable": total_net_payable,
            "total_deduction": total_deduction,
            "employee_count": len(existing_slips),
            "calculation_method": "From Existing Salary Slips",
            "employee_breakdown": breakdown,
        }

    if not doc.get("employees"):
        try:
            doc.fill_employee_details()
        except Exception as e:
            return {
                "payroll_entry": payroll_entry_id,
                "total_gross_payable": 0.0,
                "total_net_payable": 0.0,
                "total_deduction": 0.0,
                "employee_count": 0,
                "employee_breakdown": [],
                "last_error": f"Failed to fetch employees: {str(e)}",
            }

    if not doc.get("employees"):
        return {
            "payroll_entry": payroll_entry_id,
            "currency": doc.currency,
            "total_gross_payable": 0.0,
            "total_net_payable": 0.0,
            "total_deduction": 0.0,
            "employee_count": 0,
            "employee_breakdown": [],
            "last_error": "No eligible employees found.",
        }

    total_gross_payable = 0.0
    total_net_payable = 0.0
    total_deduction = 0.0
    processed_count = 0
    last_error = None
    breakdown = []

    for emp in doc.employees:
        preview_data = generate_salary_slip_preview(
            employee=emp.employee,
            start_date=doc.start_date,
            end_date=doc.end_date,
            company=doc.company,
            payroll_frequency=doc.payroll_frequency,
            posting_date=doc.posting_date,
            salary_slip_based_on_timesheet=doc.get("salary_slip_based_on_timesheet", 0),
            payroll_entry=doc.name,
            currency=doc.currency,
            exchange_rate=doc.exchange_rate,
        )

        total_gross_payable += preview_data.get("gross_pay", 0.0)
        total_net_payable += preview_data.get("net_payable", 0.0)
        total_deduction += preview_data.get("total_deduction", 0.0)

        if preview_data.get("net_payable", 0.0) > 0:
            processed_count += 1

        if preview_data.get("status") == "Error":
            last_error = preview_data.get("error_message")

        breakdown.append(preview_data)

    return {
        "payroll_entry": payroll_entry_id,
        "currency": doc.currency,
        "total_gross_payable": total_gross_payable,
        "total_net_payable": total_net_payable,
        "total_deduction": total_deduction,
        "employee_count": processed_count,
        "calculation_method": "On-the-fly Dynamic Calculation",
        "employee_breakdown": breakdown,
        "last_error": last_error,
    }


def generate_salary_slip_preview(
    employee,
    start_date,
    end_date,
    company,
    payroll_frequency=None,
    posting_date=None,
    salary_slip_based_on_timesheet=0,
    payroll_entry=None,
    currency=None,
    exchange_rate=None,
    salary_structure=None,
):
    try:
        slip = frappe.new_doc("Salary Slip")
        slip.employee = employee
        slip.start_date = start_date
        slip.end_date = end_date
        slip.company = company

        if payroll_frequency:
            slip.payroll_frequency = payroll_frequency

        if payroll_entry:
            slip.payroll_entry = payroll_entry

        if salary_structure:
            slip.salary_structure = salary_structure

        slip.posting_date = posting_date or frappe.utils.today()
        slip.salary_slip_based_on_timesheet = salary_slip_based_on_timesheet

        if currency:
            slip.currency = currency
        if exchange_rate:
            slip.exchange_rate = exchange_rate

        slip.get_emp_and_working_day_details()
        
        if hasattr(slip, "set_payroll_period"):
            slip.set_payroll_period()
            
        slip.process_salary_structure()
        slip.calculate_net_pay()

        if hasattr(slip, "compute_year_to_date"):
            slip.compute_year_to_date()

        net_payable = slip.rounded_total or slip.net_pay or 0.0

        raw_slip = slip.as_dict()
        slip_dict = extract_allowed_fields(raw_slip, SALARY_SLIP_FIELDS)

        slip_dict["earnings"] = [
            extract_allowed_fields(e, SALARY_DETAIL_FIELDS)
            for e in raw_slip.get("earnings", [])
        ]
        slip_dict["deductions"] = [
            extract_allowed_fields(d, SALARY_DETAIL_FIELDS)
            for d in raw_slip.get("deductions", [])
        ]

        slip_dict["status"] = "Preview"
        slip_dict["net_payable"] = net_payable
        slip_dict["gross_pay"] = slip.gross_pay or 0.0
        slip_dict["total_deduction"] = slip.total_deduction or 0.0
        slip_dict["error_message"] = None

        return slip_dict

    except Exception as e:
        emp_name = (
            frappe.db.get_value("Employee", employee, "employee_name") or employee
        )
        return {
            "employee": employee,
            "employee_name": emp_name,
            "status": "Error",
            "error_message": str(e),
            "net_payable": 0.0,
            "gross_pay": 0.0,
            "total_deduction": 0.0,
            "earnings": [],
            "deductions": [],
        }


def get_payroll_entry_list(
    filters, page=1, page_size=20, search="", sort_by="creation", sort_order="desc", start_date=None, end_date=None
):
    start = (page - 1) * page_size
    fields = [
        "name",
        "company",
        "start_date",
        "end_date",
        "payroll_frequency",
        "status",
        "currency",
    ]

    or_filters = []
    if start_date and end_date:
     filters["start_date"] = ["between", [start_date, end_date]]
    elif start_date:
     filters["start_date"] = [">=", start_date]
    elif end_date:
     filters["end_date"] = ["<=", end_date]
    if search:
         or_filters = [
        ["name", "like", f"%{search}%"],
        ["status", "like", f"%{search}%"],
        
    
    ]

    allowed_sort_fields = [
        "name",
        "creation",
        "start_date",
        "end_date",
        "status",
        "company",
        "payroll_frequency",
    ]
    if sort_by not in allowed_sort_fields:
        sort_by = "creation"

    sort_order = "desc" if sort_order.lower() == "desc" else "asc"
    order_by_string = f"{sort_by} {sort_order}"

    entries = frappe.get_all(
        "Payroll Entry",
        filters=filters,
        or_filters=or_filters,
        fields=fields,
        order_by=order_by_string,
        limit_start=start,
        limit_page_length=page_size,
    )

    for entry in entries:
        try:
            summary = calculate_payroll_entry_payable(entry.name)
            entry["total_gross_payable"] = summary.get("total_gross_payable", 0.0)
            entry["total_net_payable"] = summary.get("total_net_payable", 0.0)
            entry["total_deduction"] = summary.get("total_deduction", 0.0)
            entry["employee_count"] = summary.get("employee_count", 0)

            if summary.get("last_error"):
                entry["last_error"] = summary.get("last_error")
        except Exception as e:
            entry["total_gross_payable"] = 0.0
            entry["total_net_payable"] = 0.0
            entry["total_deduction"] = 0.0
            entry["employee_count"] = 0
            entry["last_error"] = f"Fatal Loop Error: {str(e)}"

    total_count = len(
        frappe.get_all(
            "Payroll Entry", filters=filters, or_filters=or_filters, pluck="name"
        )
    )
    total_pages = math.ceil(total_count / page_size) if page_size else 1

    return entries, total_count, total_pages


def get_payroll_entry_details(payroll_entry_id):
    doc = frappe.get_doc("Payroll Entry", payroll_entry_id)
    raw_doc = doc.as_dict()

    doc_dict = extract_allowed_fields(raw_doc, PAYROLL_ENTRY_FIELDS)
    financial_summary = calculate_payroll_entry_payable(payroll_entry_id)

    doc_dict["financial_summary"] = {
        "total_gross_payable": financial_summary.get("total_gross_payable"),
        "total_net_payable": financial_summary.get("total_net_payable"),
        "total_deduction": financial_summary.get("total_deduction"),
        "employee_count": financial_summary.get("employee_count"),
        "calculation_method": financial_summary.get("calculation_method"),
    }

    breakdown_list = financial_summary.get("employee_breakdown", [])
    breakdown_map = {b["employee"]: b for b in breakdown_list}

    employee_ids = [
        emp.get("employee")
        for emp in raw_doc.get("employees", [])
        if emp.get("employee")
    ]

    employees = frappe.get_all(
        "Employee",
        filters={"name": ["in", employee_ids]},
        fields=["name", "gender"],
    )

    gender_map = {
        emp["name"]: emp["gender"]
        for emp in employees
    }

    doc_dict["employees"] = []

    for emp in raw_doc.get("employees", []):
        emp_id = emp.get("employee")

        clean_emp = {
            "employee": emp_id,
            "employee_name": emp.get("employee_name"),
            "department": emp.get("department"),
            "designation": emp.get("designation"),
            "gender": gender_map.get(emp_id),
            "salary_slip_details": breakdown_map.get(emp_id),
        }

        doc_dict["employees"].append(clean_emp)

    if financial_summary.get("last_error"):
        doc_dict["last_error"] = financial_summary.get("last_error")

    return doc_dict

def delete_payroll_entry_and_links(payroll_entry_id: str) -> dict:

    doc = frappe.get_doc("Payroll Entry", payroll_entry_id)

    if doc.docstatus != 2:
        return {
            "status": "error",
            "message": _("Only Cancelled Payroll Entries can be deleted.")
        }

    linked_jes = set()
    
    if doc.get("bank_entry"):
        linked_jes.add(doc.bank_entry)

    je_accounts = frappe.get_all(
        "Journal Entry Account",
        filters={
            "reference_type": "Payroll Entry",
            "reference_name": payroll_entry_id
        },
        pluck="parent"
    )
    linked_jes.update(je_accounts)

    for je_name in linked_jes:
        if frappe.db.exists("Journal Entry", je_name):
            je_status = frappe.db.get_value("Journal Entry", je_name, "docstatus")
            if je_status in [0, 2]:
                frappe.delete_doc("Journal Entry", je_name, ignore_permissions=True)

    salary_slips = frappe.get_all(
        "Salary Slip", 
        filters={"payroll_entry": payroll_entry_id}, 
        pluck="name"
    )
    for slip_name in salary_slips:
        slip_status = frappe.db.get_value("Salary Slip", slip_name, "docstatus")
        if slip_status in [0, 2]:
            frappe.delete_doc("Salary Slip", slip_name, ignore_permissions=True)

    frappe.delete_doc("Payroll Entry", payroll_entry_id, ignore_permissions=True)

    return {"status": "success"}