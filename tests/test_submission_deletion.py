"""Deletion authorization, submission races, and submit-node retry behavior without services."""

import json
import subprocess
import unittest
from contextlib import nullcontext, redirect_stdout, redirect_stderr
from io import StringIO
from unittest.mock import Mock, patch

from condor_io.delete_jobs import process_deletions, remove_cluster
from db_io.portal_submission import handle_request, submission_details
from db_io.submission_deletion import cluster_id, request_deletion
from statuses import NOTSUBMITTED, PROCESSING, SUBMITTED, TODELETE


def submission(status=SUBMITTED, pool_node="1234"):
    return {
        "user_submission_id": 42, "user": "alice", "run_status": status, "pool_node": pool_node,
        "client_time": "2026-11-19 10:00:00", "scard": "project: CLAS12\njobs: 10\n",
    }


def database(row):
    db = Mock()
    db.pending_priority_lock.return_value = nullcontext()
    db.query_one.return_value = row
    db.execute.return_value = 1
    return db


class DeletionRequestTests(unittest.TestCase):
    def test_only_exact_authenticated_owner_can_delete(self):
        for username in ("", "bob", "Alice"):
            with self.subTest(username=username):
                db = database(submission())
                with self.assertRaises(PermissionError):
                    request_deletion(db, 42, username)
                db.execute.assert_not_called()

    def test_pending_row_deleted_and_priorities_compacted_under_claim_lock(self):
        for pool in (None, "NULL", ""):
            with self.subTest(pool=pool):
                db = database(submission(NOTSUBMITTED, pool))
                self.assertFalse(request_deletion(db, 42, "alice")["queued"])
                db.pending_priority_lock.assert_called_once()
                sql, params = db.execute.call_args.args
                self.assertTrue(sql.startswith("DELETE FROM submissions"))
                self.assertIn("pool_node <=> %s", sql)
                self.assertEqual(params, [42, "alice", NOTSUBMITTED, pool])
                db._compact_pending_priorities_locked.assert_called_once()

    def test_submitted_row_marked_for_cron_and_not_deleted(self):
        db = database(submission())
        self.assertTrue(request_deletion(db, 42, "alice")["queued"])
        sql, params = db.execute.call_args.args
        self.assertTrue(sql.startswith("UPDATE submissions"))
        self.assertEqual(params, [TODELETE, 42, "alice", SUBMITTED, "1234"])

    def test_processing_is_never_deleted_even_without_cluster_id(self):
        db = database(submission(PROCESSING, "NULL"))
        with self.assertRaisesRegex(RuntimeError, "being sent"):
            request_deletion(db, 42, "alice")
        db.execute.assert_not_called()

    def test_status_changed_before_write_is_reported(self):
        db = database(submission())
        db.execute.return_value = 0
        with self.assertRaisesRegex(RuntimeError, "changed"):
            request_deletion(db, 42, "alice")

    def test_repeated_request_is_idempotent(self):
        db = database(submission(TODELETE))
        self.assertTrue(request_deletion(db, 42, "alice")["queued"])
        db.execute.assert_not_called()

    def test_missing_row_is_reported(self):
        with self.assertRaises(LookupError):
            request_deletion(database(None), 42, "alice")

    def test_submitted_row_with_missing_cluster_is_retained(self):
        db = database(submission(SUBMITTED, "NULL"))
        with self.assertRaises(ValueError):
            request_deletion(db, 42, "alice")
        db.execute.assert_not_called()

    def test_popup_uses_live_status_and_ownership_for_plain_and_legacy_cards(self):
        for legacy in (False, True):
            row = submission(TODELETE)
            if legacy:
                row["scard"] = "2026-11-19 10:00:00\t42\tNot Submitted\t" + row["scard"]
            details = submission_details(row, "alice")
            self.assertEqual(details["status"], TODELETE)
            self.assertEqual(details["details"][0], {"key": "project", "value": "CLAS12"})
            self.assertFalse(details["can_delete"])
        self.assertTrue(submission_details(submission(), "alice")["can_delete"])
        self.assertFalse(submission_details(submission(), "bob")["can_delete"])

    def test_bridge_rejects_bad_ids_and_database_before_connecting(self):
        with patch("db_io.portal_submission.Database") as connection:
            for request in (
                {"id": "42 OR 1=1", "database": "CLAS12OCR", "user": "alice"},
                {"id": "42", "database": "mysql", "user": "alice"},
            ):
                with self.assertRaises(ValueError):
                    handle_request(request)
            connection.assert_not_called()


