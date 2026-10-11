import frappe
from frappe import _
from frappe.utils import cint

from custom_hrms.api.task.constants import (
    ASSIGNMENT_STATUSES,
    BASE_TASK_FIELDS,
    BATCH_SIZE,
    DEFAULT_PAGE_SIZE,
    MAX_DEPTH,
    MAX_PAGE_SIZE,
    PRIVILEGED_ROLES,
)


def _as_list(value):
    if value is None or value == "":
        return []
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return []
        if stripped.startswith("["):
            try:
                parsed = frappe.parse_json(stripped)
            except Exception:
                frappe.throw(_("Invalid list filter"))
            if not isinstance(parsed, list):
                frappe.throw(_("List filter must be a JSON array"))
            return [item for item in parsed if item not in (None, "")]
        return [item.strip() for item in stripped.split(",") if item.strip()]
    if isinstance(value, (list, tuple, set)):
        return [item for item in value if item not in (None, "")]
    frappe.throw(_("Unsupported filter format"))


def _chunks(items, size=BATCH_SIZE):
    values = list(items)
    for start in range(0, len(values), size):
        yield values[start : start + size]


def _is_all_tasks_mode(employee, mine):
    return not employee and not mine


def _resolve_target_user(employee):
    session_user = frappe.session.user
    if session_user == "Guest":
        frappe.throw(_("Login required"), frappe.AuthenticationError)

    if not employee:
        return session_user

    target_user = employee
    if not frappe.db.exists("User", employee):
        if not frappe.db.exists("Employee", employee):
            frappe.throw(_("Employee {0} not found").format(employee), frappe.DoesNotExistError)
        if not frappe.has_permission("Employee", "read", doc=employee):
            frappe.throw(_("Not permitted to read this employee"), frappe.PermissionError)
        target_user = frappe.db.get_value("Employee", employee, "user_id")
        if not target_user:
            frappe.throw(_("Employee has no linked user"), frappe.DoesNotExistError)

    if target_user != session_user and not (PRIVILEGED_ROLES & set(frappe.get_roles(session_user))):
        frappe.throw(_("Not permitted to view another employee's assignments"), frappe.PermissionError)

    return target_user


def _validate_project(project):
    if not project:
        return
    if not frappe.db.exists("Project", project):
        frappe.throw(_("Project {0} does not exist").format(project), frappe.DoesNotExistError)
    if not frappe.has_permission("Project", "read", doc=project):
        frappe.throw(_("Not permitted to read this project"), frappe.PermissionError)


def _resolve_assignment_statuses(assignment_status):
    requested = _as_list(assignment_status)
    if not requested or "All" in requested:
        return list(ASSIGNMENT_STATUSES)

    invalid = [value for value in requested if value not in ASSIGNMENT_STATUSES]
    if invalid:
        frappe.throw(_("Invalid assignment status: {0}").format(", ".join(invalid)))
    return requested


def _task_fields():
    fields = list(BASE_TASK_FIELDS)
    if frappe.get_meta("Task").has_field("custom_activity_type"):
        fields.append("custom_activity_type")
    return fields


def _task_filters(project, statuses, priorities, include_groups, include_cancelled):
    filters = []

    if project:
        filters.append(["project", "=", project])
    if statuses:
        filters.append(["status", "in", statuses])
    if priorities:
        filters.append(["priority", "in", priorities])
    if not include_groups:
        filters.append(["is_group", "=", 0])
    if not include_cancelled and "Cancelled" not in statuses:
        filters.append(["status", "!=", "Cancelled"])

    return filters


def _fetch_assignments(target_user, statuses):
    assignments = []
    start = 0

    while True:
        batch = frappe.get_list(
            "ToDo",
            filters={
                "reference_type": "Task",
                "allocated_to": target_user,
                "status": ["in", statuses],
            },
            fields=["name", "reference_name", "status", "priority", "allocated_to", "assigned_by"],
            order_by="modified desc, name desc",
            start=start,
            page_length=BATCH_SIZE,
        )
        assignments.extend(batch)
        if len(batch) < BATCH_SIZE:
            break
        start += len(batch)

    return assignments


def _fetch_assignments_for_tasks(task_names, statuses):
    assignments = []

    for batch_names in _chunks(task_names):
        batch = frappe.get_list(
            "ToDo",
            filters={
                "reference_type": "Task",
                "reference_name": ["in", batch_names],
                "status": ["in", statuses],
            },
            fields=[
                "name",
                "reference_name",
                "status",
                "priority",
                "allocated_to",
                "assigned_by",
            ],
            order_by="modified desc, name desc",
            page_length=BATCH_SIZE,
        )
        assignments.extend(batch)

    return assignments


