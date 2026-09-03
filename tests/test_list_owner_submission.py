"""Tests for submission progress history used by the main-page health indicator."""

import unittest
from datetime import datetime, timedelta

from condor_io.list_owner_submission import add_progress_history, select_progress_snapshot


class SubmissionProgressHistoryTests(unittest.TestCase):
    def test_selects_newest_snapshot_at_least_six_hours_old(self):
        current_time = datetime(2026, 9, 3, 16, 0, 0)
        snapshots = [
            {"snapshot_id": 3, "update_time": current_time - timedelta(hours=2)},
            {"snapshot_id": 2, "update_time": current_time - timedelta(hours=6, minutes=10)},
            {"snapshot_id": 1, "update_time": current_time - timedelta(hours=8)},
        ]

        selected = select_progress_snapshot(snapshots, current_time)

        self.assertEqual(selected["snapshot_id"], 2)

    def test_returns_none_without_sufficient_history(self):
        current_time = datetime(2026, 9, 3, 16, 0, 0)
        snapshots = [
            {"snapshot_id": 1, "update_time": current_time - timedelta(hours=5)},
        ]

        self.assertIsNone(select_progress_snapshot(snapshots, current_time))

    def test_adds_previous_done_count_to_matching_current_rows(self):
        historical_time = datetime(2026, 9, 3, 9, 30, 0)
        current_time = datetime(2026, 9, 3, 16, 0, 0)
        historical_snapshot = {
            "update_time": historical_time,
            "payload": {
                "CLAS12OCR": {
                    "results": [
                        {"user_submission_id": 100, "done": 15},
                        {"user_submission_id": 101, "done": 20},
                    ]
                }
            },
        }
        current_results = [
            {"user_submission_id": 101, "done": 20},
            {"user_submission_id": 102, "done": 5},
        ]

        add_progress_history(current_results, historical_snapshot, "CLAS12OCR", current_time)

        self.assertEqual(current_results[0]["progress_previous_done"], 20)
        self.assertEqual(current_results[0]["progress_window_hours"], 6.5)
        self.assertNotIn("progress_previous_done", current_results[1])


if __name__ == "__main__":
    unittest.main()
