import frappe
from frappe.utils import getdate, today




def _fetch_assignments(employee: str, company: str) -> list:
    filters = {
        "docstatus": 1,
        "employee": employee,
    }

    if company:
        filters["company"] = company

    return frappe.get_all(
        "Salary Structure Assignment",
        filters=filters,
        fields=[
            "name",
            "employee",
            "employee_name",
            "company",
            "salary_structure",
            "from_date",
            "currency",
            "creation",
            "base",
            "modified",
        ],
        order_by="from_date desc",
    )




def _assign_statuses(records: list) -> list:
    current_date = getdate(today())

    # Find the active record — latest from_date that is on or before today
    effective_records = [
        r for r in records
        if r.get("from_date") and getdate(r["from_date"]) <= current_date
    ]

    active_record = None
    if effective_records:
        active_record = max(
            effective_records,
            key=lambda r: getdate(r["from_date"]),
        )

    for record in records:
        from_date = getdate(record["from_date"])

        if active_record and record["name"] == active_record["name"]:
            record["status"] = "Active"
        elif from_date > current_date:
            record["status"] = "Upcoming"
        else:
            record["status"] = "Inactive"

    return records




def _apply_search(records: list, search: str) -> list:
    if not search:
        return records

    return [
        r for r in records
        if search in (r.get("employee", "") or "").lower()
        or search in (r.get("employee_name", "") or "").lower()
        or search in (r.get("salary_structure", "") or "").lower()
    ]




_STATUS_PRIORITY = {"Active": 0, "Upcoming": 1, "Inactive": 2}

def _sort_records(records: list) -> list:
    return sorted(
        records,
        key=lambda r: (
            _STATUS_PRIORITY.get(r["status"], 99),
            -getdate(r["from_date"]).toordinal(),
        ),
    )



def _paginate(records: list, page: int, page_size: int) -> dict:
    total_count = len(records)
    total_pages = max((total_count + page_size - 1) // page_size, 1)

    start = (page - 1) * page_size
    end   = start + page_size

    return {
        "data": records[start:end],
        "pagination": {
            "page":        page,
            "page_size":   page_size,
            "total":       total_count,
            "total_pages": total_pages,
            "has_next":    page < total_pages,
            "has_prev":    page > 1,
        },
    }



def get_assignment_list(employee: str, company: str, search: str, page: int, page_size: int) -> dict:
    records = _fetch_assignments(employee, company)
    records = _assign_statuses(records)
    records = _apply_search(records, search)
    records = _sort_records(records)

    return _paginate(records, page, page_size)