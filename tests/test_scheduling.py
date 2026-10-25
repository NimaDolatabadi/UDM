"""Tests for schedule window and concurrency policy helpers."""

from datetime import datetime
import unittest

from udm.scheduling import schedule_is_open, schedule_limit


class SchedulingTests(unittest.TestCase):
    def setUp(self):
        self.schedule = {
            "active": True,
            "max_dl": 2,
            "start_date": "2026-07-01",
            "end_date": "2026-07-31",
            "start_time": "22:00",
            "end_time": "02:00",
            "recurrence": "Every Day",
        }

    def test_overnight_window_opens_on_both_sides_of_midnight(self):
        self.assertTrue(
            schedule_is_open(self.schedule, datetime(2026, 7, 10, 23, 0))
        )
        self.assertTrue(
            schedule_is_open(self.schedule, datetime(2026, 7, 10, 1, 0))
        )
        self.assertFalse(
            schedule_is_open(self.schedule, datetime(2026, 7, 10, 12, 0))
        )

    def test_disabled_invalid_and_recurrence_are_enforced(self):
        self.schedule["recurrence"] = "Even Days"
        self.assertFalse(
            schedule_is_open(self.schedule, datetime(2026, 7, 11, 23, 0))
        )
        self.schedule["active"] = False
        self.assertFalse(
            schedule_is_open(self.schedule, datetime(2026, 7, 10, 23, 0))
        )
        self.assertEqual(schedule_limit({"max_dl": 0}), 1)


if __name__ == "__main__":
    unittest.main()
