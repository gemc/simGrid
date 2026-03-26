<?php
$REQUEST_URI = $_SERVER['REQUEST_URI'] ?? '';

$IS_MAIN_MODE  = strpos($REQUEST_URI, 'main/web_portal') !== false;
$IS_DEVEL_MODE = strpos($REQUEST_URI, 'dev/web_portal') !== false;

$submit_script = '../db_io/upload_submission.py';


// fallback: default to production if neither matches
if (!$IS_MAIN_MODE && !$IS_DEVEL_MODE) {
    $IS_DEVEL_MODE = false;
}