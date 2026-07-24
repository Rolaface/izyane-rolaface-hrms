import frappe
from frappe.query_builder import DocType

MAX_EMPLOYEE_NUMBER_LENGTH = 140


def _resolve_prefix_and_digits(template: str) -> tuple[str, int]:
    """
    Resolve the tabSeries key (prefix) and digit width Frappe's naming
    engine would use for a naming_series template, without calling
    parse_naming_series()/getseries() (which increment the counter).
    """
    if not template:
        frappe.throw("Naming series template is empty.")

    template = template.strip()
    if "#" not in template:
        template += ".#####"

    prefix = ""
    digits = 5
    counter_seen = False

    for part in template.split("."):
        if not part:
            continue
        if part.startswith("#"):
            if not counter_seen:
                digits = len(part)
                counter_seen = True
            continue
        if not counter_seen:
            prefix += part

    return prefix, digits


def _get_employee_naming_template(naming_series: str | None = None) -> str:
    meta = frappe.get_meta("Employee")
    naming_series_field = meta.get_field("naming_series")

    if not naming_series_field or not naming_series_field.options:
        frappe.throw("Employee naming series is not configured.")

    options = [o.strip() for o in naming_series_field.options.split("\n") if o.strip()]
    if not options:
        frappe.throw("Employee naming series options are empty.")

    if naming_series:
        naming_series = naming_series.strip()
        if naming_series not in options:
            frappe.throw(f"'{naming_series}' is not a configured Employee naming series.")
        return naming_series

    return options[0]


def get_next_employee_number(naming_series: str | None = None) -> str:
    """
    Preview the next Employee Number from Frappe's own naming series
    counter (tabSeries.current) — read-only, no increment, no scan,
    no regex.
    """
    template = _get_employee_naming_template(naming_series)
    prefix, digits = _resolve_prefix_and_digits(template)

    series = DocType("Series")
    result = (
        frappe.qb.from_(series)
        .where(series.name == prefix)
        .select(series.current)
    ).run()

    current_value = result[0][0] if result else 0
    next_value = (current_value or 0) + 1

    return f"{prefix}{str(next_value).zfill(digits)}"


def _sanitize_employee_number(employee_number):
    if not employee_number or not str(employee_number).strip():
        frappe.throw("Employee Number is required.")

    employee_number = str(employee_number).strip()

    if len(employee_number) > MAX_EMPLOYEE_NUMBER_LENGTH:
        frappe.throw(f"Employee Number must not exceed {MAX_EMPLOYEE_NUMBER_LENGTH} characters.")

    return employee_number


def check_employee_number_availability(employee_number, exclude_employee_id=None):
    """
    Live check for whether employee_number is already taken.
    Single indexed lookup — no scan, no regex.
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
    Hard save-time guard. This is the real guarantee; the availability
    check above is UX-only and can race under concurrency.
    """
    result = check_employee_number_availability(employee_number, exclude_employee_id)
    if not result["is_available"]:
        frappe.throw(
            f"Employee Number '{result['employee_number']}' is already in use "
            f"by {result['existing_employee_id']}."
        )