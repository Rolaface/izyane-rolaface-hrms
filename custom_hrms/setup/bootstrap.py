import frappe
from .cleanup_hrms import cleanup_hrms
from .zambia_hrms_setup import setup_zambia_hrms


def bootstrap():
    print("=" * 70)
    print("Starting HRMS Bootstrap")
    print("=" * 70)

    print("Starting HRMS Cleanup")
    print("=" * 70)

    cleanup_hrms()

    print("=" * 70)
    print("Starting ZAMBIA HRMS Setup")
    print("=" * 70)

    setup_zambia_hrms()

    frappe.db.commit()

    print("\nHRMS Bootstrap Completed Successfully.")