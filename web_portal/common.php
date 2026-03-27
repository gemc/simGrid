<?php
$REQUEST_URI = $_SERVER['REQUEST_URI'] ?? '';

$IS_MAIN_MODE  = strpos($REQUEST_URI, 'main/web_portal') !== false;
$IS_DEVEL_MODE = strpos($REQUEST_URI, 'dev/web_portal') !== false;

$submit_script = '../db_io/upload_submission.py';

$portalTitle = $IS_DEVEL_MODE
	? 'CLAS12 Monte-Carlo TEST Submission Portal'
	: 'CLAS12 Monte-Carlo Job Submission Portal';