<?php
$REQUEST_URI = $_SERVER['REQUEST_URI'] ?? '';
$SCRIPT_NAME = $_SERVER['SCRIPT_NAME'] ?? '';
$PHP_SELF    = $_SERVER['PHP_SELF'] ?? '';
$DOC_ROOT    = $_SERVER['DOCUMENT_ROOT'] ?? '';

error_log('REQUEST_URI: ' . $REQUEST_URI);
error_log('SCRIPT_NAME: ' . $SCRIPT_NAME);
error_log('PHP_SELF: ' . $PHP_SELF);
error_log('DOCUMENT_ROOT: ' . $DOC_ROOT);

$IS_MAIN_MODE  = strpos($REQUEST_URI, 'main/web_portal') !== false;
$IS_DEVEL_MODE = strpos($REQUEST_URI, 'dev/web_portal') !== false;

$submit_script = '../db_io/upload_submission.py';

if (!$IS_MAIN_MODE && !$IS_DEVEL_MODE) {
	$IS_MAIN_MODE = true;
}