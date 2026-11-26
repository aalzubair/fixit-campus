"""Tests for the small helpers of the Complaint and Follow models."""

from django.test import SimpleTestCase

from campus.models import Complaint, Follow, User


class ComplaintHelperTests(SimpleTestCase):
    """Complaint.location_label and the __str__ methods."""

    def test_location_label_joins_all_three_parts(self) -> None:
        """Building, floor and room are joined with commas."""
        complaint = Complaint(
            building="Block A", floor="3rd floor", room_or_area="Room 302"
        )
        self.assertEqual(complaint.location_label(), "Block A, 3rd floor, Room 302")

    def test_location_label_leaves_out_an_empty_floor(self) -> None:
        """A place without a floor, such as a lift, has no empty gap."""
        complaint = Complaint(building="Block C", floor="", room_or_area="Lift 2")
        self.assertEqual(complaint.location_label(), "Block C, Lift 2")

    def test_complaint_str_is_the_complaint_id(self) -> None:
        """A complaint is shown by its ID."""
        self.assertEqual(
            str(Complaint(complaint_id="CMP-2026-00001")), "CMP-2026-00001"
        )

    def test_follow_str_names_user_and_complaint(self) -> None:
        """A follow is shown as "<user> follows <complaint>"."""
        follow = Follow(
            user=User(username="1000001"), complaint=Complaint(complaint_id="CMP-1")
        )
        self.assertEqual(str(follow), "1000001 follows CMP-1")
