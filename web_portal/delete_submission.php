<?php
require_once __DIR__ . '/submission_api.php';
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
	header('Allow: POST');
	submissionReply(['error' => 'Use POST to delete a submission.'], 405);
}
$token = $_POST['csrf_token'] ?? '';
if (!is_string($token) || !hash_equals($submissionCsrf, $token)) {
	submissionReply(['error' => 'Invalid request token. Reload the submission details.'], 403);
}
submissionReply(submissionAction('delete', is_string($_POST['id'] ?? null) ? $_POST['id'] : ''));
