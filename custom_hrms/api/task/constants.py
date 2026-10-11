DEFAULT_PAGE_SIZE = 100
MAX_PAGE_SIZE = 500
BATCH_SIZE = 1000
MAX_DEPTH = 50

# Roles allowed to look at another employee's assignments.
PRIVILEGED_ROLES = {"System Manager", "HR Manager", "Professional"}

# Roles that see every Task (assigned or not) when no employee is requested.
ALL_TASKS_ROLES = {"System Manager", "Professional"}

ASSIGNMENT_STATUSES = ("Open", "Closed", "Cancelled")

BASE_TASK_FIELDS = [
    "name",
    "subject",
    "project",
    "parent_task",
    "is_group",
    "status",
    "priority",
    "modified",
]