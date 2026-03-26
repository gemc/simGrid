<?php
header('Content-Type: application/json; charset=UTF-8');

$response = [
	'requested_id' => $_GET['id'] ?? null
];

if (!isset($_GET['id']) || !preg_match('/^\d+$/', $_GET['id'])) {
	$response['error'] = 'Invalid or missing job id.';
	echo json_encode($response, JSON_PRETTY_PRINT);
	exit;
}

$id = $_GET['id'];
$defaultsFile = realpath(__DIR__ . '../../../../msql_conn.txt');

if ($defaultsFile === false || !is_readable($defaultsFile)) {
	$response['error'] = 'Cannot read MySQL defaults file.';
	echo json_encode($response, JSON_PRETTY_PRINT);
	exit;
}

$sql = "use CLAS12OCR; select user, scard from submissions where user_submission_id=$id;";
$cmd = 'mysql --defaults-extra-file=' . escapeshellarg($defaultsFile) . ' -Bse ' . escapeshellarg($sql) . ' 2>&1';

$output = shell_exec($cmd);

if ($output === null) {
	$response['error'] = 'Command execution failed.';
	echo json_encode($response, JSON_PRETTY_PRINT);
	exit;
}

$output = trim($output);

if ($output === '') {
	$response['error'] = 'No submission found for this job id.';
	echo json_encode($response, JSON_PRETTY_PRINT);
	exit;
}

/*
 Expected first split:
   user<TAB>scard

 Sometimes scard itself contains tabs/newlines, so split only once.
*/
$rowParts = explode("\t", $output, 2);
$response['user'] = $rowParts[0] ?? '';
$scard = $rowParts[1] ?? '';

$scard = str_replace(["\\n", "\r\n", "\r"], ["\n", "\n", "\n"], $scard);
$response['raw_scard'] = $scard;

/*
 Sample scard often starts like:
   2026-02-27 15:34:49<TAB>10517<TAB>Not Submitted<TAB>project: ...
*/
$scardParts = explode("\t", $scard);

if (count($scardParts) >= 1) {
	$response['submitted_at'] = trim($scardParts[0]);
}
if (count($scardParts) >= 2) {
	$response['user_submission_id'] = trim($scardParts[1]);
}
if (count($scardParts) >= 3) {
	$response['status'] = trim($scardParts[2]);
}

$detailsBlob = '';
if (count($scardParts) >= 4) {
	$detailsBlob = implode("\t", array_slice($scardParts, 3));
}

$detailsBlob = trim($detailsBlob);
$details = [];

if ($detailsBlob !== '') {
	$lines = preg_split('/\n+/', $detailsBlob);

	foreach ($lines as $line) {
		$line = trim($line);
		if ($line === '') continue;

		if (strpos($line, ':') !== false) {
			list($key, $value) = explode(':', $line, 2);
			$details[] = [
				'key' => trim($key),
				'value' => trim($value)
			];
		} else {
			$details[] = [
				'key' => 'info',
				'value' => $line
			];
		}
	}
}

$response['details'] = $details;

echo json_encode($response, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES);