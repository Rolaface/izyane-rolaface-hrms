import frappe
from frappe.utils import getdate

def get_holiday_lists(year=None):
    filters = {}

    # Apply year filter to boundary dates if a year is provided
    if year:
        filters["from_date"] = [">=", f"{year}-01-01"]
        filters["to_date"] = ["<=", f"{year}-12-31"]

    # Fetch the parent Holiday List documents
    holiday_lists = frappe.get_all(
        "Holiday List",
        filters=filters,
        fields=["name", "holiday_list_name", "from_date", "to_date"],
        order_by="from_date desc"
    )

    # Attach the child 'tabHoliday' records to each list
    for hl in holiday_lists:
        holidays = frappe.get_all(
            "Holiday",
            filters={"parent": hl.name, "parenttype": "Holiday List"},
            fields=["holiday_date", "description", "is_half_day"],
            order_by="holiday_date asc"
        )

        # Convert date objects to strings to match your desired JSON format
        hl["from_date"] = str(hl["from_date"]) if hl["from_date"] else None
        hl["to_date"] = str(hl["to_date"]) if hl["to_date"] else None

        formatted_holidays = []
        for h in holidays:
            formatted_holidays.append({
                "holiday_date": str(h.holiday_date) if h.holiday_date else None,
                "description": h.description,
                "is_half_day": h.is_half_day
            })
        
        hl["holidays"] = formatted_holidays

    return holiday_lists