def _fetch_tasks(names, fields, extra_filters=None):
    rows = []
    unique_names = list(dict.fromkeys(name for name in names if name))

    for batch in _chunks(unique_names):
        filters = [["name", "in", batch]]
        if extra_filters:
            filters.extend(extra_filters)
        rows.extend(
            frappe.get_list(
                "Task",
                filters=filters,
                fields=fields,
                limit_start=0,
                limit_page_length=len(batch),
            )
        )

    return rows


def _fetch_all_tasks(fields, filters):
    rows = []
    start = 0

    while True:
        batch = frappe.get_list(
            "Task",
            filters=filters,
            fields=fields,
            start=start,
            page_length=BATCH_SIZE,
            order_by="modified desc, name desc",
        )
        rows.extend(batch)
        if len(batch) < BATCH_SIZE:
            break
        start += len(batch)

    return rows


def _group_by_task(assignments):
    grouped = {}
    for assignment in assignments:
        task_name = assignment.get("reference_name")
        if task_name:
            grouped.setdefault(task_name, []).append(assignment)
    return grouped


def _load_scope(is_all_tasks_mode, target_user, todo_statuses, fields, filters):
    if is_all_tasks_mode:
        task_rows = _fetch_all_tasks(fields, filters)
        assignments = _fetch_assignments_for_tasks(
            [row["name"] for row in task_rows], todo_statuses
        )
        return task_rows, _group_by_task(assignments)

    assignments_by_task = _group_by_task(_fetch_assignments(target_user, todo_statuses))
    if not assignments_by_task:
        return [], {}

    return _fetch_tasks(assignments_by_task.keys(), fields, filters), assignments_by_task


def _load_ancestors(tasks, fields):
    ancestors = {}
    unresolved = set()
    pending = {task["parent_task"] for task in tasks.values() if task.get("parent_task")} - tasks.keys()
    depth = 0

    while pending and depth < MAX_DEPTH:
        found_rows = _fetch_tasks(pending, fields)
        found = {row["name"]: row for row in found_rows}
        unresolved.update(pending - found.keys())
        ancestors.update(found)
        pending = (
            {row["parent_task"] for row in found.values() if row.get("parent_task")}
            - tasks.keys()
            - ancestors.keys()
            - unresolved
        )
        depth += 1

    return ancestors


def _build_chain(task, universe):
    chain = []
    seen = {task["name"]}
    parent = task.get("parent_task")
    hidden = False

    while parent:
        node = universe.get(parent)
        if node is None:
            hidden = True
            break
        if parent in seen or len(chain) >= MAX_DEPTH:
            break
        chain.append(node)
        seen.add(parent)
        parent = node.get("parent_task")

    chain.reverse()
    return chain, hidden


def _priority_rank():
    field = frappe.get_meta("Task").get_field("priority")
    options = [option for option in (field.options or "").splitlines() if option]
    return {value: len(options) - index - 1 for index, value in enumerate(options)}


def _sorted_siblings(rows, priority_rank):
    rows = sorted(rows, key=lambda row: str(row.get("modified") or ""), reverse=True)
    return sorted(rows, key=lambda row: priority_rank.get(row.get("priority"), len(priority_rank)))


def _depth_first_order(nodes, priority_rank):
    children = {}
    roots = []

    for node in nodes.values():
        parent = node.get("parent_task")
        if parent in nodes:
            children.setdefault(parent, []).append(node)
        else:
            roots.append(node)

    ordered_names = []
    stack = list(reversed(_sorted_siblings(roots, priority_rank)))

    while stack:
        node = stack.pop()
        ordered_names.append(node["name"])
        stack.extend(reversed(_sorted_siblings(children.get(node["name"], []), priority_rank)))

    return ordered_names


def _matches_search(task, chain, search_term):
    if not search_term:
        return True

    searchable_values = [task.get("name") or "", task.get("subject") or ""]
    searchable_values.extend(ancestor.get("subject") or "" for ancestor in chain)
    return any(search_term in value.lower() for value in searchable_values)


def _filter_matches(tasks, chains, search):
    search_term = (search or "").strip().lower()
    return {
        name: task
        for name, task in tasks.items()
        if _matches_search(task, chains[name][0], search_term)
    }


def _order_matches(matched, chains):
    display_nodes = dict(matched)
    for name in matched:
        for ancestor in chains[name][0]:
            display_nodes.setdefault(ancestor["name"], ancestor)

    ordered_names = _depth_first_order(display_nodes, _priority_rank())
    positions = {name: index for index, name in enumerate(ordered_names)}

    blocks = []
    for name in ordered_names:
        if display_nodes[name].get("parent_task") in display_nodes and blocks:
            blocks[-1].append(name)
        else:
            blocks.append([name])

    root_blocks = [
        [name for name in block if name in matched]
        for block in blocks
    ]
    root_blocks = [block for block in root_blocks if block]

    return positions, root_blocks


