import frappe
from frappe.model.document import Document


class ProjectRole(Document):
    def validate(self):
        self.role_name = (self.role_name or "").strip()

        if not self.role_name:
            frappe.throw("Role Name is required")