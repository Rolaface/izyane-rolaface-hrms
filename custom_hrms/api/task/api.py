import frappe

from custom_hrms.api.task.constants import DEFAULT_PAGE_SIZE
from custom_hrms.api.task.service import (
    get_assigned_tasks_data,
    get_project_assignees_data,
)


@frappe.whitelist()
def get_project_assignees(project=None):
    if not project:
        frappe.throw("Project is required", frappe.MandatoryError)

    return get_project_assignees_data(project)


@frappe.whitelist()
def get_assigned_tasks(
    employee=None,
    project=None,
    status=None,
    priority=None,
    search=None,
    include_groups=1,
    include_cancelled=1,
    assignment_status="Open",
    page=1,
    page_size=DEFAULT_PAGE_SIZE,
):
    return get_assigned_tasks_data(
        employee=employee,
        project=project,
        status=status,
        priority=priority,
        search=search,
        include_groups=include_groups,
        include_cancelled=include_cancelled,
        assignment_status=assignment_status,
        page=page,
        page_size=page_size,
    )