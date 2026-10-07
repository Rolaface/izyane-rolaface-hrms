import frappe


def get_project_assignees_data(project):
    if not frappe.db.exists("Project", project):
        frappe.throw(f"Project {project} does not exist")

    return frappe.get_all(
        "Project User",
        filters={
            "parent": project,
            "parenttype": "Project",
            "parentfield": "users",
            "hide_timesheets": 0,
        },
        fields=[
            "user",
            "email",
            "full_name",
        ],
        order_by="full_name asc",
    )