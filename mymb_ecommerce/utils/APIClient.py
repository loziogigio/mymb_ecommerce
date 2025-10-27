import base64
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

import frappe
import requests
from frappe import _
from frappe.utils import cint, cstr, get_datetime, safe_json_loads
from pytz import timezone
from requests.exceptions import ReadTimeout, ConnectTimeout, HTTPError, ConnectionError

JsonDict = Dict[str, Any]


def _send_rate_limited_email(
    error_type: str,
    endpoint: str,
    subject: str,
    message: str,
    recipients: Optional[List[str]] = None,
    rate_limit_minutes: int = 30
):
    """
    Send email notification with rate limiting to avoid spam.
    Only sends one email per error_type+endpoint combination within rate_limit_minutes.

    Args:
        error_type: Type of error (timeout, connection_error, server_error, etc.)
        endpoint: API endpoint that failed
        subject: Email subject
        message: Email message
        recipients: List of email recipients (default: admin and support)
        rate_limit_minutes: Minutes to wait before sending another email for same error (default: 30)
    """
    if recipients is None:
        recipients = ["admin@crowdechain.com", "daniele.ammazzini@timegroup.it", "giovanni.abbatino@timegroup.it"]

    # Create a unique cache key for this error type and endpoint
    cache_key = f"api_email_{error_type}_{endpoint.replace('/', '_')}"

    # Check if we've already sent an email recently
    cache = frappe.cache()
    last_sent = cache.get(cache_key)

    if last_sent:
        # Email was already sent recently, skip
        frappe.log_error(
            message=f"Email notification suppressed (rate limited). Last sent: {last_sent}",
            title=f"Email Rate Limited - {error_type}"
        )
        return

    # Send the email
    try:
        frappe.sendmail(
            recipients=recipients,
            subject=subject,
            message=message,
            sender=frappe.db.get_single_value("Email Account", "email_id")
        )
        # Mark in cache that we sent this email
        cache.setex(cache_key, rate_limit_minutes * 60, str(datetime.now()))
    except Exception as email_error:
        frappe.log_error(
            message=f"Failed to send {error_type} notification email: {str(email_error)}",
            title="Sendmail Failure"
        )


class APIClient:
    """Wrapper around APIClient REST API

    API docs: https://documentation.mymb_b2c.com/
    """

    def __init__(self, base_url, auth_headers=None):
        self.base_url = base_url
        self._auth_headers = auth_headers if auth_headers is not None else {}


    @staticmethod
    def request(
        endpoint: str,
        method: str = "POST",
        headers: Optional[JsonDict] = None,
        body: Optional[JsonDict] = None,
        params: Optional[JsonDict] = None,
        files: Optional[JsonDict] = None,
        base_url: str = '',
        auth_headers: JsonDict = {},
        log_error=True,
    ) -> Tuple[JsonDict, bool]:

        if headers is None:
            headers = {}

        headers.update(auth_headers)

        url = base_url + endpoint

        try:
            response = requests.request(
                url=url, method=method, headers=headers, json=body, params=params, files=files, timeout=(3, 30)
            )
            # mymb_b2c gives useful info in response text, show it in error logs
            if response.text.strip() == '1' or response.text.strip() == 'false':
                return response.text
            response.reason = cstr(response.reason) + cstr(response.text)
            response.raise_for_status()
        except (ReadTimeout, ConnectTimeout) as timeout_error:
            error_message = f"Timeout occurred while accessing {url}: {str(timeout_error)}"
            frappe.log_error(message=error_message, title=f"Request Timeout - {endpoint}")

            _send_rate_limited_email(
                error_type="timeout",
                endpoint=endpoint,
                subject=f"[TIMEOUT ERROR] API call failed at {endpoint}",
                message=error_message
            )

            return None, False

        except HTTPError as http_err:
            if 400 <= http_err.response.status_code < 500:
                # Ignore client-side errors (e.g., 401, 403, 404)
                frappe.log_error(
                    message=f"Client error at {url}: {str(http_err)}",
                    title=f"Client Error - {endpoint}"
                )
            else:
                # Server-side errors
                error_message = f"Server error while {url}: {str(http_err)}"
                frappe.log_error(message=error_message, title=f"Server Error - {endpoint}")
                _send_rate_limited_email(
                    error_type="server_error",
                    endpoint=endpoint,
                    subject=f"[SERVER ERROR] Request failed at {endpoint}",
                    message=error_message,
                    recipients=["admin@crowdechain.com"]
                )
            return None, False

        except ConnectionError as conn_err:
            error_message = f"Connection failed - endpoint unreachable at {url}: {str(conn_err)}"
            frappe.log_error(message=error_message, title=f"Connection Error - {endpoint}")

            # Send email notification for connection failures
            _send_rate_limited_email(
                error_type="connection_error",
                endpoint=endpoint,
                subject=f"[CONNECTION ERROR] API endpoint unreachable: {endpoint}",
                message=error_message
            )

            return None, False

        except Exception as e:
            error_message = f"An error occurred while {url}: {str(e)}"
            frappe.log_error(message=error_message, title=f"Request Error - {endpoint}")
            return None, False

        if method == "GET" and "application/json" not in response.headers.get("content-type"):
            return response.content, True
        if isinstance(safe_json_loads(response.text), list):
            return safe_json_loads(response.text)
        data = frappe._dict(response.json())
        status = data.successful if data.successful is not None else True

        if not status:
            req = response.request
            url = f"URL: {req.url}"
            body = f"body:  {req.body.decode('utf-8')}"
            request_data = "\n\n".join([url, body])
            message = ", ".join(cstr(error["message"]) for error in data.errors)

        return data, status

    