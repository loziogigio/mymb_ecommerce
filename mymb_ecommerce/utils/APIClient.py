import base64
from typing import Any, Dict, List, Optional, Tuple

import frappe
import requests
from frappe import _
from frappe.utils import cint, cstr, get_datetime
from pytz import timezone

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
                url=url, method=method, headers=headers, json=body, params=params, files=files
            )
            # mymb_b2c gives useful info in response text, show it in error logs
            response.reason = cstr(response.reason) + cstr(response.text)
            response.raise_for_status()
        except Exception as e:
            frappe.log_error(message=f"An error occurred while : {str(e)}", title="Request")
            return None, False

        if method == "GET" and "application/json" not in response.headers.get("content-type"):
            return response.content, True

        data = frappe._dict(response.json())
        status = data.successful if data.successful is not None else True

        if not status:
            req = response.request
            url = f"URL: {req.url}"
            body = f"body:  {req.body.decode('utf-8')}"
            request_data = "\n\n".join([url, body])
            message = ", ".join(cstr(error["message"]) for error in data.errors)

        return data, status

    