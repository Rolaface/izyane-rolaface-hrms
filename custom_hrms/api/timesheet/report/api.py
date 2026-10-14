import frappe
from frappe.utils import cint, getdate

from custom_hrms.api.timesheet.report.service import (
    build_summary,
    get_report_data,
    group_report_data,
    parse_group_by,
)

DEFAULT_PAGE = 1
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 500
UNPAGED = 0


def _parse_list(value, label):
    if isinstance(value, str):
        value = frappe.parse_json(value)

    if value is not None and not isinstance(value, (list, tuple)):
        frappe.throw(f"{label} must be provided as a list.")

    return value


def _resolve_pagination(page, page_size):
    page = max(cint(page) or DEFAULT_PAGE, DEFAULT_PAGE)
    page_size = cint(page_size)

    if page_size < UNPAGED:
        page_size = DEFAULT_PAGE_SIZE

    return page, min(page_size, MAX_PAGE_SIZE) if page_size else UNPAGED


def _paginate(rows, page, page_size):
    total = len(rows)

    if page_size == UNPAGED:
        return rows, {
            "page": DEFAULT_PAGE,
            "page_size": total,
            "total": total,
            "total_pages": DEFAULT_PAGE,
            "has_next": False,
            "has_prev": False,
        }

    total_pages = max(DEFAULT_PAGE, -(-total // page_size))
    start = (page - 1) * page_size

    return rows[start : start + page_size], {
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > DEFAULT_PAGE,
    }


@frappe.whitelist()
def get_timesheet_report(
    from_date=None,
    to_date=None,
    customer=None,
    project=None,
    projects=None,
    employee=None,
    employees=None,
    employee_group=None,
    status=None,
    include_non_billable=1,
    group_by=None,
    page=DEFAULT_PAGE,
    page_size=DEFAULT_PAGE_SIZE,
):
    """
    group_by: none (flat entry list) or one or more levels, in order.
      "project"                 -> Project
      "project,employee"        -> Project > Employee
      "employee,project,date"   -> Employee > Project > Date
    Allowed levels: employee, project, date, month. A level can be used once.
    When grouped, `data` is a nested tree and pagination applies to the
    top-level groups.
    """


    if not from_date or not to_date:
        frappe.throw("From Date and To Date are required.")

    from_date = getdate(from_date)
    to_date = getdate(to_date)

    if from_date > to_date:
        frappe.throw("From Date cannot be after To Date.")

    group_levels = parse_group_by(group_by)

    filters = {
        "from_date": from_date,
        "to_date": to_date,
        "customer": customer,
        "project": project,
        "projects": _parse_list(projects, "Projects"),
        "employee": employee,
        "employees": _parse_list(employees, "Employees"),
        "employee_group": employee_group,
        "status": status,
        "include_non_billable": include_non_billable,
        "group_by": group_levels,
    }

    rows = get_report_data(filters)
    summary = build_summary(rows)

    data = group_report_data(rows, group_levels) if group_levels else rows

    page, page_size = _resolve_pagination(page, page_size)
    page_data, pagination = _paginate(data, page, page_size)

    return {
        "success": True,
        "filters": filters,
        "summary": summary,
        "group_by": group_levels,
        "data": page_data,
        "pagination": pagination,
    }