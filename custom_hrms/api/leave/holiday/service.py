from datetime import timedelta

import frappe

from frappe import _
from frappe.utils import getdate

VALID_WEEKDAYS = {
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
}


def create_holiday_list_service(payload: dict) -> dict:
    validate_payload(payload)

    holiday_list = frappe.get_doc(
        {
            "doctype": "Holiday List",
            "holiday_list_name": payload.get("holiday_list_name"),
            "from_date": payload.get("from_date"),
            "to_date": payload.get("to_date"),
            "country": payload.get("country"),
        }
    )

    holiday_list.insert(ignore_permissions=True)

    rebuild_holidays(
        holiday_list=holiday_list,
        payload=payload,
    )

    holiday_list.save(ignore_permissions=True)

    frappe.db.commit()

    return serialize_holiday_list(holiday_list)


def get_holiday_list_service(name: str) -> dict:
    holiday_list = frappe.get_doc(
        "Holiday List",
        name,
    )

    return serialize_holiday_list(holiday_list)


def list_holiday_lists_service() -> list:
    holiday_lists = frappe.get_all(
        "Holiday List",
        fields=[
            "name",
            "holiday_list_name",
            "from_date",
            "to_date",
            "country",
        ],
        order_by="modified desc",
    )

    return holiday_lists


def update_holiday_list_service(
    name: str,
    payload: dict,
) -> dict:
    validate_payload(payload)

    holiday_list = frappe.get_doc(
        "Holiday List",
        name,
    )

    holiday_list.holiday_list_name = payload.get("holiday_list_name")

    holiday_list.from_date = payload.get("from_date")
    holiday_list.to_date = payload.get("to_date")
    holiday_list.country = payload.get("country")

    holiday_list.holidays = []

    rebuild_holidays(
        holiday_list=holiday_list,
        payload=payload,
    )

    holiday_list.save(ignore_permissions=True)

    frappe.db.commit()

    return serialize_holiday_list(holiday_list)


def delete_holiday_list_service(name: str) -> None:
    frappe.delete_doc(
        "Holiday List",
        name,
        ignore_permissions=True,
    )

    frappe.db.commit()


def rebuild_holidays(
    holiday_list,
    payload: dict,
) -> None:
    add_weekly_offs(
        holiday_list=holiday_list,
        weekly_offs=payload.get("weekly_offs", []),
    )

    add_custom_holidays(
        holiday_list=holiday_list,
        holidays=payload.get("holidays", []),
    )


def validate_payload(payload: dict) -> None:
    required_fields = [
        "holiday_list_name",
        "from_date",
        "to_date",
    ]

    for field in required_fields:
        if not payload.get(field):
            frappe.throw(_("{0} is required.").format(field))

    if getdate(payload.get("from_date")) > getdate(payload.get("to_date")):
        frappe.throw(_("from_date cannot be greater than to_date."))

    validate_weekly_offs(payload.get("weekly_offs", []))

    validate_holidays(payload.get("holidays", []))


def validate_weekly_offs(
    weekly_offs: list,
) -> None:
    for weekly_off in weekly_offs:
        weekday = weekly_off.get("weekday")

        if not weekday:
            frappe.throw(_("weekday is required in weekly_offs."))

        if weekday not in VALID_WEEKDAYS:
            frappe.throw(_("Invalid weekday: {0}").format(weekday))

        occurrence = weekly_off.get(
            "occurrence",
            "every",
        )

        if occurrence != "every":
            frappe.throw(_("Only 'every' occurrence is supported currently."))


def validate_holidays(
    holidays: list,
) -> None:
    for holiday in holidays:
        if not holiday.get("holiday_date"):
            frappe.throw(_("holiday_date is required in holidays."))


