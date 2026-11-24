"""Access to the IUB university records.

The real records are an outside system. During development they are
simulated by a JSON file. The rest of the code uses only the
``RecordsClient`` interface, so the real system can replace the file later.
This module must not import models.
"""

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings
from django.utils.module_loading import import_string

from campus.constants import (
    RECORD_KEY_EMAIL,
    RECORD_KEY_ID_NUMBER,
    RECORD_KEY_MOBILE,
    RECORD_KEY_NAME,
    RECORD_KEY_ROLE,
    RECORDS_FILE_ENCODING,
)


@dataclass(frozen=True)
class UniversityMember:
    """One person in the university records.

    Attributes:
        id_number: The IUB ID number.
        name: The full name, as one string.
        role: One of the role constants, for example ``"student"``.
        email: The registered email, or None if there is none.
        mobile: The registered mobile number, or None if there is none.
    """

    id_number: str
    name: str
    role: str
    email: str | None
    mobile: str | None


class RecordsClient(ABC):  # pylint: disable=too-few-public-methods
    """Interface for looking up people in the university records."""

    @abstractmethod
    def find_member(self, id_number: str) -> UniversityMember | None:
        """Find a person by IUB ID number.

        Args:
            id_number: The IUB ID number to look up.

        Returns:
            The matching member, or None if the ID is not in the records.
        """


class JsonRecordsClient(RecordsClient):  # pylint: disable=too-few-public-methods
    """Records client that reads a JSON file (development and demo only)."""

    def __init__(self, file_path: Path | None = None) -> None:
        """Remember which JSON file to read.

        Args:
            file_path: Path of the records file. Defaults to
                ``settings.FIXIT_RECORDS_FILE``.
        """
        self._file_path = Path(file_path or settings.FIXIT_RECORDS_FILE)

    def find_member(self, id_number: str) -> UniversityMember | None:
        """Find a person by IUB ID number in the JSON file.

        Args:
            id_number: The IUB ID number to look up.

        Returns:
            The matching member, or None if the ID is not in the file.

        Raises:
            OSError: If the records file cannot be read.
            json.JSONDecodeError: If the records file is not valid JSON.
            KeyError: If the matching person has no name or no role.
        """
        with self._file_path.open(encoding=RECORDS_FILE_ENCODING) as records_file:
            people = json.load(records_file)
        for person in people:
            if person[RECORD_KEY_ID_NUMBER] == id_number:
                return UniversityMember(
                    id_number=person[RECORD_KEY_ID_NUMBER],
                    name=person[RECORD_KEY_NAME],
                    role=person[RECORD_KEY_ROLE],
                    email=person.get(RECORD_KEY_EMAIL),
                    mobile=person.get(RECORD_KEY_MOBILE),
                )
        return None


def get_records_client() -> RecordsClient:
    """Create the records client named in ``settings.FIXIT_RECORDS_CLIENT``.

    Returns:
        A new records client.

    Raises:
        ImportError: If the setting does not name an importable class.
    """
    client_class = import_string(settings.FIXIT_RECORDS_CLIENT)
    return client_class()
