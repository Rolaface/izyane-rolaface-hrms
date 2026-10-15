import frappe


@frappe.whitelist()
def get_project_details(project_name):
    if not project_name:
        frappe.throw("Project is required")

    project = frappe.get_doc("Project", project_name)

    return {
        "name": project.name,
        "project_name": project.project_name,
        "status": project.status,
        "company": project.company,
        "users": [
            {
                "user": row.user,
                "email": row.email,
                "full_name": row.full_name,
                "hide_timesheets": row.hide_timesheets,
            }
            for row in project.users
        ],
    }