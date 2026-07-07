__version__ = "0.0.1"
import hrms.payroll.doctype.salary_slip.salary_slip as salary_slip_module
from custom_hrms.overrides.email_salary_slip import patched_email_salary_slip

salary_slip_module.SalarySlip.email_salary_slip = patched_email_salary_slip