<!DOCTYPE html>
<html lang="english">
<?php require_once __DIR__ . '/head.php'; ?>
<body onload='osgLogtoTable();'>
<?php require_once __DIR__ . '/header.php'; ?>


<div class="w3-padding w3-center">
	<h2 class="w3-xlarge" style="text-align:center">Summary of current jobs</h2>
	<div id="osgLog_summary"></div>
	<br/><br/>
</div>

<div class="w3-row-padding w3-center w3-margin-top">

	<h2 class="w3-xlarge" style="text-align:center">Click to submit to OSG</h2>
	<a>
		<div class="w3-quarter">
			<div class="w3-card w3-container" style="min-height:230px">
				<br/><br/>
				<br/><br/>
			</div>
		</div>
	</a>

	<a href="type1.php">
		<div class="w3-quarter">
			<div class="w3-card w3-container" style="min-height:210px">
				<h3>Generator<br/></h3><br/>
				<i class="w3-margin-bottom w3-text-theme" style="font-size:120px; "></i>
				<p style="text-align: left; font-weight: normal;">
					- clas12-mcgen or gemc internal generator <br/>
					- Arbitrary number of jobs <br/>
					- Arbitrary number of events per job (max 10,000) <br/>
				</p>
			</div>
		</div>
	</a>

	<a href="type2.php">
		<div class="w3-quarter">
			<div class="w3-card w3-container" style="min-height:210px">
				<h3>LUND Files<br/></h3><br/>
				<i class="w3-margin-bottom w3-text-theme" style="font-size:120px"></i>
				<p style="text-align: left; font-weight: normal;">
					- LUND files (.txt) from a web location <br/>
					- One job per LUND file <br/>
					- File define number of events per job (max 10,000) <br/>
				</p>
			</div>
		</div>
	</a>

	<a>
		<div class="w3-quarter">
			<div class="w3-card w3-container" style="min-height:230px">
				<br/><br/>
				<br/><br/>
			</div>
		</div>
	</a>
	<br/><br/>
	<br/><br/>

</div>

<div class="w3-padding w3-center">
	<br/><br/>
	<h2 class="w3-xlarge" style="text-align:center">Details of current OSG Jobs</h2>
	<div id="osgLog"></div>
	<br/><br/>
</div>

</body>
<script src="main.js"></script>
</html>
