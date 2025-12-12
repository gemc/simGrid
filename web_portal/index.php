<!DOCTYPE html>
<html>
	<head>
		<title>CLAS12 Monte-Carlo Simulations OSG Portal</title>
		<meta charset="UTF-8"/>
		<meta name="viewport" content="width=device-width, initial-scale=1"/>
		<link rel="stylesheet" href="https://www.w3schools.com/w3css/4/w3.css"/>
		<link rel="stylesheet" href="https://www.w3schools.com/lib/w3-theme-black.css"/>
		<link rel="stylesheet" href="https://fonts.googleapis.com/css?family=Raleway"/>
		<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css"/>
		<link rel="stylesheet" href="main.css"/>
	</head>
	
	<body onload='osgLogtoTable();'>
		<header class="w3-panel w3-container" id="myHeader">
			<ul id="nav">
				<li><a href="index.php">     <h3><b>Home</b></h3></a></li>
				<li><a href="about.html">    About</a></li>
<!--				<li><a href="disk.php">      Disk Usage</a></li>-->
				<li><a href="osgStats.html"> OSG Stats</a></li>
				<li><a href="monitor.html">  Monitors</a></li>
			</ul>

			<div class="w3-center">
				<h1 id="title" class="w3-xlarge w3-opacity"></h1>
				<h2 class="w3-xlarge" style="text-align:right">Logged in as <img width = "160" src="username.php"/></h2>
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
						- In-Container or gemc internal generator <br/>
						- Arbitrary number of jobs <br/>
						- Arbitrary number of events for each job (max 10,000) <br/>
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
			<!--					<div id="farmStats"></div>-->
			<br/><br/>
			<h2 class="w3-xlarge" style="text-align:center">Details of current OSG Jobs</h2>
			<div id="osgLog"></div>
			<br/><br/>
		</div>

	</body>

	<script src="main.js"></script>		<!-- Don't move this line to the top! It causes an error at Safari -->

</html>
