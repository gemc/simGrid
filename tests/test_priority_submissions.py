"""Tests for pending-submission fair-share priorities."""

import json
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from condor_io.list_owner_submission import calculate_average_queue_to_osg_hours
from db_io.priority_submissions import (
    compute_history_loads,
    compute_priorities,
    compute_condor_jobs_from_snapshot,
    compute_condor_jobs_by_user,
    get_round_service_counts,
    print_summary,
    write_priority_json,
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
    def test_average_queue_to_osg_hours_includes_valid_outliers(self):
        rows = [
            {"client_time": "2026-08-01 10:00:00", "server_time": "2026-08-01 12:00:00"},
            {"client_time": "2026-08-02 10:00:00", "server_time": "2026-08-02 14:00:00"},
            {"client_time": "2026-08-03 10:00:00", "server_time": "2026-08-07 14:00:00"},
            {"client_time": "invalid", "server_time": "2026-08-03 14:00:00"},
            {"client_time": "2026-08-04 14:00:00", "server_time": "2026-08-04 10:00:00"},
        ]

        self.assertAlmostEqual(calculate_average_queue_to_osg_hours(rows), 106.0 / 3.0)

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

    def test_condor_jobs_are_summed_by_portal_user(self):
        submission_rows = [
            {"user": "alpha", "pool_node": "101"},
            {"user": "alpha", "pool_node": 102},
            {"user": "beta", "pool_node": "103"},
        ]
        condor_batches = {
            101: {"counts": {"RUN": 4000, "IDLE": 6000}},
            102: {"counts": {"RUN": 6822, "IDLE": 3178}},
            103: {"counts": {"RUN": 7, "IDLE": 0}},
            999: {"counts": {"RUN": 500, "IDLE": 500}},
        }

        self.assertEqual(
            compute_condor_jobs_by_user(submission_rows, condor_batches),
            {"alpha": 10822, "beta": 7},
        )
        self.assertEqual(
            compute_condor_jobs_by_user(submission_rows, condor_batches, state="IDLE"),
            {"alpha": 9178, "beta": 0},
        )

    def test_condor_jobs_are_read_from_stored_snapshot(self):
        snapshot = {
            "payload": {
                "CLAS12OCR": {
                    "results": [
                        {"user": "alpha", "run": 4000, "idle": 6000},
                        {"user": "alpha", "run": 6822, "idle": 3178},
                        {"user": "beta", "run": 7, "idle": 0},
                        {"user": "pending", "run": None, "idle": None},
                    ]
                }
            }
        }

        self.assertEqual(
            compute_condor_jobs_from_snapshot(snapshot, "CLAS12OCR"),
            {"alpha": 10822, "beta": 7},
        )
        self.assertEqual(
            compute_condor_jobs_from_snapshot(snapshot, "CLAS12OCR", state="IDLE"),
            {"alpha": 9178, "beta": 0},
        )

    def test_missing_and_invalid_counts_do_not_create_negative_load(self):
        values = [None, "bad", -10, "12"]
        submissions = [{"user": "alpha", "pool_node": i} for i in range(5)]
        batches = {i: {"counts": {"IDLE": value}} for i, value in enumerate(values)}
        batches[4] = {"counts": {}}
        snapshot = {"payload": {"CLAS12OCR": {"results": [
            {"user": "alpha", "idle": value} for value in values
        ] + [{"user": "alpha"}]}}}
        self.assertEqual(compute_condor_jobs_by_user(submissions, batches, "IDLE"), {"alpha": 12})
        self.assertEqual(compute_condor_jobs_from_snapshot(snapshot, "CLAS12OCR", "IDLE"), {"alpha": 12})


class InterleavedPriorityTests(unittest.TestCase):
    def queue(self, rows, running=None, idle=None, burst=2):
        return compute_priorities(
            rows=rows,
            algorithm="aging_interleaved",
            time_format=TIME_FORMAT,
            half_life_days=3.0,
            queue_penalty_exponent=2.0,
            history_half_life_days=5.0,
            burst_per_user=burst,
            running_jobs_by_user=running,
            idle_jobs_by_user=idle,
        )[1]

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

    def test_recalculation_preserves_every_users_turn_over_multiple_rounds(self):
        now = datetime.now().replace(microsecond=0)
        rows = [pending_row(user, index * 10 + i, now - timedelta(days=2))
                for index, user in enumerate(("alpha", "beta", "carman")) for i in range(6)]
        running = {"alpha": 0, "beta": 71, "carman": 347}
        served = []
        for i in range(len(rows)):
            queue = self.queue(rows, running)
            self.assertEqual([row["priority"] for row in queue], list(range(1, len(queue) + 1)))
            selected = next(row for row in rows if row["user_submission_id"] == queue[0]["user_submission_id"])
            served.append(selected["user"])
            selected["run_status"] = SUBMITTED
            selected["server_time"] = format_time(now + timedelta(seconds=i))
        self.assertEqual(served, ["alpha", "alpha", "beta", "beta", "carman", "carman"] * 3)
        self.assertEqual(self.queue(rows, running), [])

    def test_a_partially_served_user_keeps_only_their_remaining_allowance(self):
        now = datetime.now().replace(microsecond=0)
        rows = [pending_row(user, index * 10 + i, now - timedelta(days=2))
                for index, user in enumerate(("alpha", "beta", "carman")) for i in range(4)]
        for number, row in enumerate((rows[0], rows[4], rows[5])):
            row.update(run_status=SUBMITTED, server_time=format_time(now + timedelta(seconds=number)))
        queue = self.queue(rows, {"alpha": 0, "beta": 71, "carman": 347})
        self.assertEqual([row["user"] for row in queue[:3]], ["alpha", "carman", "carman"])

    def test_idle_work_counts_for_every_algorithm(self):
        now = datetime.now().replace(microsecond=0)
        rows = [pending_row("storyf", 1, now - timedelta(days=1)),
                pending_row("carman", 2, now - timedelta(days=1))]
        for algorithm in ("inverse_count", "aging", "aging_interleaved"):
            with self.subTest(algorithm=algorithm):
                _, queue, _, _ = compute_priorities(
                    rows, algorithm, TIME_FORMAT, 3.0, 2.0, 5.0,
                    running_jobs_by_user={"storyf": 0, "carman": 347},
                    idle_jobs_by_user={"storyf": 30000, "carman": 0},
                )
                self.assertEqual([row["user"] for row in queue], ["carman", "storyf"])
                self.assertEqual(queue[1]["outstanding_jobs_for_user"], 30000)

    def test_carman_advances_with_supplied_october_20_history(self):
        pending = [
            ("carman", 12067, "2026-10-13 07:03:53"),
            ("carman", 12068, "2026-10-13 07:04:28"),
            ("matthewn", 12052, "2026-10-12 05:53:25"),
            ("borozdin", 12100, "2026-10-18 15:10:13"),
            ("storyf", 12115, "2026-10-18 19:44:38"),
            ("lanza", 12118, "2026-10-19 03:45:53"),
            ("asliacar", 11912, "2026-09-18 07:16:34"),
            ("ishige", 12019, "2026-10-06 20:46:50"),
            ("aosmond", 12038, "2026-10-09 11:22:06"),
            ("mkerr", 12047, "2026-10-09 13:02:33"),
        ]
        served = [
            ("carman", 11997, "2026-10-03 14:15:00"),
            ("matthewn", 12050, "2026-10-14 20:27:00"),
            ("matthewn", 12051, "2026-10-14 23:45:00"),
            ("borozdin", 12098, "2026-10-18 16:33:00"),
            ("borozdin", 12099, "2026-10-19 21:51:00"),
            ("storyf", 12112, "2026-10-18 21:34:00"),
            ("storyf", 12113, "2026-10-19 15:51:00"),
            ("storyf", 12114, "2026-10-20 05:57:00"),
            ("asliacar", 11909, "2026-10-15 13:09:00"),
            ("asliacar", 11910, "2026-10-16 08:57:00"),
            ("asliacar", 11911, "2026-10-17 21:03:00"),
            ("ishige", 11937, "2026-10-12 19:09:00"),
            ("ishige", 12017, "2026-10-14 14:21:00"),
            ("ishige", 12018, "2026-10-15 04:15:00"),
            ("aosmond", 12034, "2026-10-16 20:27:00"),
            ("aosmond", 12035, "2026-10-17 05:33:00"),
            ("aosmond", 12036, "2026-10-18 02:57:00"),
            ("mkerr", 12042, "2026-10-13 11:21:00"),
            ("mkerr", 12044, "2026-10-18 07:21:00"),
            ("mkerr", 12045, "2026-10-18 12:51:00"),
            ("mkerr", 12046, "2026-10-18 14:39:00"),
        ]
        rows = [pending_row(user, number, datetime.strptime(time, TIME_FORMAT))
                for user, number, time in pending]
        rows += [dict(user=user, user_submission_id=number, client_time=time,
                      server_time=time, run_status=SUBMITTED) for user, number, time in served]
        with patch("db_io.priority_submissions.datetime") as clock:
            clock.now.return_value = datetime(2026, 10, 20, 6)
            clock.strptime.side_effect = datetime.strptime
            queue = self.queue(
                rows,
                {"carman": 347, "matthewn": 71, "borozdin": 220, "storyf": 0, "lanza": 334,
                 "asliacar": 890, "ishige": 1011, "aosmond": 1414, "mkerr": 1061},
                {"carman": 0, "matthewn": 0, "borozdin": 16409, "storyf": 30000, "lanza": 1305,
                 "asliacar": 6838, "ishige": 6692, "aosmond": 8735, "mkerr": 9777},
            )
        self.assertEqual([row["user_submission_id"] for row in queue[:3]], [12067, 12068, 12118])

    def test_new_work_does_not_inherit_service_from_before_it_was_queued(self):
        now = datetime.now().replace(microsecond=0)
        rows = [pending_row("alpha", 1, now - timedelta(days=2)),
                pending_row("beta", 2, now - timedelta(hours=1))]
        for number, time in enumerate((now - timedelta(hours=2), now - timedelta(minutes=30)), 10):
            rows.append(dict(user="beta", user_submission_id=number, client_time=format_time(time),
                             server_time=format_time(time), run_status=SUBMITTED))
        rows.append(dict(user="alpha", user_submission_id=20, server_time="invalid", run_status=SUBMITTED))
        rows.append(dict(user="alpha", user_submission_id=21, server_time=None, run_status=SUBMITTED))
        self.assertEqual(get_round_service_counts(rows, TIME_FORMAT, 2), {"beta": 1})

    def test_exhausted_users_and_single_user_queues_do_not_block(self):
        now = datetime.now().replace(microsecond=0)
        rows = [pending_row("alpha", i, now - timedelta(days=1)) for i in range(5)]
        for row in rows[:2]:
            row.update(run_status=SUBMITTED, server_time=format_time(now))
        self.assertEqual([row["user_submission_id"] for row in self.queue(rows)], [2, 3, 4])
        rows.append(pending_row("beta", 10, now - timedelta(days=1)))
        self.assertEqual(self.queue(rows, {"alpha": 0, "beta": 100})[0]["user"], "beta")

    def test_diagnostics_include_running_idle_and_total_load(self):
        now = datetime.now().replace(microsecond=0)
        rows = [pending_row("alpha", 1, now - timedelta(days=1))]
        queue = self.queue(rows, {"alpha": 3}, {"alpha": 7})
        output = StringIO()
        with redirect_stdout(output):
            print_summary(rows, {"alpha": 0}, {"alpha": 1}, {"alpha": 3}, idle_jobs_by_user={"alpha": 7})
        self.assertIn("idle_jobs", output.getvalue())
        self.assertIn("outstanding_jobs", output.getvalue())
        with TemporaryDirectory() as directory:
            path = Path(directory) / "priorities.json"
            write_priority_json(path, queue, rows, "aging_interleaved", 3, 5, None,
                                {"alpha": 0}, {"alpha": 1}, {"alpha": 3}, idle_jobs_by_user={"alpha": 7})
            payload = json.loads(path.read_text())
        self.assertEqual(payload["jobs_per_user"][0]["idle_jobs"], 7)
        self.assertEqual(payload["jobs_per_user"][0]["outstanding_jobs"], 10)
        self.assertEqual(payload["priorities"][0]["idle_jobs_for_user"], 7)
        self.assertEqual(payload["priorities"][0]["outstanding_jobs_for_user"], 10)


if __name__ == "__main__":
    unittest.main()
