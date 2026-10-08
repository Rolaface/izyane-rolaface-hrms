import frappe

from frappe.utils import add_days, date_diff, get_datetime, getdate


CANCELLED_DOCSTATUS = 2
DRAFT_STATUS = "Draft"

MAX_RANGE_DAYS = 366

DAY_FORMAT = "%Y-%m-%d"
MONTH_FORMAT = "%Y-%m"

BUCKET_FORMATS = {
    "day": DAY_FORMAT,
    "month": MONTH_FORMAT,
}

DETAIL_FIELDS = [
    "parent",
    "from_time",
    "hours",
    "docstatus",
    "project",
    "project_name",
    "task",
    "activity_type",
    "description",
]


def add_after(data, key, new_key, value):
    new = frappe._dict()

    for k, v in data.items():
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

    return {
        r.name: r.project_name
        for r in rows
    }


def get_task_names(task_ids):
    if not task_ids:
        return {}

    rows = frappe.get_list(
        "Task",
        filters={"name": ["in", task_ids]},
        fields=["name", "subject"],
    )

    return {
        r.name: r.subject
        for r in rows
    }


def get_link_value(doctype, name, fieldname):
    if not name or not frappe.has_permission(
        doctype,
        "read",
        doc=name,
    ):
        return None

    return frappe.db.get_value(
        doctype,
        name,
        fieldname,
    )


def add_row_names(rows, project_names, task_names):
    result = []

    for row in rows:
        project = row.get("project")

        if project:
            project_name = (
                project_names.get(project)
                or row.get("project_name")
            )

            if project_name:
                row = add_after(
                    row,
                    "project",
                    "project_name",
                    project_name,
                )

        task = row.get("task")

        if task:
            task_name = task_names.get(task)

            if task_name:
                row = add_after(
                    row,
                    "task",
                    "task_name",
                    task_name,
                )

        result.append(row)

    return result


def get_timesheet_with_names(name):
    doc = frappe.get_doc("Timesheet", name)

    doc.check_permission("read")
    doc.apply_fieldlevel_read_permissions()

    data = doc.as_dict(no_nulls=True)

    rows = data.get("time_logs", [])

    project_names = get_project_names(
        list(
            {
                r["project"]
                for r in rows
                if r.get("project")
            }
        )
    )

    task_names = get_task_names(
        list(
            {
                r["task"]
                for r in rows
                if r.get("task")
            }
        )
    )

    data["time_logs"] = add_row_names(
        rows,
        project_names,
        task_names,
    )

    customer_name = get_link_value(
        "Customer",
        data.get("customer"),
        "customer_name",
    )

    if customer_name:
        data = add_after(
            data,
            "customer",
            "customer_name",
            customer_name,
        )

    parent_project_name = get_link_value(
        "Project",
        data.get("parent_project"),
        "project_name",
    )

    if parent_project_name:
        data = add_after(
            data,
            "parent_project",
            "parent_project_name",
            parent_project_name,
        )

    return data


def validate_range(from_date, to_date):
    if getdate(to_date) < getdate(from_date):
        frappe.throw(
            "To Date cannot be before From Date",
            frappe.ValidationError,
        )

    if date_diff(to_date, from_date) >= MAX_RANGE_DAYS:
        frappe.throw(
            f"Date range cannot exceed {MAX_RANGE_DAYS} days",
            frappe.ValidationError,
        )


def day_bounds(from_date, to_date):
    return (
        getdate(from_date),
        add_days(getdate(to_date), 1),
    )


def get_own_employees():
    return frappe.get_all(
        "Employee",
        filters={
            "user_id": frappe.session.user,
        },
        pluck="name",
    )


