import math
import frappe
from frappe import _
from hrms.hr.doctype.appraisal_cycle.appraisal_cycle import get_appraisal_cycle_summary
from .utils import extract_allowed_fields, APPRAISAL_CYCLE_FIELDS, APPRAISAL_FIELDS, get_error_response


def get_eligible_employees(filters: dict, page=1, page_size=20):
    start = (page - 1) * page_size
    fields = ["name", "employee_name", "department", "designation", "branch", "image"]

    employees = frappe.get_all(
        "Employee",
        filters=filters,
        fields=fields,
        order_by="employee_name asc",
        limit_start=start,
        limit_page_length=page_size
    )

    total_count = frappe.db.count("Employee", filters=filters)
    total_pages = math.ceil(total_count / page_size) if page_size else 1

    return employees, total_count, total_pages

def run_appraisal_cycle(appraisal_cycle_id: str) -> dict:
    try:
        doc = frappe.get_doc("Appraisal Cycle", appraisal_cycle_id)

        if doc.docstatus == 2:
            return get_error_response(_("Cannot run a cancelled Appraisal Cycle."))
            
        if doc.status == "Completed":
            return get_error_response(_("Cannot create appraisals for a Completed Appraisal Cycle."))

        if doc.status != "In Progress":
            if hasattr(doc, "start"):
                doc.start()
            else:
                doc.db_set("status", "In Progress")
            doc.reload()

        if not doc.get("appraisees"):
            doc.set_employees()
            doc.save()
            doc.reload()

        doc.create_appraisals()
        doc.reload()

        return {
            "status": "success",
            "message": _("Appraisal creation triggered successfully."),
            "appraisal_cycle": doc.name,
            "cycle_status": doc.status,
            "appraisee_count": len(doc.get("appraisees", []))
        }

    except frappe.ValidationError as e:
        frappe.db.rollback()
        return get_error_response(str(e))
    except Exception as e:
        frappe.db.rollback()
        return get_error_response(f"Failed to start cycle: {str(e)}", frappe.get_traceback())


def get_appraisal_cycle_list(filters: dict, page=1, page_size=20, search="", sort_by="creation", sort_order="desc"):
    start = (page - 1) * page_size
    fields = ["name", "company", "start_date", "end_date", "status", "department", "branch"]
    
    or_filters = []
    if search:
        or_filters.append(["name", "like", f"%{search}%"])

    allowed_sort_fields = ["name", "creation", "start_date", "end_date", "status", "company"]
    if sort_by not in allowed_sort_fields: sort_by = "creation"
    
    sort_order_str = "desc" if sort_order.lower() == "desc" else "asc"
    
    entries = frappe.get_all(
        "Appraisal Cycle", 
        filters=filters, 
        or_filters=or_filters, 
        fields=fields, 
        order_by=f"{sort_by} {sort_order_str}", 
        limit_start=start, 
        limit_page_length=page_size
    )

    for entry in entries:
        try:
            summary = get_appraisal_cycle_summary(entry.name)
            entry.update(summary)
        except Exception:
                pass 

    total_count = frappe.db.count("Appraisal Cycle", filters=filters, or_filters=or_filters)
    total_pages = math.ceil(total_count / page_size) if page_size else 1

    return entries, total_count, total_pages


def get_appraisal_cycle_details(appraisal_cycle_id: str) -> dict:
    doc = frappe.get_doc("Appraisal Cycle", appraisal_cycle_id)
    raw_doc = doc.as_dict()
    
    doc_dict = extract_allowed_fields(raw_doc, APPRAISAL_CYCLE_FIELDS)
    
    try:
        doc_dict["summary"] = get_appraisal_cycle_summary(appraisal_cycle_id)
    except Exception as e:
        doc_dict["summary"] = {}
        doc_dict["summary_error"] = str(e)

    appraisals = frappe.get_all(
        "Appraisal",
        filters={"appraisal_cycle": appraisal_cycle_id, "docstatus": ("<", 2)},
        fields=APPRAISAL_FIELDS
    )
    doc_dict["appraisals"] = [extract_allowed_fields(a, APPRAISAL_FIELDS) for a in appraisals]

    return doc_dict