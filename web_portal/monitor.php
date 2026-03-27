<!DOCTYPE html>
<html lang="en">
<?php require_once __DIR__ . '/head.php'; ?>
<body>
<?php require_once __DIR__ . '/header.php'; ?>

<main class="page-section">
	<section class="content-block">
		<h2 class="section-title">OSG Daily Summary</h2>

		<div class="iframe-card monitor-links-card">
			<table class="monitor-links-table">
				<tbody>
					<tr>
						<td>
							<a href="https://clasweb.jlab.org/clas12offline/osg/daily-digest/latest.pdf" target="_blank" rel="noopener noreferrer">
								Latest
							</a>
						</td>
						<td>
							<a href="https://clasweb.jlab.org/clas12offline/osg/daily-digest/latest-logscale.pdf" target="_blank" rel="noopener noreferrer">
								Latest Logscale
							</a>
						</td>
					</tr>
					<tr>
						<td colspan="2">
							<a href="https://clasweb.jlab.org/clas12offline/osg/daily-digest/?C=M;O=D" target="_blank" rel="noopener noreferrer">
								All Daily Monitoring Graphs
							</a>
						</td>
					</tr>
				</tbody>
			</table>
		</div>
	</section>

	<section class="content-block">
		<div class="iframe-card">
			<iframe
				class="dashboard-frame dashboard-frame--tall"
				title="OSG Monitor"
				src="https://clasweb.jlab.org/clas12offline/osg/">
			</iframe>
		</div>
	</section>
</main>

<script src="main.js"></script>
</body>
</html>