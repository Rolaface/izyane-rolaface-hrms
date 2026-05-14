import frappe

from custom_hrms.utils.response import send_old_response

from .service import (
    create_holiday_list_service,
    get_holiday_list_service,
    list_holiday_lists_service,
    update_holiday_list_service,
    delete_holiday_list_service,
    assign_default_holiday_list_to_company,
)


@frappe.whitelist(allow_guest=False, methods=["POST"])
def create_holiday_list():
    try:
        payload = frappe.request.get_json()

        holiday_list = create_holiday_list_service(payload)

        return send_old_response(
            status="success",
            message="Holiday List created successfully.",
            data=holiday_list,
            status_code=201,
            http_status=201,
        )

    except frappe.ValidationError as e:
        frappe.db.rollback()

        return send_old_response(
            status="error",
            message=str(e),
            data=None,
            status_code=400,
            http_status=400,
        )

    except Exception as e:
        frappe.db.rollback()

        frappe.log_error(
            frappe.get_traceback(),
            "Create Holiday List API Error",
        )

        return send_old_response(
            status="error",
            message=str(e),
            data=None,
            status_code=500,
            http_status=500,
        )


@frappe.whitelist(allow_guest=False, methods=["GET"])
def get_holiday_list(name: str):
    try:
        holiday_list = get_holiday_list_service(name)

        return send_old_response(
            status="success",
            message="Holiday List retrieved successfully.",
            data=holiday_list,
            status_code=200,
            http_status=200,
        )

    except frappe.DoesNotExistError:
        return send_old_response(
            status="error",
            message="Holiday List not found.",
            data=None,
            status_code=404,
            http_status=404,
        )

    except Exception as e:
        frappe.log_error(
            frappe.get_traceback(),
            "Get Holiday List API Error",
        )

        return send_old_response(
            status="error",
            message=str(e),
            data=None,
            status_code=500,
            http_status=500,
        )


@frappe.whitelist(allow_guest=False, methods=["GET"])
def list_holiday_lists():
    try:
        holiday_lists = list_holiday_lists_service()

        return send_old_response(
            status="success",
            message="Holiday Lists retrieved successfully.",
            data=holiday_lists,
            status_code=200,
            http_status=200,
        )

    except Exception as e:
        frappe.log_error(
            frappe.get_traceback(),
            "List Holiday Lists API Error",
        )

        return send_old_response(
            status="error",
            message=str(e),
            data=None,
            status_code=500,
            http_status=500,
        )


@frappe.whitelist(allow_guest=False, methods=["PUT", "PATCH"])
def update_holiday_list(name: str):
    try:
        payload = frappe.request.get_json()

        holiday_list = update_holiday_list_service(
            name=name,
            payload=payload,
        )

        return send_old_response(
            status="success",
            message="Holiday List updated successfully.",
            data=holiday_list,
            status_code=200,
            http_status=200,
        )

    except frappe.DoesNotExistError:
        frappe.db.rollback()

        return send_old_response(
            status="error",
            message="Holiday List not found.",
            data=None,
            status_code=404,
            http_status=404,
        )

    except frappe.ValidationError as e:
        frappe.db.rollback()

        return send_old_response(
            status="error",
            message=str(e),
            data=None,
            status_code=400,
            http_status=400,
        )

    except Exception as e:
        frappe.db.rollback()

        frappe.log_error(
            frappe.get_traceback(),
            "Update Holiday List API Error",
        )

        return send_old_response(
            status="error",
            message=str(e),
            data=None,
            status_code=500,
            http_status=500,
        )


@frappe.whitelist(allow_guest=False, methods=["DELETE"])
def delete_holiday_list(name: str):
    try:
        delete_holiday_list_service(name)

        return send_old_response(
            status="success",
            message="Holiday List deleted successfully.",
            data=None,
            status_code=200,
            http_status=200,
        )

    except frappe.DoesNotExistError:
        frappe.db.rollback()

        return send_old_response(
            status="error",
            message="Holiday List not found.",
            data=None,
            status_code=404,
            http_status=404,
        )

    except Exception as e:
        frappe.db.rollback()

        frappe.log_error(
            frappe.get_traceback(),
            "Delete Holiday List API Error",
        )

        return send_old_response(
            status="error",
            message=str(e),
            data=None,
            status_code=500,
            http_status=500,
        )


@frappe.whitelist(allow_guest=False, methods=["POST"])
def assign_default_holiday_list_to_company():
    try:
        payload = frappe.request.get_json()

        result = assign_default_holiday_list_to_company(
            payload=payload,
        )

        return send_old_response(
            status="success",
            message="Holiday List assigned to company successfully.",
            data=result,
            status_code=200,
            http_status=200,
        )

    except frappe.DoesNotExistError:
        frappe.db.rollback()

        return send_old_response(
            status="error",
            message="Company or Holiday List not found.",
            data=None,
            status_code=404,
            http_status=404,
        )

    except Exception as e:
        frappe.db.rollback()

        frappe.log_error(
            frappe.get_traceback(),
            "Assign Holiday List To Company API Error",
        )

        return send_old_response(
            status="error",
            message=str(e),
            data=None,
            status_code=500,
            http_status=500,
        )
