"""Tests for marking submissions that disappeared from the main-page snapshot."""

import unittest

from db_io.mark_completed_submissions import (
    CANDIDATE_LIMIT,
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
        return len(params) - 2


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

    def test_update_is_guarded_by_current_submitted_status(self):
        db = FakeDatabase()
        candidates = [{"user_submission_id": 102}, {"user_submission_id": "104"}]

        self.assertEqual(mark_completed(db, candidates), 2)
        sql, params = db.updates[0]
        self.assertIn("WHERE run_status = %s", sql)
        self.assertEqual(params, [COMPLETED, SUBMITTED, 102, 104])

    def test_no_candidates_skips_update(self):
        db = FakeDatabase()

        self.assertEqual(mark_completed(db, []), 0)
        self.assertEqual(db.updates, [])


if __name__ == "__main__":
    unittest.main()
