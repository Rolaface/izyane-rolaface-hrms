import frappe
from custom_hrms.utils.response import send_response, send_response_list
from . import service 

@frappe.whitelist(allow_guest=False, methods=["GET"])
def get_all_holiday_lists(year=None):
    try:
        # Check request args if 'year' isn't explicitly passed to the function
        if not year:
            year = frappe.request.args.get("year")

        # Fetch the formatted data from the service layer
        holiday_lists = service.get_holiday_lists(year=year)

        # Return the successful custom response
        return send_response_list(
            status="success",
            message="Holiday Lists retrieved successfully.",
            status_code=200,
            data=holiday_lists,
            http_status=200,
        )

    except Exception as e:
        # Log the error in Frappe's Error Log for debugging
        frappe.log_error(
            frappe.get_traceback(),
            "Get All Holiday Lists API Error",
        )

        # Return standard error payload
        return send_response(
            status="error",
            message=f"Internal Server Error: {str(e)}",
            status_code=500,
            http_status=500,
        )