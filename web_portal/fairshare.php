<!DOCTYPE html>
<html lang="en">
<?php require_once __DIR__ . '/head.php'; ?>
<body onload="fairshareToTable();">
<?php require_once __DIR__ . '/header.php'; ?>

<main class="page-section">
	<section class="content-block page-section--center">
		<h2 class="section-title">Pending Jobs Fairshare Priority</h2>
		<div id="fairshare"></div>
	</section>

	<section class="content-block page-section--center">
		<h2 class="section-title">Summary: jobs per user</h2>
		<div id="fairshare_user_summary"></div>
	</section>

	<section class="content-block page-section--center">
		<h2 class="section-title">Fairshare Summary</h2>
		<div id="fairshare_summary"></div>
	</section>

</main>

<script src="main.js"></script>
</body>
</html>