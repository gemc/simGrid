<?php
require_once __DIR__ . '/common.php';

$portalTitle = $IS_DEVEL_MODE
	? 'CLAS12 Monte-Carlo TEST Submission Portal'
	: 'CLAS12 Monte-Carlo Job Submission Portal';
?>
<head>
	<title><?php echo htmlspecialchars($portalTitle, ENT_QUOTES, 'UTF-8'); ?></title>
	<meta charset="UTF-8"/>
	<meta name="viewport" content="width=device-width, initial-scale=1"/>
	<link rel="stylesheet" href="main.css"/>
</head>