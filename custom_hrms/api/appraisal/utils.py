import frappe

APPRAISAL_CYCLE_FIELDS = [
    "name",
    "docstatus",
    "company",
    "start_date",
    "end_date",
    "appraisal_template",
    "department",
    "branch",
    "designation",
    "status",
    "calculate_final_score"
]

APPRAISAL_FIELDS = [
    "name",
    "docstatus",
    "employee",
    "employee_name",
    "company",
    "department",
    "branch",
    "designation",
    "status",
    "start_date",
    "end_date",
    "appraisal_cycle",
    "appraisal_template",
    "total_score",
    "final_score"
]

def extract_allowed_fields(raw_dict: dict, allowed_fields: list) -> dict:
    """Safely extracts only the explicitly allowed fields from a dictionary."""
    return {key: raw_dict[key] for key in allowed_fields if key in raw_dict}

def get_error_response(message: str, traceback: str | None = None) -> dict:
    """Standardized error response formatter."""
    response = {
        "status": "error",
        "message": message,
    }
    if traceback:
        response["traceback"] = traceback
    return response