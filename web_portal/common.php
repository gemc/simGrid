<?php
$REQUEST_URI = $_SERVER['REQUEST_URI'] ?? '';

$IS_DEVEL_MODE = strpos($REQUEST_URI, 'dev/web_portal') !== false;
$IS_MAIN_MODE  = !$IS_DEVEL_MODE;

$submit_script = '../db_io/upload_submission.py';

$portalTitle = $IS_DEVEL_MODE
	? 'CLAS12 Monte-Carlo TEST OSG Portal'
	: 'CLAS12 Monte-Carlo OSG Portal';