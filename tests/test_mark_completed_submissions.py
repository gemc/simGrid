"""Tests for marking submissions that disappeared from the main-page snapshot."""

import unittest

from db_io.mark_completed_submissions import (
    CANDIDATE_LIMIT,
    build_last_done_map,
    extract_visible_submission_ids,
    find_completion_candidates,
    get_recent_submitted_rows,
    mark_completed,
)
from statuses import COMPLETED, SUBMITTED


class FakeDatabase:
    """Record queries and updates without opening a database connection."""

    def __init__(self, query_result=None):
        self.query_result = query_result or []
        self.queries = []
        self.updates = []

    def query(self, sql, params):
        self.queries.append((sql, params))
        return self.query_result

    def execute(self, sql, params):
        self.updates.append((sql, params))
        return 1


class CompletedSubmissionTests(unittest.TestCase):
    def test_extracts_submission_ids_from_main_page_payload(self):
        payload = {
            "CLAS12OCR": {
                "results": [
                    {"user_submission_id": 101},
                    {"submission id": "102"},
                    {"user_submission_id": None},
                ]
            }
        }

        self.assertEqual(extract_visible_submission_ids(payload, "CLAS12OCR"), {101, 102})

    def test_rejects_snapshot_without_selected_database(self):
        with self.assertRaisesRegex(ValueError, "CLAS12OCR"):
            extract_visible_submission_ids({"CLAS12TEST": {"results": []}}, "CLAS12OCR")

    def test_selects_only_submitted_rows_missing_from_snapshot(self):
        rows = [
            {"user_submission_id": 103},
            {"user_submission_id": 102},
            {"user_submission_id": 101},
        ]

        candidates = find_completion_candidates(rows, {101, 103})

        self.assertEqual(candidates, [{"user_submission_id": 102}])

    def test_queries_only_the_newest_100_submitted_rows(self):
        rows = [{"user_submission_id": 123}]
        db = FakeDatabase(rows)

        self.assertEqual(get_recent_submitted_rows(db), rows)
        sql, params = db.queries[0]
        self.assertIn("ORDER BY user_submission_id DESC", sql)
        self.assertEqual(params, [SUBMITTED, CANDIDATE_LIMIT])
        self.assertEqual(CANDIDATE_LIMIT, 100)

    def test_update_records_done_and_is_guarded_by_submitted_status(self):
        db = FakeDatabase()
        candidates = [
            {"user_submission_id": 102, "done": 9500},
            {"user_submission_id": "104", "done": None},
        ]

        self.assertEqual(mark_completed(db, candidates), 2)
        self.assertEqual(len(db.updates), 2)
        sql, params = db.updates[0]
        self.assertIn("WHERE run_status = %s", sql)
        self.assertIn("completion_time = NOW()", sql)
        self.assertEqual(params, [COMPLETED, 9500, SUBMITTED, 102])
        self.assertEqual(db.updates[1][1], [COMPLETED, None, SUBMITTED, 104])

    def test_no_candidates_skips_update(self):
        db = FakeDatabase()

        self.assertEqual(mark_completed(db, []), 0)
        self.assertEqual(db.updates, [])

    def test_build_last_done_map_takes_most_recent_done(self):
        snapshots = [
            {"payload": {"CLAS12OCR": {"results": [{"user_submission_id": 201, "done": 500}]}}},
            {"payload": {"CLAS12OCR": {"results": [
                {"user_submission_id": 201, "done": 300},
                {"submission id": "202", "done": 42},
            ]}}},
        ]

        self.assertEqual(
            build_last_done_map(snapshots, "CLAS12OCR"),
            {201: 500, 202: 42},
        )


if __name__ == "__main__":
    unittest.main()
