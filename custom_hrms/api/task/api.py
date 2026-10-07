import frappe

from custom_hrms.api.task.service import get_project_assignees_data


@frappe.whitelist()
def get_project_assignees(project=None):
    if not project:
        frappe.throw("Project is required", frappe.MandatoryError)

    return get_project_assignees_data(project)