import functools
import jwt
import datetime
import frappe
from frappe import _

# Your JWT secret key - make sure to keep it secret!
JWT_SECRET_KEY = "your_jwt_secret_key"
# Token expiration time (e.g., 24 hours)
# Token expiration time (e.g., 240 minutes)
JWT_EXPIRATION_DELTA = 240 * 60


class JWTManager:
    def __init__(self, secret_key, algorithm="HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm

    def encode(self, payload, expiration_minutes=None):
        if expiration_minutes:
            payload["exp"] = datetime.datetime.utcnow() + datetime.timedelta(minutes=expiration_minutes)
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token

    def decode(self, token):
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    @staticmethod
    def jwt_required(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            JWTManager.verify_jwt_in_request()
            return fn(*args, **kwargs)
        return wrapper
    
    @staticmethod
    def verify_jwt_in_request():
        jwt_manager_instance = JWTManager(secret_key=JWT_SECRET_KEY)
        try:
            jwt_header = frappe.get_request_header("Authorization")
            if not jwt_header:
                raise ValueError("Missing Authorization header")

            parts = jwt_header.split()
            if len(parts) != 2 or parts[0].lower() != "bearer":
                raise ValueError("Invalid Authorization header format")

            token = parts[1]
            payload = jwt_manager_instance.decode(token)

            frappe.local.jwt_payload = payload

        except Exception as e:
            frappe.throw(_("Invalid JWT token: {0}").format(str(e)))
