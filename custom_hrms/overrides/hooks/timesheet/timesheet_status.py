from .constants import EXTRA_DRAFT_STATUSES

def remember_status(doc, method=None):
    doc.flags.requested_status = doc.status

def restore_status(doc, method=None):
    if doc.docstatus == 0 and doc.flags.requested_status in EXTRA_DRAFT_STATUSES:
        doc.status = doc.flags.requested_status