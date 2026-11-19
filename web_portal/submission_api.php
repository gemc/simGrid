<?php
require_once __DIR__ . '/common.php';
header('Content-Type: application/json; charset=UTF-8');
header('Cache-Control: no-store');

function submissionReply(array $response, int $status = 200): void {
	http_response_code($status);
	echo json_encode($response, JSON_UNESCAPED_SLASHES);
	exit;
}

if (empty($_SERVER['REMOTE_USER'])) {
	submissionReply(['error' => 'Authentication is required.'], 401);
}

ini_set('session.use_strict_mode', '1');
if (!session_start([
	'cookie_httponly' => true,
	'cookie_secure' => !empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off',
	'cookie_samesite' => 'Lax'
])) {
	submissionReply(['error' => 'Unable to start a secure session.'], 500);
}
if (empty($_SESSION['submission_csrf'])) {
	$_SESSION['submission_csrf'] = bin2hex(random_bytes(32));
}
$submissionCsrf = $_SESSION['submission_csrf'];
session_write_close();

function submissionAction(string $action, string $id): array {
	global $IS_DEVEL_MODE;
	if (!preg_match('/^[0-9]+$/D', $id) || (int)$id <= 0) {
		submissionReply(['error' => 'Invalid or missing submission ID.'], 400);
	}
	$command = escapeshellarg(__DIR__ . '/../db_io/portal_submission.py');
	$process = proc_open($command, [0 => ['pipe', 'r'], 1 => ['pipe', 'w'], 2 => ['pipe', 'w']], $pipes);
	if (!is_resource($process)) {
		submissionReply(['error' => 'Unable to access submissions.'], 500);
	}
	fwrite($pipes[0], json_encode([
		'action' => $action,
		'id' => $id,
		'user' => $_SERVER['REMOTE_USER'],
		'database' => $IS_DEVEL_MODE ? 'CLAS12TEST' : 'CLAS12OCR'
	]));
	fclose($pipes[0]);
	$output = stream_get_contents($pipes[1]);
	fclose($pipes[1]);
	$errors = stream_get_contents($pipes[2]);
	fclose($pipes[2]);
	if ($errors !== '') {
		error_log($errors);
	}
	$exitCode = proc_close($process);
	$response = json_decode($output, true);
	if ($exitCode !== 0 || !is_array($response)) {
		submissionReply(['error' => 'Unable to access submissions. Please try again later.'], 500);
	}
	if (isset($response['error'])) {
		submissionReply(['error' => $response['error']], $response['http_status'] ?? 500);
	}
	return $response;
}
