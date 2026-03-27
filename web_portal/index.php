<!DOCTYPE html>
<html lang="en">
<?php require_once __DIR__ . '/head.php'; ?>
<body onload="osgLogtoTable();">
<?php require_once __DIR__ . '/header.php'; ?>

<section class="page-section page-section--center">
	<h2 class="section-title">Summary of current jobs</h2>
	<div id="osgLog_summary"></div>
</section>

<section class="page-section page-section--center">
	<h2 class="section-title">Click to submit to OSG</h2>

	<div class="card-grid">
		<div class="card-grid__item">
			<div class="card card--empty"></div>
		</div>

		<a class="card-grid__item card-link" href="type1.php">
			<div class="card card--submit">
				<h3>Generator</h3>
				<div class="card-icon"></div>
				<p class="card-text">
					- clas12-mcgen or gemc internal generator <br/>
					- Arbitrary number of jobs <br/>
					- Arbitrary number of events per job (max 10,000) <br/>
				</p>
			</div>
		</a>

		<a class="card-grid__item card-link" href="type2.php">
			<div class="card card--submit">
				<h3>LUND Files</h3>
				<div class="card-icon"></div>
				<p class="card-text">
					- LUND files (.txt) from a web location <br/>
					- One job per LUND file <br/>
					- File define number of events per job (max 10,000) <br/>
				</p>
			</div>
		</a>

		<div class="card-grid__item">
			<div class="card card--empty"></div>
		</div>
	</div>
</section>

<section class="page-section page-section--center">
	<h2 class="section-title">Details of current OSG Jobs</h2>
	<div id="osgLog"></div>
</section>

<script src="main.js"></script>
</body>
</html>