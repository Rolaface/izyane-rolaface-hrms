import re
import frappe

DEFAULT_EMPLOYEE_NUMBER_PREFIX = "EMP-"
DEFAULT_EMPLOYEE_NUMBER_WIDTH = 5
MAX_EMPLOYEE_NUMBER_LENGTH = 140  # matches Frappe's default Data field length

_NUMERIC_SUFFIX_PATTERN = re.compile(r"^(.*?)(\d+)$")


def get_next_employee_number():
    """
    Suggests the next employee number based on the highest existing
    numeric suffix found in Employee.employee_number.

    Suggestion only — no writes, no reservation, no interaction with
    Frappe's naming series (Employee.name / HR-EMP-xxxxx).
    """
    existing_numbers = frappe.get_all(
        "Employee",
        filters={"employee_number": ["is", "set"]},
        pluck="employee_number",
    )

    if not existing_numbers:
        return _format_number(DEFAULT_EMPLOYEE_NUMBER_PREFIX, 1, DEFAULT_EMPLOYEE_NUMBER_WIDTH)

    best_prefix, best_width, best_number = _find_highest_employee_number(existing_numbers)
    return _format_number(best_prefix, best_number + 1, best_width)


def check_employee_number_availability(employee_number, exclude_employee_id=None):
    """
    Live check for whether employee_number is already taken.
    Intended for on-blur/on-type validation before Save, so the user
    gets instant feedback instead of discovering the clash at submit time.

    exclude_employee_id: current employee's id on an edit screen, so the
    record being edited doesn't flag itself as a duplicate.
    """
    employee_number = _sanitize_employee_number(employee_number)

    filters = {"employee_number": employee_number}
    if exclude_employee_id:
        filters["name"] = ["!=", exclude_employee_id]

    existing_employee_id = frappe.db.get_value("Employee", filters, "name")
    is_available = not existing_employee_id

    return {
        "employee_number": employee_number,
        "is_available": is_available,
        "existing_employee_id": existing_employee_id if not is_available else None,
    }


def assert_employee_number_is_unique(employee_number, exclude_employee_id=None):
    """
    Hard save-time guard used inside create_employee / update_employee.
    Raises frappe.ValidationError on clash. This is the real guarantee;
    check_employee_number_availability is only a UX convenience and can
    race under concurrency.
    """
    result = check_employee_number_availability(employee_number, exclude_employee_id)
    if not result["is_available"]:
        frappe.throw(
            f"Employee Number '{result['employee_number']}' is already in use "
            f"by {result['existing_employee_id']}."
        )


def _sanitize_employee_number(employee_number):
    if not employee_number or not str(employee_number).strip():
        frappe.throw("Employee Number is required.")

    employee_number = str(employee_number).strip()

    if len(employee_number) > MAX_EMPLOYEE_NUMBER_LENGTH:
        frappe.throw(f"Employee Number must not exceed {MAX_EMPLOYEE_NUMBER_LENGTH} characters.")

    return employee_number


def _find_highest_employee_number(existing_numbers):
    best_prefix = DEFAULT_EMPLOYEE_NUMBER_PREFIX
    best_width = DEFAULT_EMPLOYEE_NUMBER_WIDTH
    best_number = 0

    for value in existing_numbers:
        if not value:
            continue

        match = _NUMERIC_SUFFIX_PATTERN.match(str(value).strip())
        if not match:
            # Legacy/manually entered values without a numeric suffix
            # are skipped rather than breaking the whole suggestion.
            continue

        prefix, digits = match.group(1), match.group(2)
        numeric_value = int(digits)

        if numeric_value > best_number:
            best_number = numeric_value
            best_prefix = prefix
            best_width = len(digits)

    return best_prefix, best_width, best_number


def _format_number(prefix, number, width):
    return f"{prefix}{str(number).zfill(width)}"