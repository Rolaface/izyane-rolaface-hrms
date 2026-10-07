import frappe


def add_after(d, key, new_key, value):
    new = frappe._dict()
    for k, v in d.items():
        if k == new_key:
            continue
        new[k] = v
        if k == key:
            new[new_key] = value
    return new


def get_project_names(project_ids):
    if not project_ids:
        return {}
    rows = frappe.get_list(
        "Project",
        filters={"name": ["in", project_ids]},
        fields=["name", "project_name"],
    )
    return {r.name: r.project_name for r in rows}


def get_task_names(task_ids):
    if not task_ids:
        return {}
    rows = frappe.get_list(
        "Task",
        filters={"name": ["in", task_ids]},
        fields=["name", "subject"],
    )
    return {r.name: r.subject for r in rows}


def get_link_value(doctype, name, fieldname):
    if not name or not frappe.has_permission(doctype, "read", doc=name):
        return None
    return frappe.db.get_value(doctype, name, fieldname)


def add_row_names(rows, project_names, task_names):
    result = []
    for row in rows:
        project = row.get("project")
        if project:
            project_name = project_names.get(project) or row.get("project_name")
            if project_name:
                row = add_after(row, "project", "project_name", project_name)

        task = row.get("task")
        if task:
            task_name = task_names.get(task)
            if task_name:
                row = add_after(row, "task", "task_name", task_name)

        result.append(row)
    return result


def get_timesheet_with_names(name):
    doc = frappe.get_doc("Timesheet", name)
    doc.check_permission("read")
    doc.apply_fieldlevel_read_permissions()

    data = doc.as_dict(no_nulls=True)
    rows = data.get("time_logs", [])

    project_names = get_project_names(
        list({r["project"] for r in rows if r.get("project")})
    )
    task_names = get_task_names(
        list({r["task"] for r in rows if r.get("task")})
    )
    data["time_logs"] = add_row_names(rows, project_names, task_names)

    customer_name = get_link_value("Customer", data.get("customer"), "customer_name")
    if customer_name:
        data = add_after(data, "customer", "customer_name", customer_name)

    parent_project_name = get_link_value(
        "Project", data.get("parent_project"), "project_name"
    )
    if parent_project_name:
        data = add_after(
            data, "parent_project", "parent_project_name", parent_project_name
        )

    return data