def add_weekly_offs(
    holiday_list,
    weekly_offs: list,
) -> None:
    existing_dates = set()

    for holiday in holiday_list.holidays:
        existing_dates.add(str(holiday.holiday_date))

    from_date = getdate(holiday_list.from_date)

    to_date = getdate(holiday_list.to_date)

    weekday_map = {
        "Monday": 0,
        "Tuesday": 1,
        "Wednesday": 2,
        "Thursday": 3,
        "Friday": 4,
        "Saturday": 5,
        "Sunday": 6,
    }

    current_date = from_date

    while current_date <= to_date:
        current_weekday = current_date.weekday()

        for weekly_off in weekly_offs:
            target_weekday = weekday_map.get(weekly_off.get("weekday"))

            if current_weekday != target_weekday:
                continue

            current_date_str = str(current_date)

            if current_date_str in existing_dates:
                continue

            holiday_list.append(
                "holidays",
                {
                    "holiday_date": current_date,
                    "description": weekly_off.get("weekday"),
                    "weekly_off": 1,
                    "is_half_day": (
                        1
                        if weekly_off.get(
                            "is_half_day",
                            False,
                        )
                        else 0
                    ),
                },
            )

            existing_dates.add(current_date_str)

        current_date += timedelta(days=1)


def add_custom_holidays(
    holiday_list,
    holidays: list,
) -> None:
    existing_dates = set()

    for holiday in holiday_list.holidays:
        existing_dates.add(str(holiday.holiday_date))

    for holiday in holidays:
        holiday_date = holiday.get("holiday_date")

        if str(holiday_date) in existing_dates:
            continue

        holiday_list.append(
            "holidays",
            {
                "holiday_date": holiday_date,
                "description": holiday.get("description"),
                "weekly_off": 0,
                "is_half_day": (
                    1
                    if holiday.get(
                        "is_half_day",
                        False,
                    )
                    else 0
                ),
            },
        )

        existing_dates.add(str(holiday_date))


# def serialize_holiday_list(
#     holiday_list,
# ) -> dict:
#     return {
#         "name": holiday_list.name,
#         "holiday_list_name": holiday_list.holiday_list_name,
#         "from_date": holiday_list.from_date,
#         "to_date": holiday_list.to_date,
#         "country": holiday_list.country,
#         "holidays": [
#             {
#                 "holiday_date": holiday.holiday_date,
#                 "description": holiday.description,
#                 "weekly_off": holiday.weekly_off,
#                 "is_half_day": holiday.is_half_day,
#             }
#             for holiday in holiday_list.holidays
#         ],
#     }


def serialize_holiday_list(
    holiday_list,
) -> dict:
    weekly_offs = []
    holidays = []

    added_weekdays = set()

    for holiday in holiday_list.holidays:
        if holiday.weekly_off:
            weekday = holiday.description

            if weekday in added_weekdays:
                continue

            weekly_off = {
                "weekday": weekday,
            }

            if holiday.is_half_day:
                weekly_off["is_half_day"] = True

            weekly_offs.append(weekly_off)

            added_weekdays.add(weekday)

        else:
            holiday_data = {
                "holiday_date": holiday.holiday_date,
                "description": holiday.description,
            }

            if holiday.is_half_day:
                holiday_data["is_half_day"] = True

            holidays.append(holiday_data)

    return {
        "name": holiday_list.name,
        "holiday_list_name": holiday_list.holiday_list_name,
        "from_date": holiday_list.from_date,
        "to_date": holiday_list.to_date,
        "weekly_offs": weekly_offs,
        "holidays": holidays,
    }


def assign_default_holiday_list_to_company(
    payload: dict,
) -> dict:
    company = payload.get("company") or frappe.defaults.get_user_default("Company")

    holiday_list = payload.get("holiday_list")

    if not company:
        frappe.throw(_("company is required."))

    if not holiday_list:
        frappe.throw(_("holiday_list is required."))

    company_doc = frappe.get_doc(
        "Company",
        company,
    )

    frappe.get_doc(
        "Holiday List",
        holiday_list,
    )

    company_doc.default_holiday_list = holiday_list

    company_doc.save(
        ignore_permissions=True,
    )

    frappe.db.commit()

    return {
        "company": company_doc.name,
        "default_holiday_list": company_doc.default_holiday_list,
    }
