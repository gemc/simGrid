"""Tests for pending-submission fair-share priorities."""

import unittest
from datetime import datetime, timedelta

from db_io.priority_submissions import (
    compute_history_loads,
    compute_priorities,
    compute_running_jobs_from_snapshot,
    compute_running_jobs_by_user,
)
from db_io.database import build_contiguous_priority_updates
from statuses import NOTSUBMITTED, SUBMITTED


TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def format_time(value):
    """Format a datetime like the submissions table."""
    return value.strftime(TIME_FORMAT)


def pending_row(user, submission_id, client_time):
    """Build one pending submission row."""
    return {
        "user": user,
        "user_submission_id": submission_id,
        "client_time": format_time(client_time),
        "server_time": None,
        "run_status": NOTSUBMITTED,
    }


class PriorityHistoryTests(unittest.TestCase):
    def test_pending_priorities_are_compacted_and_zero_rows_are_appended(self):
        rows = [
            {
                "user_submission_id": 11651,
                "client_time": "2026-07-31 05:54:17",
                "priority": "21",
            },
            {
                "user_submission_id": 11787,
                "client_time": "2026-08-25 18:12:19",
                "priority": "6",
            },
            {
                "user_submission_id": 11810,
                "client_time": "2026-08-31 14:14:51",
                "priority": "0",
            },
        ]

        self.assertEqual(
            build_contiguous_priority_updates(rows),
            [("1", 11787), ("2", 11651), ("3", 11810)],
        )

    def test_submitted_load_uses_server_time_before_client_time(self):
        now = datetime.now().replace(microsecond=0)
        rows = [
            {
                "user": "recently_served",
                "user_submission_id": 1,
                "client_time": format_time(now - timedelta(days=60)),
                "server_time": format_time(now),
                "run_status": SUBMITTED,
            },
            {
                "user": "client_time_fallback",
                "user_submission_id": 2,
                "client_time": format_time(now - timedelta(days=14)),
                "server_time": None,
                "run_status": SUBMITTED,
            },
        ]

        _, submitted_loads, _, _ = compute_history_loads(
            rows,
            time_format=TIME_FORMAT,
            history_half_life_days=7.0,
        )

        self.assertGreater(submitted_loads["recently_served"], 0.99)
        self.assertAlmostEqual(submitted_loads["client_time_fallback"], 0.25, delta=0.01)

    def test_running_jobs_are_summed_by_portal_user(self):
        submission_rows = [
            {"user": "alpha", "pool_node": "101"},
            {"user": "alpha", "pool_node": 102},
            {"user": "beta", "pool_node": "103"},
        ]
        condor_batches = {
            101: {"counts": {"RUN": 4000}},
            102: {"counts": {"RUN": 6822}},
            103: {"counts": {"RUN": 7}},
            999: {"counts": {"RUN": 500}},
        }

        self.assertEqual(
            compute_running_jobs_by_user(submission_rows, condor_batches),
            {"alpha": 10822, "beta": 7},
        )

    def test_running_jobs_are_read_from_stored_snapshot(self):
        snapshot = {
            "payload": {
                "CLAS12OCR": {
                    "results": [
                        {"user": "alpha", "run": 4000},
                        {"user": "alpha", "run": 6822},
                        {"user": "beta", "run": 7},
                        {"user": "pending", "run": None},
                    ]
                }
            }
        }

        self.assertEqual(
            compute_running_jobs_from_snapshot(snapshot, "CLAS12OCR"),
            {"alpha": 10822, "beta": 7},
        )


class InterleavedPriorityTests(unittest.TestCase):
    def test_user_with_10822_running_jobs_is_not_first(self):
        now = datetime.now().replace(microsecond=0)
        rows = [
            pending_row("nlbucuru", 1, now - timedelta(days=30)),
            pending_row("other", 2, now - timedelta(days=1)),
        ]

        _, baseline, _, _ = compute_priorities(
            rows=rows,
            algorithm="aging_interleaved",
            time_format=TIME_FORMAT,
            half_life_days=0.5,
            queue_penalty_exponent=0.25,
            history_half_life_days=7.0,
        )
        _, prioritized, _, _ = compute_priorities(
            rows=rows,
            algorithm="aging_interleaved",
            time_format=TIME_FORMAT,
            half_life_days=0.5,
            queue_penalty_exponent=0.25,
            history_half_life_days=7.0,
            running_jobs_by_user={"nlbucuru": 10822},
        )

        self.assertEqual(baseline[0]["user"], "nlbucuru")
        self.assertEqual(prioritized[0]["user"], "other")
        self.assertEqual(prioritized[1]["running_jobs_for_user"], 10822)

    def test_recalculation_continues_recent_users_burst(self):
        now = datetime.now().replace(microsecond=0)
        old_client_time = now - timedelta(days=60)
        recent_client_time = now - timedelta(days=1)
        rows = [
            pending_row("alpha", 1, old_client_time),
            pending_row("alpha", 2, old_client_time + timedelta(seconds=1)),
            pending_row("alpha", 3, old_client_time + timedelta(seconds=2)),
            pending_row("beta", 4, recent_client_time),
            pending_row("beta", 5, recent_client_time + timedelta(seconds=1)),
        ]

        def prioritized_users():
            _, prioritized, _, _ = compute_priorities(
                rows=rows,
                algorithm="aging_interleaved",
                time_format=TIME_FORMAT,
                half_life_days=7.0,
                queue_penalty_exponent=1.0,
                history_half_life_days=7.0,
                burst_per_user=2,
            )
            return [row["user"] for row in prioritized]

        self.assertEqual(prioritized_users()[:2], ["alpha", "alpha"])

        rows[0]["run_status"] = SUBMITTED
        rows[0]["server_time"] = format_time(now)
        self.assertEqual(prioritized_users()[:3], ["alpha", "beta", "beta"])

        rows[1]["run_status"] = SUBMITTED
        rows[1]["server_time"] = format_time(now + timedelta(seconds=1))
        self.assertEqual(prioritized_users()[:2], ["beta", "beta"])


if __name__ == "__main__":
    unittest.main()
