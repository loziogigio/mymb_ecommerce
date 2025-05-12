import base64
from typing import Any, Dict, List, Optional, Tuple

import frappe
import requests
from frappe import _
from frappe.utils import cint, cstr, get_datetime, safe_json_loads
from pytz import timezone
from requests.exceptions import ReadTimeout, ConnectTimeout, HTTPError

JsonDict = Dict[str, Any]


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
                url=url, method=method, headers=headers, json=body, params=params, files=files , timeout=30
            )
            # mymb_b2c gives useful info in response text, show it in error logs
            if response.text.strip() == '1' or response.text.strip() == 'false':
                return response.text
            response.reason = cstr(response.reason) + cstr(response.text)
            response.raise_for_status()
        except (ReadTimeout, ConnectTimeout) as timeout_error:
            error_message = f"Timeout occurred while accessing {url}: {str(timeout_error)}"
            frappe.log_error(message=error_message, title=f"Request Timeout - {endpoint}")

            try:
                frappe.sendmail(
                    recipients=["admin@crowdechain.com", "mymb.support@timegroup.it"],
                    subject=f"[TIMEOUT ERROR] API call failed at {endpoint}",
                    message=error_message,
                    sender=frappe.db.get_single_value("Email Account", "email_id")
                )
            except Exception as email_error:
                frappe.log_error(
                    message=f"Failed to send timeout notification email: {str(email_error)}",
                    title="Sendmail Failure"
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
                try:
                    frappe.sendmail(
                        recipients=["admin@crowdechain.com"],
                        subject=f"[SERVER ERROR] Request failed at {endpoint}",
                        message=error_message,
                        sender=frappe.db.get_single_value("Email Account", "email_id")
                    )
                except Exception as email_error:
                    frappe.log_error(
                        message=f"Failed to send server error email: {str(email_error)}",
                        title="Sendmail Failure"
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

    