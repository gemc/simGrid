"""Offline checks for the portal's rolling hourly completion totals."""

import json
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from condor_io import list_owner_submission as submissions


class TimelineCompletionTests(unittest.TestCase):
    latest = int(datetime(2026, 11, 2, 14, 46, 20, tzinfo=timezone.utc).timestamp())

    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.timeline = Path(self.directory.name) / "timeline.json"

    def samples(self):
        return [
            {"update_ts": self.latest - age * 3600, "global": {"done": age + 1}}
            for age in reversed(range(241))
        ]

    def collect(self, rows):
        self.timeline.write_text(json.dumps(rows))
        return submissions.collect_completions_per_day(self.timeline)

    def test_ten_full_intervals_end_at_latest_sample_and_ignore_old_history(self):
        days = self.collect(self.samples())

        self.assertEqual(len(days), 10)
        self.assertEqual(days[-1], {
            "date": "2026-11-02",
            "start": "2026-11-01T14:46:20+00:00",
            "end": "2026-11-02T14:46:20+00:00",
            "completed_jobs": sum(range(1, 25)),
        })
        self.assertEqual(days[0]["completed_jobs"], sum(range(217, 241)))
        for older, newer in zip(days, days[1:]):
            self.assertEqual(older["end"], newer["start"])
        for day in days:
            duration = datetime.fromisoformat(day["end"]) - datetime.fromisoformat(day["start"])
            self.assertEqual(duration.total_seconds(), 86400)

    def test_jitter_does_not_add_a_25th_sample_or_drop_a_boundary_sample(self):
        rows = self.samples()
        for row in rows[:-1]:
            row["update_ts"] += 2 if row["global"]["done"] % 2 else -2
        self.assertEqual(self.collect(rows), self.collect(self.samples()))

    def test_unsorted_duplicate_hour_uses_newest_sample(self):
        rows = self.samples()
        rows.append({"update_ts": self.latest - 3600 - 5, "global": {"done": 9999}})
        self.assertEqual(self.collect(list(reversed(rows))), self.collect(self.samples()))

    def test_missing_hour_is_unknown_and_does_not_inflate_neighboring_days(self):
        rows = [row for row in self.samples() if row["update_ts"] != self.latest - 3600]
        days = self.collect(rows)
        self.assertIsNone(days[-1]["completed_jobs"])
        self.assertEqual(days[-2]["completed_jobs"], sum(range(25, 49)))

    def test_missing_done_is_unknown_but_zero_is_valid(self):
        rows = self.samples()
        rows[-1]["global"] = {}
        self.assertIsNone(self.collect(rows)[-1]["completed_jobs"])
        rows[-1]["global"]["done"] = 0
        self.assertEqual(self.collect(rows)[-1]["completed_jobs"], sum(range(2, 25)))

    def test_empty_or_unreadable_timeline_omits_summary(self):
        self.assertEqual(self.collect([]), [])
        self.timeline.write_text("[{invalid")
        with patch("sys.stderr") as stderr:
            self.assertEqual(submissions.collect_completions_per_day(self.timeline), [])
            self.assertTrue(stderr.write.called)
        with patch("sys.stderr"):
            self.assertEqual(submissions.collect_completions_per_day(self.timeline.with_suffix(".missing")), [])

    def test_cli_passes_custom_timeline_to_snapshot_builder(self):
        selected = submissions.empty_db_payload("CLAS12OCR", "gemc", "2026-11-02 10:00:00")
        argv = ["list_owner_submission.py", "--store-db", "--timeline-file", str(self.timeline)]
        with patch.object(submissions, "Database"), \
                patch.object(submissions, "collect_for_database", return_value=selected) as collect, \
                patch("sys.argv", argv):
            self.assertEqual(submissions.main(), 0)
            self.assertEqual(collect.call_args.kwargs["timeline_file"], self.timeline)

    def test_snapshot_rate_uses_latest_timeline_interval_without_condor_history(self):
        full = self.samples()
        missing_hour = full[:-2] + full[-1:]
        zero = [{"update_ts": row["update_ts"], "global": {"done": 0}} for row in full]
        condor = SimpleNamespace(get_owner_batches=MagicMock(return_value={}))
        database = MagicMock()
        database.__enter__.return_value = database
        database.query.return_value = []
        for rows, expected in [(full, 300), (missing_hour, None), ([], None), (zero, 0)]:
            with self.subTest(expected=expected, samples=len(rows)):
                self.timeline.write_text(json.dumps(rows))
                with patch.dict("sys.modules", {"htcondor_utils": condor}), \
                        patch.object(submissions, "Database", return_value=database):
                    payload = submissions.collect_for_database("gemc", "unused", "CLAS12OCR", self.timeline)
                self.assertEqual(payload["average_completions_per_day"], expected)
                if payload["completions_per_day"]:
                    self.assertEqual(payload["completions_per_day"][-1]["completed_jobs"], expected)

    def test_from_db_exports_stored_summary_without_reading_timeline(self):
        database = MagicMock()
        database.__enter__.return_value = database
        database.export_latest_owner_submission_payload.return_value = {"CLAS12OCR": {"results": []}}
        with patch.object(submissions, "Database", return_value=database), \
                patch.object(submissions, "collect_completions_per_day") as collect, \
                patch("sys.argv", ["list_owner_submission.py", "--from-db", "-q"]):
            self.assertEqual(submissions.main(), 0)
        collect.assert_not_called()
        database.export_latest_owner_submission_payload.assert_called_once_with(
            database_name="CLAS12OCR", owner="gemc"
        )


if __name__ == "__main__":
    unittest.main()
