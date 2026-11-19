<?php
require_once __DIR__ . '/submission_api.php';
if ($_SERVER['REQUEST_METHOD'] !== 'GET') {
	header('Allow: GET');
	submissionReply(['error' => 'Use GET for submission details.'], 405);
}
$response = submissionAction('details', is_string($_GET['id'] ?? null) ? $_GET['id'] : '');
if ($response['can_delete']) {
	$response['csrf_token'] = $submissionCsrf;
}
submissionReply($response);
