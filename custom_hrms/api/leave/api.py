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