class CondorDeletionTests(unittest.TestCase):
    def setUp(self):
        self.output = StringIO()
        self.enterContext(redirect_stdout(self.output))
        self.enterContext(redirect_stderr(self.output))

    def test_only_positive_cluster_ids_are_accepted(self):
        for value in (None, "NULL", "0", "-1", "1.0", "123; condor_rm gemc", "１２３"):
            with self.assertRaises(ValueError):
                cluster_id(value)
        self.assertEqual(cluster_id("123"), 123)

    @patch("condor_io.delete_jobs.subprocess.run")
    def test_running_idle_and_held_jobs_are_removed_as_one_cluster(self, run):
        run.return_value.stdout = json.dumps([
            {"Owner": "gemc", "JobStatus": status} for status in (1, 2, 5)
        ])
        remove_cluster(1234)
        self.assertEqual(run.call_args_list[1].args[0], ["condor_rm", "1234"])

    @patch("condor_io.delete_jobs.subprocess.run")
    def test_empty_or_already_removed_cluster_is_successful(self, run):
        for ads in ([], [{"Owner": "gemc", "JobStatus": 3}]):
            run.reset_mock()
            run.return_value.stdout = json.dumps(ads)
            remove_cluster(1234)
            self.assertEqual(run.call_count, 1)

    @patch("condor_io.delete_jobs.subprocess.run")
    def test_wrong_condor_owner_is_rejected(self, run):
        run.return_value.stdout = '[{"Owner": "someone_else", "JobStatus": 2}]'
        with self.assertRaises(RuntimeError):
            remove_cluster(1234)
        self.assertEqual(run.call_count, 1)

    @patch("condor_io.delete_jobs.remove_cluster")
    def test_dry_run_never_queries_condor_or_changes_database(self, remove):
        db = database(submission(TODELETE))
        db.query.return_value = [submission(TODELETE)]
        self.assertEqual(process_deletions(db), 0)
        self.assertEqual(db.query.call_args.args[1], [TODELETE])
        remove.assert_not_called()
        db.execute.assert_not_called()

    @patch("condor_io.delete_jobs.remove_cluster")
    def test_database_row_deleted_only_after_successful_condor_removal(self, remove):
        db = database(submission(TODELETE))
        db.query.return_value = [submission(TODELETE)]
        db.execute.side_effect = lambda *args: 1 if remove.called else self.fail("Deleted too early")
        self.assertEqual(process_deletions(db, apply=True), 0)
        self.assertEqual(db.execute.call_args.args[1], [42, TODELETE, "1234"])

    @patch("condor_io.delete_jobs.subprocess.run")
    def test_query_and_removal_failures_preserve_row(self, run):
        for failing_command in ("condor_q", "condor_rm"):
            with self.subTest(command=failing_command):
                def execute(command, **kwargs):
                    if command[0] == failing_command:
                        raise subprocess.CalledProcessError(1, command)
                    return Mock(stdout='[{"Owner": "gemc", "JobStatus": 2}]')
                run.side_effect = execute
                db = database(submission(TODELETE))
                db.query.return_value = [submission(TODELETE)]
                self.assertEqual(process_deletions(db, apply=True), 1)
                db.execute.assert_not_called()

    @patch("condor_io.delete_jobs.subprocess.run")
    def test_invalid_condor_response_preserves_row(self, run):
        for response in ("", "not JSON", "{}", "[{}]"):
            run.return_value.stdout = response
            db = database(None)
            db.query.return_value = [submission(TODELETE)]
            self.assertEqual(process_deletions(db, apply=True), 1)
            db.execute.assert_not_called()

    @patch("condor_io.delete_jobs.remove_cluster")
    def test_database_failure_after_removal_is_reported_for_retry(self, remove):
        db = database(None)
        db.query.return_value = [submission(TODELETE)]
        db.execute.side_effect = RuntimeError("MySQL unavailable")
        self.assertEqual(process_deletions(db, apply=True), 1)
        remove.assert_called_once_with(1234)
        self.assertIn("retained for retry", self.output.getvalue())

    @patch("condor_io.delete_jobs.remove_cluster")
    def test_bad_cluster_does_not_prevent_processing_next_request(self, remove):
        db = database(None)
        db.query.return_value = [submission(TODELETE, "NULL"), submission(TODELETE)]
        self.assertEqual(process_deletions(db, apply=True), 1)
        remove.assert_called_once_with(1234)
        db.execute.assert_called_once()


if __name__ == "__main__":
    unittest.main()
