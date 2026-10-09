import frappe
from frappe.utils import cint

from custom_hrms.api.timesheet.service import (
    get_calendar_details,
    get_calendar_summary,
    get_timesheet_with_names,
)


@frappe.whitelist()
def get_timesheet(name=None):
    if not name:
        frappe.throw("Timesheet name is required", frappe.MandatoryError)
    frappe.response["data"] = get_timesheet_with_names(name)


@frappe.whitelist()
def get_timesheet_calendar_summary(
    from_date,
    to_date,
    granularity="day",
    employees=None,
    exclude_draft=0,
    project=None,
    activity_type=None,
):
    frappe.response["data"] = get_calendar_summary(
        from_date,
        to_date,
        granularity,
        frappe.parse_json(employees) if employees else None,
        bool(cint(exclude_draft)),
        project,
        activity_type,
    )


@frappe.whitelist()
def get_timesheet_calendar_details(from_date, to_date, mine=0):
    frappe.response["data"] = get_calendar_details(
        from_date, to_date, bool(cint(mine))
    )