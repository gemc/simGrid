<!DOCTYPE html>
<html lang="en">
<?php require_once __DIR__ . '/head.php'; ?>
<body>
<?php require_once __DIR__ . '/header.php'; ?>

<main class="page-section">
	<section class="content-block">
		<h2 class="section-title">OSG Monitoring</h2>

		<div class="iframe-card">
			<iframe
				class="dashboard-frame"
				title="OSG Monitoring Dashboard"
				src="https://gracc.opensciencegrid.org/d/000000080/vo-summary?orgId=1&from=now-7d&to=now&var-interval=$__auto_interval_interval&var-vo=All&var-type=Payload&var-Filter=ProjectName%7C%3D%7CCLAS12">
			</iframe>
		</div>
	</section>
</main>

<script src="main.js"></script>
</body>
</html>