import frappe
from custom_hrms.utils.response import send_response, send_response_list
from . import service 

@frappe.whitelist(allow_guest=False, methods=["GET"])
def get_leave_approvers(page=1, page_size=20):
    try:
        page = int(page)
        page_size = int(page_size)

        filters = frappe._dict({
            "employee": frappe.request.args.get("employee"),
            "doctype": (
                frappe.request.args.get("doctype")
                or "Leave Application"
            ),
        })

        (
            approvers,
            total_approvers,
            total_pages,
        ) = service.get_leave_approvers(
            filters=filters,
            page=page,
            page_size=page_size,
        )

        response_data = {
            "success": True,
            "message": "Leave approvers retrieved successfully",
            "data": approvers,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total_approvers,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
            },
        }

        return send_response_list(
            status="success",
            message="Success",
            status_code=200,
            data=response_data,
            http_status=200,
        )

    except Exception as e:
        frappe.log_error(
            frappe.get_traceback(),
            "Get Leave Approvers API Error",
        )

        return send_response(
            status="error",
            message=f"Internal Server Error: {str(e)}",
            status_code=500,
            http_status=500,
        )

@frappe.whitelist(allow_guest=False, methods=["GET"])
def custom_employee_details(employee_id=None):
    # Fallback to query params if not explicitly passed as an argument
    if not employee_id:
        employee_id = frappe.request.args.get("employee_id")

    if not employee_id:
        return send_response(
            status="error",
            message="Missing required parameter: employee_id",
            data=None,
            status_code=400,
            http_status=400,
        )

    try:
        # Call the service layer to get the compiled data
        data = service.get_employee_details_data(employee_id)

        # Handle the case where the employee does not exist
        if not data:
            return send_response(
                status="error",
                message=f"Employee with ID {employee_id} not found.",
                data=None,
                status_code=404,
                http_status=404,
            )

        return send_response(
            status="success",
            message="Employee details retrieved successfully.",
            data=data,
            status_code=200,
            http_status=200,
        )

    except Exception as e:
        frappe.log_error(
            frappe.get_traceback(), 
            f"Employee Details API Error - {employee_id}"
        )
        
        return send_response(
            status="error",
            message=f"Internal Server Error: {str(e)}",
            data=None,
            status_code=500,
            http_status=500,
        )

@frappe.whitelist(allow_guest=False, methods=["GET"])
def get_employee_status_counts():
    try:
        counts_data = service.get_employee_status_counts()

        response = send_response(
            status="success",
            message="Employee status counts retrieved successfully",
            status_code=200,
            data=counts_data,
            http_status=200,
        )
        
        frappe.response.update(response)

    except Exception as e:
        frappe.log_error(
            frappe.get_traceback(),
            "Get Employee Status Counts API Error",
        )

        error_response = send_response(
            status="error",
            message=f"Internal Server Error: {str(e)}",
            status_code=500,
            http_status=500,
        )
        
        frappe.response.update(error_response)
