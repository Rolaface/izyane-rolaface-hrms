import frappe
from custom_hrms.utils.response import send_response, send_response_list
from ...utils.common_utils import parse_api_payload
from . import service

@frappe.whitelist(allow_guest=False, methods=["POST"])
def create_employee():
    try:
        data = parse_api_payload()
        
        employee_data = service.create_employee(data)
        
        messages = f"Welcome email sent to {employee_data.company_email} please check and create login account for employee."
        frappe.db.commit()

        return send_response(
            status="success",
            message="Employee created successfully.",
            data={
                "employee": employee_data.employee,
                "messages": messages
            },
            status_code=201,
            http_status=201,
        )

    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(frappe.get_traceback(), "Create Employee API Error")
        return send_response(
            status="error",
            message=str(e),
            status_code=500,
            http_status=500,
        )

@frappe.whitelist(allow_guest=False, methods=["PUT", "PATCH"])
def update_employee(id=None):
    try:
        data = parse_api_payload()
        employee_id = id or frappe.request.args.get("id")

        if not employee_id:
            return send_response(
                status="fail",
                message="Employee ID required as query parameter (?id=...)",
                status_code=400,
                http_status=400,
            )
        if not frappe.db.exists("Employee", employee_id):
            return send_response(
                status="fail",
                message="Employee not found",
                status_code=404,
                http_status=404,
            )

        employee_data = service.update_employee(employee_id, data)
        frappe.db.commit()
        
        return send_response(
            status="success",
            message="Employee updated successfully",
            data=employee_data,
            status_code=200,
            http_status=200,
        )

    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(frappe.get_traceback(), "Update Employee API Error")
        return send_response(
            status="error",
            message=str(e),
            status_code=500,
            http_status=500,
        )

@frappe.whitelist(allow_guest=False, methods=["GET"])
def get_employee_by_id(id):
    try:
        if not frappe.db.exists("Employee", id):
            return send_response(
                status="fail",
                message="Employee not found",
                status_code=404,
                http_status=404,
            )

        data = service.get_employee_by_id(id)
        return send_response(
            status="success",
            message="Employee retrieved successfully",
            status_code=200,
            data=data,
            http_status=200,
        )

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Get Employee By ID Error")
        return send_response(
            status="error",
            message=f"Failed to retrieve employee: {str(e)}",
            status_code=500,
            http_status=500,
        )

@frappe.whitelist(allow_guest=False, methods=["GET"])
def get_employees(page=1, page_size=20):
    args = frappe.local.form_dict
    
    search = args.get("search")
    filters = args.get("filters", "{}") 
    sort_by = args.get("sort_by", "creation")
    sort_order = args.get("sort_order", "desc")
    
    try:
        page, page_size = int(page), int(page_size)
        
        employees, total_employees, total_pages = service.get_employees(
            filters=filters, 
            page=page, 
            page_size=page_size, 
            search=search,
            sort_by=sort_by,
            sort_order=sort_order
        )

        response_data = {
            "success": True,
            "message": "Employees retrieved successfully",
            "data": employees,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total_employees,
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
        frappe.log_error(frappe.get_traceback(), "Get All Employees Error")
        return send_response(
            status="error",
            message=f"Internal Server Error: {str(e)}",
            status_code=500,
            http_status=500,
        )

@frappe.whitelist(allow_guest=False, methods=["DELETE"])
def delete_employee(id=None):
    try:
        employee_id = id or frappe.local.form_dict.get("id")
        if not employee_id:
            return send_response(
                status="fail",
                message="Employee ID required",
                status_code=400,
                http_status=400,
            )
        if not frappe.db.exists("Employee", employee_id):
            return send_response(
                status="fail",
                message="Employee not found",
                status_code=404,
                http_status=404,
            )

        service.delete_employee(employee_id)
        frappe.db.commit()
        
        return send_response(
            status="success",
            message="Employee deleted successfully",
            status_code=200,
            http_status=200,
        )

    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(frappe.get_traceback(), "Delete Employee Error")
        return send_response(
            status="error",
            message=str(e),
            status_code=500,
            http_status=500,
        )