def get_visible_sheets(
    from_date,
    to_date,
    employees=None,
    exclude_draft=False,
):
    if employees is not None and not employees:
        return {}

    filters = {
        "start_date": ["<=", to_date],
        "end_date": [">=", from_date],
        "docstatus": ["!=", CANCELLED_DOCSTATUS],
    }

    if employees is not None:
        filters["employee"] = ["in", employees]

    if exclude_draft:
        filters["status"] = ["!=", DRAFT_STATUS]

    rows = frappe.get_list(
        "Timesheet",
        filters=filters,
        fields=[
            "name",
            "employee",
            "employee_name",
            "status",
            "docstatus",
        ],
        limit_page_length=0,
    )

    return {
        r.name: r
        for r in rows
    }


def get_sheet_details(
    sheet_names,
    from_date,
    to_date,
    fields,
    project=None,
    activity_type=None,
):
    start, end = day_bounds(
        from_date,
        to_date,
    )

    filters = [
        ["parent", "in", sheet_names],
        ["from_time", ">=", start],
        ["from_time", "<", end],
        ["docstatus", "!=", CANCELLED_DOCSTATUS],
    ]

    if project:
        filters.append(
            ["project", "=", project]
        )

    if activity_type:
        filters.append(
            ["activity_type", "=", activity_type]
        )

    return frappe.get_all(
        "Timesheet Detail",
        filters=filters,
        fields=fields,
        order_by="from_time asc",
        parent_doctype="Timesheet",
        limit_page_length=0,
    )


def get_calendar_summary(
    from_date,
    to_date,
    granularity="day",
    employees=None,
    exclude_draft=False,
    project=None,
    activity_type=None,
):
    bucket_format = BUCKET_FORMATS.get(granularity)

    if not bucket_format:
        frappe.throw(
            f"Invalid granularity: {granularity}",
            frappe.ValidationError,
        )

    validate_range(
        from_date,
        to_date,
    )

    sheets = get_visible_sheets(
        from_date,
        to_date,
        employees,
        exclude_draft,
    )

    if not sheets:
        return []

    details = get_sheet_details(
        list(sheets),
        from_date,
        to_date,
        ["parent", "from_time", "hours"],
        project,
        activity_type,
    )

    cells = {}

    for detail in details:
        sheet = sheets[detail.parent]

        bucket = get_datetime(
            detail.from_time
        ).strftime(bucket_format)

        cell = cells.setdefault(
            (sheet.employee, bucket),
            {
                "employee": sheet.employee,
                "employee_name": (
                    sheet.employee_name
                    or sheet.employee
                ),
                "date": bucket,
                "approved_hours": 0,
                "draft_hours": 0,
                "draft_sheets": [],
            },
        )

        if sheet.docstatus == 1:
            cell["approved_hours"] += detail.hours

        elif sheet.status == DRAFT_STATUS:
            cell["draft_hours"] += detail.hours

            if sheet.name not in cell["draft_sheets"]:
                cell["draft_sheets"].append(
                    sheet.name
                )

    return list(cells.values())


def get_calendar_details(
    from_date,
    to_date,
    mine=False,
):
    validate_range(
        from_date,
        to_date,
    )

    employees = (
        get_own_employees()
        if mine
        else None
    )

    sheets = get_visible_sheets(
        from_date,
        to_date,
        employees,
    )

    if not sheets:
        return []

    details = get_sheet_details(
        list(sheets),
        from_date,
        to_date,
        DETAIL_FIELDS,
    )

    rows = []

    for detail in details:
        sheet = sheets[
            detail.pop("parent")
        ]

        rows.append(
            frappe._dict(
                detail,
                timesheet=sheet.name,
                employee=(
                    sheet.employee_name
                    or sheet.employee
                ),
                status=sheet.status,
                date=get_datetime(
                    detail.from_time
                ).strftime(DAY_FORMAT),
            )
        )

    project_names = get_project_names(
        list(
            {
                r.project
                for r in rows
                if r.project
            }
        )
    )

    task_names = get_task_names(
        list(
            {
                r.task
                for r in rows
                if r.task
            }
        )
    )

    return add_row_names(
        rows,
        project_names,
        task_names,
    )