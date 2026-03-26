<!DOCTYPE html>
<html>
<?php require_once __DIR__ . '/head.php'; ?>

	<body onload='osgLogtoTable();'>
		<header class="w3-panel w3-container" id="myHeader">
			<ul id="nav">
				<li><a href="index.php">     <h3><b>Home</b></h3></a></li>
				<li><a href="about.html">    About</a></li>
				<li><a href="osgStats.html"> OSG Stats</a></li>
				<li><a href="monitor.html">  Monitors</a></li>
				<li><a href="fairshare.html"> Fairshare</a></li>
			</ul>

			<div class="w3-center">
				<h1 id="title" class="w3-xlarge w3-opacity"></h1>
				<?php $user = $_SERVER['REMOTE_USER'] ?? 'no auth user'; ?>
				<h4><i>Logged in as <?php echo htmlspecialchars($user, ENT_QUOTES, 'UTF-8'); ?></i></h4>
				<br/><br/>
			</div>

			<div class="w3-padding w3-center">
				<!--					<div id="farmStats"></div>-->
				<br/><br/>
				<h2 class="w3-xlarge" style="text-align:center">Summary of current jobs</h2>
				<div id="osgLog_summary"></div>
				<br/><br/>
			</div>

		</header>


		<div class="w3-row-padding w3-center w3-margin-top">
			<!--		Notice: these two must be in different lines:-->
			<!--		<div class="w3-card w3-container" style="min-height:300px">-->
			<!--		</div>-->
			<h2 class="w3-xlarge" style="text-align:center">Click to submit to OSG</h2>
			<a>
				<div class="w3-quarter">
					<div class="w3-card w3-container" style="min-height:230px">
						<br/><br/>
						<br/><br/>
					</div>
				</div>
			</a>

			<a href="type1.html" >
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

			<a href="type2.html" >
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

	<script src="main.js?v=3"></script>

</html>
