import frappe

from custom_hrms.api.timesheet.service import get_timesheet_with_names


@frappe.whitelist()
def get_timesheet(name=None):
    if not name:
        frappe.throw("Timesheet name is required", frappe.MandatoryError)
    frappe.response["data"] = get_timesheet_with_names(name)