"""Named constants for FixIt Campus: rules, roles, statuses and messages.

Every value is immutable (str, int or tuple) so no module can change it.

User-facing messages come from three sources:

- Copied word for word from SRS FR-01: ``MSG_ID_NOT_FOUND``,
  ``MSG_ALREADY_REGISTERED``, ``MSG_PASSWORD_TOO_SHORT``,
  ``MSG_NO_CONTACT_DETAILS`` and ``MSG_TOO_MANY_REQUESTS``.
- Copied word for word from SRS FR-02 to FR-04: ``MSG_INVALID_LOGIN``,
  ``MSG_ACCOUNT_LOCKED``, ``MSG_ACCOUNT_NO_LONGER_ACTIVE``,
  ``MSG_NOT_AUTHORIZED``, ``MSG_SESSION_EXPIRED`` and ``MSG_RESET_OTP_SENT``.
- From the UI design: ``MSG_OTP_INCORRECT`` and ``MSG_OTP_NO_LONGER_VALID``.
- Our own wording: ``MSG_OTP_EXPIRED``, ``MSG_OTP_FORMAT``,
  ``MSG_NEW_OTP_SENT`` and ``MSG_PASSWORD_CHANGED``.

The UI-design and own-wording messages have not been checked against the
SRS Wiki yet.
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
# Same size as Django's own ``first_name`` field, where the name is stored.
MEMBER_NAME_MAX_LENGTH = 150

# --- Account statuses ---
# "Locked" is not a status: it is derived from ``User.locked_until`` so the
# two can never disagree (FR-02).
ACCOUNT_PENDING_ACTIVATION = "pending_activation"
ACCOUNT_ACTIVE = "active"
ACCOUNT_STATUS_CHOICES = (
    (ACCOUNT_PENDING_ACTIVATION, "Pending activation"),
    (ACCOUNT_ACTIVE, "Active"),
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

# --- OTP purposes ---
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

# --- Business rules (FR-02, FR-03) ---
LOGIN_MAX_FAILED_ATTEMPTS = 5
ACCOUNT_LOCK_MINUTES = 15
SESSION_IDLE_TIMEOUT_MINUTES = 15

# --- Input shape (checked by forms) ---
ID_NUMBER_MAX_LENGTH = 20
OTP_PATTERN = rf"^\d{{{OTP_LENGTH}}}$"

# --- Presentation: session keys, URL names and templates ---
SESSION_REGISTER_ID_NUMBER = "register_id_number"
SESSION_RESET_ID_NUMBER = "reset_id_number"
SESSION_LAST_ACTIVITY = "last_activity"
URL_NAME_REGISTER = "register"
URL_NAME_REGISTER_VERIFY = "register_verify"
URL_NAME_REGISTER_NEW_OTP = "register_new_otp"
URL_NAME_REGISTER_DONE = "register_done"
URL_NAME_LOGIN = "login"
URL_NAME_LOGOUT = "logout"
URL_NAME_HOME = "home"
URL_NAME_PASSWORD_RESET = "password_reset"
URL_NAME_PASSWORD_RESET_VERIFY = "password_reset_verify"
URL_NAME_PASSWORD_RESET_NEW_OTP = "password_reset_new_otp"
TEMPLATE_REGISTER = "campus/register.html"
TEMPLATE_REGISTER_VERIFY = "campus/register_verify.html"
TEMPLATE_REGISTER_DONE = "campus/register_done.html"
TEMPLATE_LOGIN = "campus/login.html"
TEMPLATE_HOME = "campus/home.html"
TEMPLATE_PASSWORD_RESET = "campus/password_reset.html"
TEMPLATE_PASSWORD_RESET_VERIFY = "campus/password_reset_verify.html"
TEMPLATE_FORBIDDEN = "campus/403.html"

# --- Home page placeholder for each role: (role, heading, short text) ---
# Real home pages come with later features.
HOME_PAGE_TEXT = (
    (
        ROLE_STUDENT,
        "Student home",
        "Here you will submit complaints and follow their progress.",
    ),
    (
        ROLE_FACULTY,
        "Faculty home",
        "Here you will submit complaints and follow their progress.",
    ),
    (
        ROLE_MAINTENANCE_STAFF,
        "Maintenance staff home",
        "Here you will see the complaints assigned to you.",
    ),
    (
        ROLE_SUPERVISOR,
        "Maintenance supervisor home",
        "Here you will assign complaints and watch the work of your team.",
    ),
    (
        ROLE_ADMINISTRATOR,
        "University administration home",
        "Here you will see reports and manage complaints.",
    ),
)

# --- University records file (JSON keys) ---
RECORDS_FILE_ENCODING = "utf-8"
RECORD_KEY_ID_NUMBER = "id_number"
RECORD_KEY_NAME = "name"
RECORD_KEY_ROLE = "role"
RECORD_KEY_EMAIL = "email"
RECORD_KEY_MOBILE = "mobile"
# Developer-facing: the records data is wrong. Leaves out the name itself.
RECORDS_ERROR_EMPTY_NAME = "University record {id_number} has an empty name."

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
MSG_NEW_OTP_SENT = "A new OTP has been sent. The earlier OTP no longer works."

# --- User-facing messages (SRS FR-02, FR-03, FR-04) ---
MSG_INVALID_LOGIN = "Invalid ID or password"
MSG_ACCOUNT_LOCKED = "Your account is locked. Please try again later."
MSG_ACCOUNT_NO_LONGER_ACTIVE = (
    "Your account is no longer active. Please contact the university administration."
)
MSG_NOT_AUTHORIZED = "You are not authorized to view this page."
MSG_SESSION_EXPIRED = "Your session has expired. Please log in again."
MSG_RESET_OTP_SENT = "If this ID is registered, a one-time password has been sent."
# Our own wording (not in the SRS): shown on the login page after a reset.
MSG_PASSWORD_CHANGED = "Your password has been changed. Please log in."
