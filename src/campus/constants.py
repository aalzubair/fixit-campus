"""Named constants for FixIt Campus: rules, roles, statuses and messages.

Every value is immutable (str, int or tuple) so no module can change it.
Messages shown to users match the SRS word for word.
"""

# --- Roles (the value stored in the database and in the university records) ---
ROLE_STUDENT = "student"
ROLE_FACULTY = "faculty"
ROLE_MAINTENANCE_STAFF = "maintenance_staff"
ROLE_SUPERVISOR = "supervisor"
ROLE_ADMINISTRATOR = "administrator"
ROLE_CHOICES = (
    (ROLE_STUDENT, "Student"),
    (ROLE_FACULTY, "Faculty Member"),
    (ROLE_MAINTENANCE_STAFF, "Maintenance Staff"),
    (ROLE_SUPERVISOR, "Maintenance Supervisor"),
    (ROLE_ADMINISTRATOR, "University Administration"),
)
ROLE_MAX_LENGTH = 20

# --- Account statuses ---
ACCOUNT_PENDING_ACTIVATION = "pending_activation"
ACCOUNT_ACTIVE = "active"
ACCOUNT_LOCKED = "locked"
ACCOUNT_STATUS_CHOICES = (
    (ACCOUNT_PENDING_ACTIVATION, "Pending activation"),
    (ACCOUNT_ACTIVE, "Active"),
    (ACCOUNT_LOCKED, "Locked"),
)
ACCOUNT_STATUS_MAX_LENGTH = 20

# --- OTP statuses ---
OTP_VALID = "valid"
OTP_USED = "used"
OTP_EXPIRED = "expired"
OTP_INVALID = "invalid"
OTP_STATUS_CHOICES = (
    (OTP_VALID, "Valid"),
    (OTP_USED, "Used"),
    (OTP_EXPIRED, "Expired"),
    (OTP_INVALID, "Invalid"),
)
OTP_STATUS_MAX_LENGTH = 10

# --- OTP purposes (password_reset is used later by FR-04) ---
OTP_PURPOSE_REGISTRATION = "registration"
OTP_PURPOSE_PASSWORD_RESET = "password_reset"
OTP_PURPOSE_CHOICES = (
    (OTP_PURPOSE_REGISTRATION, "Registration"),
    (OTP_PURPOSE_PASSWORD_RESET, "Password reset"),
)
OTP_PURPOSE_MAX_LENGTH = 20

# Same size as Django's own password field, which holds the same kind of hash.
OTP_HASH_MAX_LENGTH = 128

# --- Business rules (FR-01) ---
OTP_LENGTH = 6
OTP_LIFETIME_MINUTES = 5
OTP_MAX_WRONG_ATTEMPTS = 3
OTP_REQUEST_LIMIT = 5
OTP_REQUEST_WINDOW_MINUTES = 15
PASSWORD_MIN_LENGTH = 8

# --- University records file (JSON keys) ---
RECORDS_FILE_ENCODING = "utf-8"
RECORD_KEY_ID_NUMBER = "id_number"
RECORD_KEY_ROLE = "role"
RECORD_KEY_EMAIL = "email"
RECORD_KEY_MOBILE = "mobile"

# --- Development-only console OTP sender ---
CONSOLE_OTP_MESSAGE = "[DEVELOPMENT ONLY] OTP for {destination}: {code}"

# --- User-facing messages (SRS FR-01 and UI design) ---
MSG_ID_NOT_FOUND = (
    "IUB ID number not found. Please contact the university administration."
)
MSG_ALREADY_REGISTERED = "This ID is already registered."
MSG_PASSWORD_TOO_SHORT = "Password must be at least 8 characters."
MSG_NO_CONTACT_DETAILS = (
    "No contact details are registered for this ID. "
    "Please contact the university administration."
)
MSG_TOO_MANY_REQUESTS = "Too many requests. Please try again in 15 minutes."
MSG_OTP_INCORRECT = "Incorrect OTP. Please check it and try again."
MSG_OTP_NO_LONGER_VALID = (
    "Too many wrong attempts. This OTP is no longer valid. Please request a new OTP."
)
MSG_OTP_EXPIRED = "This OTP has expired. Please request a new OTP."
MSG_OTP_FORMAT = "Enter the 6-digit OTP."
