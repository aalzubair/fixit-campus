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
# The roles that may submit, browse, follow and reopen complaints (FR-06).
COMPLAINANT_ROLES = (ROLE_STUDENT, ROLE_FACULTY, ROLE_ADMINISTRATOR)

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

# --- Complaint statuses (SRS FR-06 to FR-20, SDS complaint state diagram) ---
# Overdue is not a status: it is a mark on an Open complaint (SRS Glossary).
COMPLAINT_OPEN = "open"
COMPLAINT_IN_PROGRESS = "in_progress"
COMPLAINT_RESOLVED = "resolved"
COMPLAINT_REJECTED = "rejected"
COMPLAINT_STATUS_CHOICES = (
    (COMPLAINT_OPEN, "Open"),
    (COMPLAINT_IN_PROGRESS, "In Progress"),
    (COMPLAINT_RESOLVED, "Resolved"),
    (COMPLAINT_REJECTED, "Rejected"),
)
COMPLAINT_STATUS_MAX_LENGTH = 12
# Complaints that other users may see in the lists and follow (FR-07, FR-21).
BROWSABLE_STATUSES = (COMPLAINT_OPEN, COMPLAINT_IN_PROGRESS)

# --- Complaint categories (the value stored, the label shown) ---
# Taken from the UI design. The SRS (Assumption 4) says the university supplies
# the final list, so add or rename entries here when it does.
CATEGORY_CHOICES = (
    ("electrical", "Electrical"),
    ("plumbing", "Plumbing"),
    ("furniture", "Furniture"),
    ("air_conditioning", "Air conditioning"),
    ("lift", "Lift"),
    ("wifi", "Wi-Fi"),
)
CATEGORY_MAX_LENGTH = 20

# --- Complaint locations: (building, floor, room or area) ---
# Example list taken from the UI design; replace it with the university's list
# (SRS Assumption 4). An empty floor means the place has no floor (a lift).
LOCATIONS = (
    ("Block A", "1st floor", "Room 105"),
    ("Block A", "2nd floor", "Room 215"),
    ("Block A", "3rd floor", "Room 302"),
    ("Block B", "Ground floor", "Washroom"),
    ("Block B", "1st floor", "Washroom"),
    ("Block C", "", "Lift 2"),
    ("Block C", "1st floor", "Room 105"),
    ("Block C", "2nd floor", "Room 208"),
    ("Block C", "4th floor", "Room 410"),
    ("Block D", "1st floor", "Room 112"),
    ("Library", "1st floor", "Reading hall"),
)

# --- Complaint field sizes and storage ---
# "CMP-2026-01482" is 14 characters; 20 leaves room if the number grows.
COMPLAINT_ID_MAX_LENGTH = 20
# A complaint ID is the prefix plus a number padded to this width: CMP-2026-00001.
COMPLAINT_ID_PREFIX_FORMAT = "CMP-{year}-"
COMPLAINT_ID_NUMBER_WIDTH = 5
LOCATION_PART_MAX_LENGTH = 50
DESCRIPTION_MAX_LENGTH = 1000
# Used for both the reopen reason (FR-10) and the reject reason (FR-20).
REASON_MAX_LENGTH = 500
# Folder inside MEDIA_ROOT where complaint photos are stored (FR-06).
COMPLAINT_PHOTO_DIR = "complaint_photos"

# --- Complaint photo rules (FR-06, NFR-17) ---
PHOTO_MAX_MEGABYTES = 5
BYTES_PER_MEGABYTE = 1024 * 1024
PHOTO_ALLOWED_EXTENSIONS = (".jpg", ".jpeg", ".png")
# The first bytes of a real JPG and PNG file, in hex. The file name alone is
# not trusted, because anyone can rename a file.
PHOTO_SIGNATURES_HEX = ("ffd8ff", "89504e470d0a1a0a")
PHOTO_SIGNATURE_BYTES = 8

# --- Complaint rules (FR-10) ---
REOPEN_WINDOW_DAYS = 7

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
URL_NAME_SUBMIT_COMPLAINT = "submit_complaint"
URL_NAME_SIMILAR_COMPLAINTS = "similar_complaints"
URL_NAME_COMPLAINT_SUBMITTED = "complaint_submitted"
URL_NAME_EXISTING_COMPLAINTS = "existing_complaints"
URL_NAME_MY_COMPLAINTS = "my_complaints"
URL_NAME_COMPLAINT_DETAIL = "complaint_detail"
URL_NAME_COMPLAINT_PHOTO = "complaint_photo"
URL_NAME_FOLLOW_COMPLAINT = "follow_complaint"
URL_NAME_UNFOLLOW_COMPLAINT = "unfollow_complaint"
URL_NAME_REOPEN_COMPLAINT = "reopen_complaint"
TAB_MY_COMPLAINTS = "mine"
TAB_FOLLOWING = "following"
TEMPLATE_REGISTER = "campus/register.html"
TEMPLATE_REGISTER_VERIFY = "campus/register_verify.html"
TEMPLATE_REGISTER_DONE = "campus/register_done.html"
TEMPLATE_LOGIN = "campus/login.html"
TEMPLATE_HOME = "campus/home.html"
TEMPLATE_PASSWORD_RESET = "campus/password_reset.html"
TEMPLATE_PASSWORD_RESET_VERIFY = "campus/password_reset_verify.html"
TEMPLATE_FORBIDDEN = "campus/403.html"
TEMPLATE_SUBMIT_COMPLAINT = "campus/complaint_submit.html"
TEMPLATE_SIMILAR_COMPLAINTS = "campus/_similar_complaints.html"
TEMPLATE_COMPLAINT_SUBMITTED = "campus/complaint_submitted.html"
TEMPLATE_EXISTING_COMPLAINTS = "campus/existing_complaints.html"
TEMPLATE_MY_COMPLAINTS = "campus/my_complaints.html"
TEMPLATE_COMPLAINT_DETAIL = "campus/complaint_detail.html"
TEMPLATE_REOPEN_COMPLAINT = "campus/complaint_reopen.html"

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

# --- User-facing messages (SRS FR-06, FR-09, FR-10, FR-21) ---
MSG_PHOTO_INVALID = "Photo must be a JPG or PNG file of up to 5 MB."
MSG_NO_COMPLAINTS = "You have no complaints to show."
MSG_COMPLAINT_NOT_ALLOWED = "You are not allowed to view this complaint."
MSG_ONLY_RESOLVED_CAN_REOPEN = "Only Resolved complaints can be reopened."
MSG_REASON_REQUIRED = "Please enter a reason."
MSG_NO_FILTER_MATCH = "No complaints match your filters."
# From the UI design (SRS FR-10 only says "asks me to submit a new complaint").
MSG_REOPEN_EXPIRED = (
    "This complaint was resolved more than 7 days ago and can no longer be "
    "reopened. Please submit a new complaint."
)
# From the UI design (not word for word in the SRS).
MSG_SELECT_CATEGORY = "Please select a category."
MSG_SELECT_LOCATION = "Please select a location."
MSG_COMPLAINT_NOT_SAVED = (
    "Your complaint was not saved. Fix the highlighted fields and submit again."
)
# Our own wording (not in the SRS).
MSG_FOLLOWING_STARTED = "You are now following this complaint."
MSG_FOLLOWING_STOPPED = "You stopped following this complaint."
MSG_CANNOT_FOLLOW_OWN = "You cannot follow your own complaint."
MSG_ONLY_BROWSABLE_CAN_FOLLOW = "Only Open or In Progress complaints can be followed."
MSG_COMPLAINT_REOPENED = "Your complaint was reopened."
