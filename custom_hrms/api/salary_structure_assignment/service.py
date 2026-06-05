import frappe
from frappe.utils import getdate, today


def _fetch_assignments(employee: str, company: str, from_date: str, to_date: str) -> list:
    filters = [
        ["docstatus", "=", 1],
        ["employee", "=", employee],
    ]

    if company:
        filters.append(["company", "=", company])
    if from_date:
        filters.append(["from_date", ">=", from_date])
    if to_date:
        filters.append(["from_date", "<=", to_date])

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


_STATUS_PRIORITY = {"Active": 0, "Upcoming": 1, "Inactive": 2}


def _sort_records(records: list) -> list:
    def sort_key(record):
        from_date = getdate(record["from_date"])
        status    = record["status"]

        if status == "Upcoming":
            return (_STATUS_PRIORITY.get(status, 99), from_date.toordinal())

        return (_STATUS_PRIORITY.get(status, 99), -from_date.toordinal())

    return sorted(records, key=sort_key)


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


def get_assignment_list(
    employee:  str,
    company:   str,
    from_date: str,
    to_date:   str,
    page:      int,
    page_size: int,
) -> dict:
    records = _fetch_assignments(employee, company, from_date, to_date)
    records = _assign_statuses(records)
    records = _sort_records(records)

    return _paginate(records, page, page_size)


def sync_condition_and_formula(salary_component):
    doc = frappe.get_doc("Salary Component", salary_component)

    structures = frappe.get_all(
        "Salary Detail",
        filters={
            "salary_component": salary_component,
            "parenttype": "Salary Structure",
        },
        distinct=True,
        pluck="parent",
    )

    if not structures:
        return {
            "salary_component": salary_component,
            "synced_structures": 0,
        }

    doc.update_salary_structures(
        structures=structures,
        field="condition",
        value=doc.condition or "",
    )

    doc.update_salary_structures(
        structures=structures,
        field="formula",
        value=doc.formula or "",
    )

    return {
        "salary_component": salary_component,
        "synced_structures": len(structures),
    }