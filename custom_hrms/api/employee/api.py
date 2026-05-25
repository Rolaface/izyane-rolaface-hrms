import os
import frappe
from custom_hrms.utils.response import send_response, send_response_list
from ...utils.common_utils import parse_api_payload
from . import service
from .utils import ALLOWED_IMAGE_EXTENSIONS


@frappe.whitelist(allow_guest=False, methods=["POST"])
def create_employee():
    try:
        data = parse_api_payload()

        employee_data = service.create_employee(data)

        messages = f" A welcome email has been sent to {employee_data.company_email}. Kindly check your inbox and complete the account setup process to access your employee login portal."
        frappe.db.commit()

        return send_response(
            status="success",
            message="Employee created successfully.",
            data={"employee": employee_data.employee_name, "employee_id": employee_data.employee, "messages": messages},
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
            sort_order=sort_order,
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


@frappe.whitelist(allow_guest=False, methods=["PUT", "PATCH"])
def update_employee_status(id=None, status=None):
    try:
        emp_id = id or frappe.request.args.get("id")
        new_status = status or frappe.request.args.get("status")

        if not emp_id or not new_status:
            return send_response(
                status="fail",
                message="Both 'id' and 'status' query parameters are required (?id=...&status=...).",
                status_code=400,
                http_status=400,
            )

        valid_statuses = ["Active", "Inactive", "Suspended", "Left"]
        if new_status not in valid_statuses:
            return send_response(
                status="fail",
                message=f"Invalid status '{new_status}'. Allowed values: {', '.join(valid_statuses)}",
                status_code=400,
                http_status=400,
            )

        if not frappe.db.exists("Employee", emp_id):
            return send_response(
                status="fail",
                message="Employee not found",
                status_code=404,
                http_status=404,
            )

        result = service.update_employee_status(emp_id, new_status)
        frappe.db.commit()

        return send_response(
            status="success",
            message="Employee status updated successfully",
            data=result,
            status_code=200,
            http_status=200,
        )

    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(frappe.get_traceback(), "Update Employee Status API Error")
        return send_response(
            status="error",
            message=str(e),
            status_code=500,
            http_status=500,
        )


@frappe.whitelist(allow_guest=False, methods=["POST"])
def upload_employee_image(id=None):
    try:
        emp_id = id or frappe.request.args.get("id") or frappe.local.form_dict.get("id")

        if not emp_id:
            return send_response(
                status="fail",
                message="Employee 'id' is required.",
                status_code=400,
                http_status=400,
            )

        if not frappe.db.exists("Employee", emp_id):
            return send_response(
                status="fail",
                message="Employee not found",
                status_code=404,
                http_status=404,
            )

        if "file" not in frappe.request.files:
            return send_response(
                status="fail",
                message="No image provided. Please send a file using the 'file' key.",
                status_code=400,
                http_status=400,
            )

        uploaded_file = frappe.request.files["file"]

        file_ext = os.path.splitext(uploaded_file.filename)[1].lower()
        if file_ext not in ALLOWED_IMAGE_EXTENSIONS:
            return send_response(
                status="fail",
                message=f"Invalid file type '{file_ext}'. Allowed types are: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}",
                status_code=400,
                http_status=400,
            )

        file_url = service.upload_employee_image(
            employee_id=emp_id,
            filename=uploaded_file.filename,
            file_content=uploaded_file.read(),
        )

        frappe.db.commit()

        return send_response(
            status="success",
            message="Employee image uploaded successfully.",
            data={"image_url": file_url},
            status_code=201,
            http_status=201,
        )

    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(frappe.get_traceback(), "Upload Employee Image API Error")
        return send_response(
            status="error", message=str(e), status_code=500, http_status=500
        )


@frappe.whitelist(allow_guest=False, methods=["POST", "PUT", "PATCH"])
def update_employee_image(id=None):
    try:
        emp_id = id or frappe.request.args.get("id") or frappe.local.form_dict.get("id")

        if not emp_id:
            return send_response(
                status="fail",
                message="Employee 'id' is required.",
                status_code=400,
                http_status=400,
            )

        if not frappe.db.exists("Employee", emp_id):
            return send_response(
                status="fail",
                message="Employee not found",
                status_code=404,
                http_status=404,
            )

        if "file" not in frappe.request.files:
            return send_response(
                status="fail",
                message="No new image provided.",
                status_code=400,
                http_status=400,
            )

        uploaded_file = frappe.request.files["file"]

        file_ext = os.path.splitext(uploaded_file.filename)[1].lower()
        if file_ext not in ALLOWED_IMAGE_EXTENSIONS:
            return send_response(
                status="fail",
                message=f"Invalid file type '{file_ext}'. Allowed types are: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}",
                status_code=400,
                http_status=400,
            )

        new_file_url = service.update_employee_image(
            employee_id=emp_id,
            filename=uploaded_file.filename,
            file_content=uploaded_file.read(),
        )

        frappe.db.commit()

        return send_response(
            status="success",
            message="Employee image updated successfully.",
            data={"image_url": new_file_url},
            status_code=200,
            http_status=200,
        )

    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(frappe.get_traceback(), "Update Employee Image API Error")
        return send_response(
            status="error", message=str(e), status_code=500, http_status=500
        )


@frappe.whitelist(allow_guest=False, methods=["POST", "DELETE"])
def remove_employee_image(id=None):
    try:
        emp_id = id or frappe.request.args.get("id") or frappe.local.form_dict.get("id")

        if not emp_id:
            return send_response(
                status="fail",
                message="Employee 'id' is required.",
                status_code=400,
                http_status=400,
            )

        if not frappe.db.exists("Employee", emp_id):
            return send_response(
                status="fail",
                message="Employee not found",
                status_code=404,
                http_status=404,
            )

        service.remove_employee_image(emp_id)

        frappe.db.commit()

        return send_response(
            status="success",
            message="Employee image removed successfully.",
            status_code=200,
            http_status=200,
        )

    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(frappe.get_traceback(), "Remove Employee Image API Error")
        return send_response(
            status="error",
            message=str(e),
            status_code=500,
            http_status=500,
        )


@frappe.whitelist(allow_guest=False, methods=["POST"])
def upload_employee_document(id=None):
    try:
        emp_id = id or frappe.request.args.get("id") or frappe.local.form_dict.get("id")

        document_name = frappe.request.args.get(
            "document_name"
        ) or frappe.local.form_dict.get("document_name")

        if not emp_id:
            return send_response(
                status="fail",
                message="Employee 'id' is required.",
                status_code=400,
                http_status=400,
            )

        if not document_name:
            return send_response(
                status="fail",
                message="'document_name' is required.",
                status_code=400,
                http_status=400,
            )

        if not frappe.db.exists("Employee", emp_id):
            return send_response(
                status="fail",
                message="Employee not found.",
                status_code=404,
                http_status=404,
            )

        if "file" not in frappe.request.files:
            return send_response(
                status="fail",
                message="No document provided. Please send a file using the 'file' key.",
                status_code=400,
                http_status=400,
            )

        uploaded_file = frappe.request.files["file"]

        if not uploaded_file or not uploaded_file.filename:
            return send_response(
                status="fail",
                message="Invalid uploaded file.",
                status_code=400,
                http_status=400,
            )

        file_content = uploaded_file.read()

        if not file_content:
            return send_response(
                status="fail",
                message="Uploaded file is empty.",
                status_code=400,
                http_status=400,
            )

        saved_file_doc = service.upload_employee_document(
            employee_id=emp_id,
            filename=uploaded_file.filename,
            file_content=file_content,
            document_name=document_name,
        )

        frappe.db.commit()

        return send_response(
            status="success",
            message=f"{document_name} uploaded successfully.",
            data={
                "file_id": saved_file_doc.name,
                "document_name": saved_file_doc.file_name,
                "file_url": saved_file_doc.file_url,
                "is_private": saved_file_doc.is_private,
            },
            status_code=201,
            http_status=201,
        )

    except frappe.ValidationError as e:
        frappe.db.rollback()

        return send_response(
            status="fail",
            message=str(e),
            status_code=400,
            http_status=400,
        )

    except Exception as e:
        frappe.db.rollback()

        frappe.log_error(
            frappe.get_traceback(),
            "Upload Employee Document API Error",
        )

        return send_response(
            status="error",
            message="Failed to upload employee document.",
            data={"error": str(e)},
            status_code=500,
            http_status=500,
        )


@frappe.whitelist(allow_guest=False, methods=["GET"])
def get_employee_documents(id=None):
    try:
        emp_id = id or frappe.request.args.get("id")

        if not emp_id:
            return send_response(
                status="fail",
                message="Employee 'id' required",
                status_code=400,
                http_status=400,
            )

        if not frappe.db.exists("Employee", emp_id):
            return send_response(
                status="fail",
                message="Employee not found",
                status_code=404,
                http_status=404,
            )

        documents = service.get_employee_documents(emp_id)

        return send_response(
            status="success",
            message="Documents retrieved successfully",
            data=documents,
            status_code=200,
            http_status=200,
        )

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Get Employee Documents Error")
        return send_response(
            status="error", message=str(e), status_code=500, http_status=500
        )


@frappe.whitelist(allow_guest=False, methods=["GET"])
def get_employee_document_by_id(file_id=None):
    try:
        file_id = file_id or frappe.request.args.get("file_id")

        if not file_id:
            return send_response(
                status="fail",
                message="Parameter 'file_id' required",
                status_code=400,
                http_status=400,
            )

        if not frappe.db.exists("File", file_id):
            return send_response(
                status="fail",
                message="Document not found",
                status_code=404,
                http_status=404,
            )

        doc_data = service.get_employee_document_by_id(file_id)

        return send_response(
            status="success",
            message="Document retrieved",
            data=doc_data,
            status_code=200,
            http_status=200,
        )

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Get Employee Document Error")
        return send_response(
            status="error", message=str(e), status_code=500, http_status=500
        )


@frappe.whitelist(allow_guest=False, methods=["POST", "PUT"])
def update_employee_document(file_id=None):
    try:
        form = frappe.local.form_dict
        f_id = file_id or form.get("file_id")
        document_name = form.get("document_name")

        if not f_id:
            return send_response(
                status="fail",
                message="Parameter 'file_id' required",
                status_code=400,
                http_status=400,
            )

        if not frappe.db.exists("File", f_id):
            return send_response(
                status="fail",
                message="Document not found",
                status_code=404,
                http_status=404,
            )

        new_file_content = None
        new_filename = None

        uploaded_file = frappe.request.files.get("file")
        if uploaded_file:
            new_file_content = uploaded_file.stream.read()
            new_filename = uploaded_file.filename

        updated_doc = service.update_employee_document(
            file_id=f_id,
            new_document_name=document_name,
            new_file_content=new_file_content,
            new_filename=new_filename,
        )

        frappe.db.commit()

        return send_response(
            status="success",
            message="Document updated successfully",
            data={
                "file_id": updated_doc.name,
                "document_name": updated_doc.file_name,
                "file_url": updated_doc.file_url,
            },
            status_code=200,
            http_status=200,
        )

    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(frappe.get_traceback(), "Update Employee Document Error")
        return send_response(
            status="error", message=str(e), status_code=500, http_status=500
        )


@frappe.whitelist(allow_guest=False, methods=["DELETE"])
def delete_employee_document(file_id=None):
    try:
        f_id = file_id or frappe.local.form_dict.get("file_id")

        if not f_id:
            return send_response(
                status="fail",
                message="Parameter 'file_id' required",
                status_code=400,
                http_status=400,
            )

        if not frappe.db.exists("File", f_id):
            return send_response(
                status="fail",
                message="Document not found",
                status_code=404,
                http_status=404,
            )

        service.delete_employee_document(f_id)
        frappe.db.commit()

        return send_response(
            status="success",
            message="Document deleted successfully",
            status_code=200,
            http_status=200,
        )

    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(frappe.get_traceback(), "Delete Employee Document Error")
        return send_response(
            status="error", message=str(e), status_code=500, http_status=500
        )
