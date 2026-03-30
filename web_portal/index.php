<!DOCTYPE html>
<html lang="en">
<?php require_once __DIR__ . '/head.php'; ?>
<body onload="osgLogtoTable('<?php echo $IS_DEVEL_MODE ? 'devel' : 'production'; ?>');">
<?php require_once __DIR__ . '/header.php'; ?>

<section class="page-section page-section--center">
	<h2 class="section-title">
		Summary of current jobs <?php echo $IS_DEVEL_MODE ? '(devel)' : '(production)'; ?>
	</h2>
	<div id="osgLog_summary"></div>
</section>

<section class="page-section page-section--center">
	<h2 class="section-title">Submit to OSG:</h2>

	<div class="card-grid">

		<a class="card-grid__item card-link" href="type1.php">
			<div class="card card--submit">
				<h3>Generator</h3>
				<div class="card-icon">⚙️</div>
				<p class="card-text">
					- clas12-mcgen or gemc internal generator <br/>
					- Arbitrary number of jobs (max 10,000) <br/>
					- Arbitrary number of events per job (max 5,000) <br/>
				</p>
			</div>
		</a>

		<a class="card-grid__item card-link" href="type2.php">
			<div class="card card--submit">
				<h3>LUND Files</h3>
				<div class="card-icon">📂</div>
				<p class="card-text">
					- LUND files (.txt) from a web location <br/>
					- One job per LUND file <br/>
					- File define number of events per job (max 10,000) <br/>
				</p>
			</div>
		</a>
	</div>
</section>

<section class="page-section page-section--center">
	<h2 class="section-title">
		Details of current jobs <?php echo $IS_DEVEL_MODE ? '(devel)' : ''; ?>
	</h2>
	<div id="osgLog"></div>
</section>

<script src="main.js"></script>
</body>
</html>