import frappe
from email.utils import parseaddr
from frappe.utils import now_datetime, cstr
from frappe.utils.background_jobs import enqueue, get_jobs

def sendmail(recipients, sender='', subject='', message='', reference_doctype=None,
             reference_name=None, unsubscribe_method=None, unsubscribe_params=None,
             attachments=None, content=None, send_after=None, communication=False):

    # Ensure that sender is a valid email address
    if sender and "@" not in parseaddr(sender)[1]:
        sender = None

    try:
        # Send the email using frappe.sendmail
        frappe.sendmail(
            recipients=recipients,
            sender=sender,
            subject=subject,
            message=message,
            reference_doctype=reference_doctype,
            reference_name=reference_name,
            unsubscribe_method=unsubscribe_method,
            unsubscribe_params=unsubscribe_params,
            content=content,
            delayed=send_after is not None,
        )

        return "Email sent successfully"
    except Exception as e:
        return str(e)