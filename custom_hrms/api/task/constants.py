DEFAULT_PAGE_SIZE = 100
MAX_PAGE_SIZE = 500
BATCH_SIZE = 1000
MAX_DEPTH = 50

PRIVILEGED_ROLES = {"System Manager", "HR Manager", "Professional"}

ALL_TASKS_ROLES = {"System Manager", "Professional", "All Tasks Viewer"}

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
    "owner",
    "creation",
    "exp_start_date",
    "exp_end_date",
    "progress",
    "is_milestone",
]