"""Tests for pending-submission fair-share priorities."""

import unittest
from datetime import datetime, timedelta

from db_io.priority_submissions import compute_history_loads, compute_priorities
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


class InterleavedPriorityTests(unittest.TestCase):
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