def _public_row(task, chain, has_hidden_ancestor, assignments, context_only):
    return {
        "name": task["name"],
        "subject": task.get("subject"),
        "project": task.get("project"),
        "parent_task": task.get("parent_task"),
        "is_group": cint(task.get("is_group")),
        "status": task.get("status"),
        "priority": task.get("priority"),
        "custom_activity_type": task.get("custom_activity_type"),
        "depth": len(chain),
        "ancestors": [
            {"name": ancestor["name"], "subject": ancestor.get("subject")}
            for ancestor in chain
        ],
        "has_hidden_ancestor": has_hidden_ancestor,
        "assignments": [
            {
                "todo": assignment["name"],
                "status": assignment["status"],
                "priority": assignment.get("priority"),
                "allocated_to": assignment["allocated_to"],
                "assigned_by": assignment.get("assigned_by"),
            }
            for assignment in assignments
        ],
        "is_assigned": bool(assignments) and not context_only,
        "context_only": context_only,
    }


def _empty_response(page, page_size, target_user, assignment_statuses):
    return {
        "data": [],
        "context": [],
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": 0,
            "total_pages": 1,
            "total_tasks": 0,
            "has_more": False,
        },
        "meta": {
            "user": target_user,
            "assignment_status": assignment_statuses,
        },
    }


def _build_page(page_names, matched, chains, universe, positions, assignments_by_task):
    page_name_set = set(page_names)

    data = [
        _public_row(
            task=matched[name],
            chain=chains[name][0],
            has_hidden_ancestor=chains[name][1],
            assignments=assignments_by_task.get(name, []),
            context_only=False,
        )
        for name in page_names
    ]

    context_names = {
        ancestor["name"]
        for name in page_names
        for ancestor in chains[name][0]
        if ancestor["name"] not in page_name_set
    }

    context = []
    for name in sorted(context_names, key=lambda value: positions.get(value, 0)):
        task = universe[name]
        chain, has_hidden_ancestor = _build_chain(task, universe)
        context.append(
            _public_row(
                task=task,
                chain=chain,
                has_hidden_ancestor=has_hidden_ancestor,
                assignments=[],
                context_only=True,
            )
        )

    return data, context


@frappe.whitelist()
def get_project_assignees_data(project):
    if not project:
        frappe.throw(_("Project {0} does not exist").format(project), frappe.DoesNotExistError)
    _validate_project(project)

    return frappe.get_all(
        "Project User",
        filters={
            "parent": project,
            "parenttype": "Project",
            "parentfield": "users",
            "hide_timesheets": 0,
        },
        fields=["user", "email", "full_name"],
        order_by="full_name asc",
    )


@frappe.whitelist()
def get_assigned_tasks_data(
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
    mine=0,
):
    mine = bool(cint(mine))
    is_all_tasks_mode = _is_all_tasks_mode(employee, mine)
    target_user = _resolve_target_user(employee)
    page = max(cint(page), 1)
    page_size = min(max(cint(page_size) or DEFAULT_PAGE_SIZE, 1), MAX_PAGE_SIZE)
    todo_statuses = _resolve_assignment_statuses(assignment_status)
    _validate_project(project)

    filters = _task_filters(
        project=project,
        statuses=_as_list(status),
        priorities=_as_list(priority),
        include_groups=bool(cint(include_groups)),
        include_cancelled=bool(cint(include_cancelled)),
    )
    fields = _task_fields()

    def empty():
        return _empty_response(page, page_size, target_user, todo_statuses)

    task_rows, assignments_by_task = _load_scope(
        is_all_tasks_mode, target_user, todo_statuses, fields, filters
    )
    tasks = {row["name"]: row for row in task_rows}
    if not tasks:
        return empty()

    universe = {**_load_ancestors(tasks, fields), **tasks}
    chains = {name: _build_chain(task, universe) for name, task in tasks.items()}

    matched = _filter_matches(tasks, chains, search)
    if not matched:
        return empty()

    positions, root_blocks = _order_matches(matched, chains)

    total = len(root_blocks)
    total_pages = max((total + page_size - 1) // page_size, 1)
    start = (page - 1) * page_size
    page_names = [
        name
        for block in root_blocks[start : start + page_size]
        for name in block
    ]

    data, context = _build_page(
        page_names, matched, chains, universe, positions, assignments_by_task
    )

    return {
        "data": data,
        "context": context,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
            "total_tasks": len(matched),
            "has_more": start + page_size < total,
        },
        "meta": {
            "user": target_user,
            "assignment_status": todo_statuses,
            "mode": "all_tasks" if is_all_tasks_mode else "assigned_tasks",
        },
    }