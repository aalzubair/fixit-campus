"""Tests for records.py: the JSON records client and its factory."""

import json
import shutil
import tempfile
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase, override_settings

from campus.constants import (
    RECORD_KEY_EMAIL,
    RECORD_KEY_ID_NUMBER,
    RECORD_KEY_MOBILE,
    RECORD_KEY_ROLE,
    RECORDS_FILE_ENCODING,
    ROLE_CHOICES,
    ROLE_MAINTENANCE_STAFF,
    ROLE_STUDENT,
)
from campus.records import (
    JsonRecordsClient,
    UniversityMember,
    get_records_client,
)
from campus.tests.base import NO_CONTACT_ID, STUDENT_EMAIL, STUDENT_ID, UNKNOWN_ID
from campus.tests.fakes import FakeRecordsClient

TEMP_RECORDS = [
    {
        RECORD_KEY_ID_NUMBER: STUDENT_ID,
        RECORD_KEY_ROLE: ROLE_STUDENT,
        RECORD_KEY_EMAIL: STUDENT_EMAIL,
        RECORD_KEY_MOBILE: None,
    },
    # Keys left out on purpose: a missing key must mean "no contact".
    {RECORD_KEY_ID_NUMBER: NO_CONTACT_ID, RECORD_KEY_ROLE: ROLE_MAINTENANCE_STAFF},
]


class JsonRecordsClientTests(SimpleTestCase):
    """JsonRecordsClient reads people from a temporary JSON file."""

    def setUp(self) -> None:
        """Write the temporary records file."""
        temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, temp_dir)
        self.file_path = Path(temp_dir) / "records.json"
        self.file_path.write_text(json.dumps(TEMP_RECORDS), RECORDS_FILE_ENCODING)
        self.client_under_test = JsonRecordsClient(self.file_path)

    def test_finds_member_by_id(self) -> None:
        """A known ID returns the member with role and contact details."""
        member = self.client_under_test.find_member(STUDENT_ID)
        self.assertEqual(
            member, UniversityMember(STUDENT_ID, ROLE_STUDENT, STUDENT_EMAIL, None)
        )

    def test_missing_contact_keys_become_none(self) -> None:
        """Missing email and mobile keys are read as None."""
        member = self.client_under_test.find_member(NO_CONTACT_ID)
        self.assertIsNone(member.email)
        self.assertIsNone(member.mobile)

    def test_unknown_id_returns_none(self) -> None:
        """An ID that is not in the file returns None."""
        self.assertIsNone(self.client_under_test.find_member(UNKNOWN_ID))

    def test_missing_file_raises_error(self) -> None:
        """Exception: a missing records file is a configuration error."""
        client = JsonRecordsClient(self.file_path.with_name("missing.json"))
        with self.assertRaises(FileNotFoundError):
            client.find_member(STUDENT_ID)

    def test_broken_file_raises_error(self) -> None:
        """Exception: a file that is not JSON cannot be read."""
        self.file_path.write_text("not json", RECORDS_FILE_ENCODING)
        with self.assertRaises(json.JSONDecodeError):
            self.client_under_test.find_member(STUDENT_ID)


class ShippedRecordsFileTests(SimpleTestCase):
    """The demo records file has the people the task asks for."""

    def setUp(self) -> None:
        """Read the demo records file named in settings."""
        self.people = json.loads(
            Path(settings.FIXIT_RECORDS_FILE).read_text(RECORDS_FILE_ENCODING)
        )

    def test_every_role_is_present(self) -> None:
        """Each of the five roles has at least one person."""
        roles = {person[RECORD_KEY_ROLE] for person in self.people}
        self.assertEqual(roles, {role for role, _ in ROLE_CHOICES})

    def test_has_mobile_only_and_no_contact_people(self) -> None:
        """One person has only a mobile number and one has no contact."""
        contacts = [
            (person[RECORD_KEY_EMAIL], person[RECORD_KEY_MOBILE])
            for person in self.people
        ]
        self.assertTrue(any(email is None and mobile for email, mobile in contacts))
        self.assertIn((None, None), contacts)


class GetRecordsClientTests(SimpleTestCase):
    """get_records_client builds the class named in settings."""

    def test_default_setting_gives_json_client(self) -> None:
        """The project uses the JSON client by default."""
        self.assertIsInstance(get_records_client(), JsonRecordsClient)

    @override_settings(FIXIT_RECORDS_CLIENT="campus.tests.fakes.FakeRecordsClient")
    def test_setting_selects_client_class(self) -> None:
        """Changing the setting swaps the records system."""
        self.assertIsInstance(get_records_client(), FakeRecordsClient)

    @override_settings(FIXIT_RECORDS_CLIENT="campus.records.NoSuchClient")
    def test_wrong_setting_raises_import_error(self) -> None:
        """Exception: a setting that names no class fails clearly."""
        with self.assertRaises(ImportError):
            get_records_client()
