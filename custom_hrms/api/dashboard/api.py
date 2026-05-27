import frappe
from custom_hrms.utils.response import send_response
from . import service 

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

@frappe.whitelist(allow_guest=False, methods=["GET"])
def get_hr_dashboard_data():
    try:
        # Extract the year from the URL query parameters (e.g., ?year=2024)
        year = frappe.request.args.get("year")
        
        # Call the service layer, passing the year
        payroll_data, attendance_pattern = service.get_hr_dashboard_data(year=year)

        # Construct the response data payload
        response_data = {
            "Department Wise Payroll": payroll_data,
            "Attendance Pattern": attendance_pattern
        }

        # Return the formatted response
        return {
            "status_code": 200,
            "status": "success",
            "message": "Data retrieved successfully",
            "data": response_data
        }

    except Exception as e:
        # Log the error in Frappe
        frappe.log_error(
            frappe.get_traceback(),
            "Get HR Dashboard Data API Error"
        )

        # Return error response
        return {
            "status_code": 500,
            "status": "error",
            "message": f"Internal Server Error: {str(e)}",
            "data": {}
        }

@frappe.whitelist(allow_guest=False, methods=["GET"])
def get_employee_trend():
    try:
        # Fetch query parameters, defaulting to 6 months if not specified
        year = frappe.request.args.get("year")
        visible_months = frappe.request.args.get("visible_months", 6)

        # Call service layer to process ORM data
        filter_data, summary, trend = service.get_employee_trend_data(
            year=year,
            visible_months=visible_months
        )

        # Construct final payload
        response_data = {
            "filter": filter_data,
            "summary": summary,
            "trend": trend
        }

        return {
            "status_code": 200,
            "status": "success",
            "message": "Employee trend retrieved successfully",
            "data": response_data
        }

    except Exception as e:
        # Log backend error for developers
        frappe.log_error(
            frappe.get_traceback(),
            "Get Employee Trend API Error"
        )
        
        # Return safe error response
        return {
            "status_code": 500,
            "status": "error",
            "message": f"Internal Server Error: {str(e)}",
            "data": {}
        }