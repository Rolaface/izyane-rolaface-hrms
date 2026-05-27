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
    
    existing_slips = frappe.get_all("Salary Slip", filters={"payroll_entry": payroll_entry_id}, pluck="name")

    if existing_slips:
        total_payable = 0.0
        breakdown = []
        
        for slip_name in existing_slips:
            slip_doc = frappe.get_doc("Salary Slip", slip_name)
            payable = slip_doc.rounded_total or slip_doc.net_pay or 0.0
            total_payable += payable
            
            raw_slip = slip_doc.as_dict()
            slip_dict = extract_allowed_fields(raw_slip, SALARY_SLIP_FIELDS)
            
            slip_dict["earnings"] = [extract_allowed_fields(e, SALARY_DETAIL_FIELDS) for e in raw_slip.get("earnings", [])]
            slip_dict["deductions"] = [extract_allowed_fields(d, SALARY_DETAIL_FIELDS) for d in raw_slip.get("deductions", [])]
            
            if slip_doc.docstatus == 1: slip_status = "Submitted"
            elif slip_doc.docstatus == 2: slip_status = "Cancelled"
            else: slip_status = "Draft"

            slip_dict["status"] = slip_status
            slip_dict["payable_amount"] = payable
            breakdown.append(slip_dict)
            
        return {
            "payroll_entry": payroll_entry_id, "currency": doc.currency, "total_payable": total_payable,
            "employee_count": len(existing_slips), "calculation_method": "From Existing Salary Slips",
            "employee_breakdown": breakdown
        }

    if not doc.get("employees"):
        try: doc.fill_employee_details()
        except Exception as e:
            return {"payroll_entry": payroll_entry_id, "total_payable": 0.0, "employee_count": 0, "employee_breakdown": [], "last_error": f"Failed to fetch employees: {str(e)}"}

    if not doc.get("employees"):
        return {"payroll_entry": payroll_entry_id, "currency": doc.currency, "total_payable": 0.0, "employee_count": 0, "employee_breakdown": [], "last_error": "No eligible employees found."}

    total_payable = 0.0
    processed_count = 0
    last_error = None
    breakdown = []

    for emp in doc.employees:
        try:
            slip = frappe.new_doc("Salary Slip")
            slip.employee = emp.employee
            slip.start_date = doc.start_date
            slip.end_date = doc.end_date
            slip.company = doc.company
            slip.payroll_frequency = doc.payroll_frequency
            slip.payroll_entry = doc.name 
            slip.posting_date = doc.posting_date or frappe.utils.today()
            slip.salary_slip_based_on_timesheet = doc.get("salary_slip_based_on_timesheet", 0)
            
            if doc.currency: slip.currency = doc.currency
            if doc.exchange_rate: slip.exchange_rate = doc.exchange_rate
            
            slip.get_emp_and_working_day_details()
            slip.process_salary_structure()
            slip.calculate_net_pay()
            
            payable = slip.rounded_total or slip.net_pay or 0.0
            total_payable += payable
            if payable > 0: processed_count += 1
                
            raw_slip = slip.as_dict()
            slip_dict = extract_allowed_fields(raw_slip, SALARY_SLIP_FIELDS)
            slip_dict["earnings"] = [extract_allowed_fields(e, SALARY_DETAIL_FIELDS) for e in raw_slip.get("earnings", [])]
            slip_dict["deductions"] = [extract_allowed_fields(d, SALARY_DETAIL_FIELDS) for d in raw_slip.get("deductions", [])]
            
            slip_dict["status"] = "Preview"
            slip_dict["payable_amount"] = payable
            breakdown.append(slip_dict)
                
        except Exception as e:
            last_error = f"Error calculating for {emp.employee}: {str(e)}"
            breakdown.append({"employee": emp.employee, "employee_name": emp.employee_name, "status": "Error", "error_message": str(e), "payable_amount": 0.0})

    return {
        "payroll_entry": payroll_entry_id, "currency": doc.currency, "total_payable": total_payable,
        "employee_count": processed_count, "calculation_method": "On-the-fly Dynamic Calculation",
        "employee_breakdown": breakdown, "last_error": last_error
    }


def get_payroll_entry_list(filters, page=1, page_size=20, search="", sort_by="creation", sort_order="desc"):
    start = (page - 1) * page_size
    fields = ["name", "company", "start_date", "end_date", "payroll_frequency", "status", "currency"]
    
    or_filters = []
    if search: or_filters.append(["name", "like", f"%{search}%"])

    allowed_sort_fields = ["name", "creation", "start_date", "end_date", "status", "company", "payroll_frequency"]
    if sort_by not in allowed_sort_fields: sort_by = "creation"
    
    sort_order = "desc" if sort_order.lower() == "desc" else "asc"
    order_by_string = f"{sort_by} {sort_order}"

    entries = frappe.get_all("Payroll Entry", filters=filters, or_filters=or_filters, fields=fields, order_by=order_by_string, limit_start=start, limit_page_length=page_size)

    for entry in entries:
        try:
            summary = calculate_payroll_entry_payable(entry.name)
            entry["total_payable"] = summary.get("total_payable", 0.0)
            entry["employee_count"] = summary.get("employee_count", 0)
            if summary.get("last_error"): entry["last_error"] = summary.get("last_error")
        except Exception as e:
            entry["total_payable"] = 0.0
            entry["employee_count"] = 0
            entry["last_error"] = f"Fatal Loop Error: {str(e)}"

    total_count = len(frappe.get_all("Payroll Entry", filters=filters, or_filters=or_filters, pluck="name"))
    total_pages = math.ceil(total_count / page_size) if page_size else 1

    return entries, total_count, total_pages


def get_payroll_entry_details(payroll_entry_id):
    doc = frappe.get_doc("Payroll Entry", payroll_entry_id)
    raw_doc = doc.as_dict()
    
    doc_dict = extract_allowed_fields(raw_doc, PAYROLL_ENTRY_FIELDS)
    financial_summary = calculate_payroll_entry_payable(payroll_entry_id)

    doc_dict["financial_summary"] = {
        "total_payable": financial_summary.get("total_payable"),
        "employee_count": financial_summary.get("employee_count"),
        "calculation_method": financial_summary.get("calculation_method")
    }
    
    breakdown_list = financial_summary.get("employee_breakdown", [])
    breakdown_map = {b["employee"]: b for b in breakdown_list}

    doc_dict["employees"] = []
    if "employees" in raw_doc:
        for emp in raw_doc["employees"]:
            emp_id = emp.get("employee")
            clean_emp = {
                "employee": emp_id,
                "employee_name": emp.get("employee_name"),
                "department": emp.get("department"),
                "designation": emp.get("designation"),
                "salary_slip_details": breakdown_map.get(emp_id)
            }
            doc_dict["employees"].append(clean_emp)
    
    if financial_summary.get("last_error"):
        doc_dict["last_error"] = financial_summary.get("last_error")

    return doc_dict