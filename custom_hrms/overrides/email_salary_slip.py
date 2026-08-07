import frappe
from frappe import _
from frappe.utils.background_jobs import enqueue

from hrms.payroll.doctype.salary_slip.salary_slip import (
    SalarySlip,
    generate_password_for_pdf,
)


def patched_email_salary_slip(self):
    receiver = frappe.db.get_value("Employee", self.employee, "prefered_email", cache=True)
    payroll_settings = frappe.get_single("Payroll Settings")

    subject = f"Salary Slip - from {self.start_date} to {self.end_date}"
    message = _("Please see attachment")

    if payroll_settings.email_template:
        email_template = frappe.get_doc("Email Template", payroll_settings.email_template)
        context = self.as_dict()
        subject = frappe.render_template(email_template.subject, context)
        message = frappe.render_template(email_template.response, context)

    password = None
    if payroll_settings.encrypt_salary_slips_in_emails:
        password = generate_password_for_pdf(payroll_settings.password_policy, self.employee)
        if not payroll_settings.email_template:
            message += "<br>" + _(
                "Note: Your salary slip is password protected, the password to unlock the PDF is of the format {0}."
            ).format(payroll_settings.password_policy)

    if receiver:
        month = self.start_date.strftime("%b %Y")
        filename = f"Salary Slip - {self.employee_name} - {month}"

        email_args = {
            "sender": payroll_settings.sender_email,
            "recipients": [receiver],
            "message": message,
            "subject": subject,
            "attachments": [
                frappe.attach_print(
                    self.doctype,
                    self.name,
                    file_name=filename,
                    password=password,
                )
            ],
            "reference_doctype": self.doctype,
            "reference_name": self.name,
        }

        if not frappe.flags.in_test:
            enqueue(
                method=frappe.sendmail,
                queue="short",
                timeout=300,
                is_async=True,
                **email_args,
            )
        else:
            frappe.sendmail(**email_args)
    else:
        frappe.msgprint(
            _("{0}: Employee email not found, hence email not sent").format(self.employee_name)
        )