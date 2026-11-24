"""Fake outside systems for tests: nothing is printed and no file is read."""

from dataclasses import replace

from campus.delivery import OtpSender
from campus.records import RecordsClient, UniversityMember


class FakeOtpSender(OtpSender):
    """OTP sender that remembers every message instead of sending it."""

    def __init__(self) -> None:
        """Start with no sent messages."""
        self.sent_messages: list[tuple[str, str]] = []

    def send_otp(self, destination: str, code: str) -> None:
        """Remember the destination and the code.

        Args:
            destination: An email address or a mobile number.
            code: The plain OTP code.
        """
        self.sent_messages.append((destination, code))

    @property
    def last_destination(self) -> str:
        """Return where the most recent OTP was sent.

        Returns:
            The destination of the last message.
        """
        return self.sent_messages[-1][0]

    @property
    def last_code(self) -> str:
        """Return the most recent plain OTP code.

        Returns:
            The code of the last message.
        """
        return self.sent_messages[-1][1]


class FailingOtpSender(FakeOtpSender):
    """OTP sender whose delivery service is down."""

    def send_otp(self, destination: str, code: str) -> None:
        """Remember the attempt, then fail like a broken delivery service.

        Args:
            destination: An email address or a mobile number.
            code: The plain OTP code.

        Raises:
            ConnectionError: Always.
        """
        super().send_otp(destination, code)
        raise ConnectionError("delivery service unavailable")


class FakeRecordsClient(RecordsClient):
    """University records kept in memory. Tests may change them (FR-02, FR-04)."""

    def __init__(self, members: tuple[UniversityMember, ...] = ()) -> None:
        """Store the members by IUB ID number.

        Args:
            members: The people in the fake records.
        """
        self._members = {member.id_number: member for member in members}

    def find_member(self, id_number: str) -> UniversityMember | None:
        """Find a person by IUB ID number.

        Args:
            id_number: The IUB ID number to look up.

        Returns:
            The matching member, or None.
        """
        return self._members.get(id_number)

    def remove_member(self, id_number: str) -> None:
        """Remove a person, as when they leave the university.

        Args:
            id_number: The IUB ID number to remove.
        """
        del self._members[id_number]

    def change_member(self, id_number: str, **changes: str | None) -> None:
        """Change details of a person, for example a new role.

        Args:
            id_number: The IUB ID number of the person.
            changes: New values for ``name``, ``role``, ``email`` or ``mobile``.
        """
        self._members[id_number] = replace(self._members[id_number], **changes)
