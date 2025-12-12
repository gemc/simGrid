<!DOCTYPE HTML>
<html>
	<head>
		<title>CLAS12 Monte-Carlo Job Submission Portal</title>
		<meta charset="UTF-8"/>
		<meta name="viewport" content="width=device-width, initial-scale=1"/>
		<link rel="stylesheet" href="https://www.w3schools.com/w3css/4/w3.css"/>
		<link rel="stylesheet" href="https://www.w3schools.com/lib/w3-theme-black.css"/>
		<link rel="stylesheet" href="https://fonts.googleapis.com/css?family=Raleway"/>
		<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css"/>
		<link rel="stylesheet" href="main.css"/>
	</head>
	
	<body onload='diskUsagetoTable();'>
		<header class="w3-panel w3-container" id="myHeader">
			<ul id="nav">
				<li><a href="index.php">     Home</a></li>
				<li><a href="about.html">    About</a></li>
				<li><a href="disk.php">      Disk Usage</a></li>
				<li><a href="osgStats.html"> OSG Stats</a></li>
			</ul>

			<div class="w3-center">
				<h1 id="title" class="w3-xlarge w3-opacity"></h1>
				<h2 class="w3-xlarge" style="text-align:right">Logged in as <img width = "160" src="username.php"/></h2>
				<br/><br/>
			</div>

			<div class="w3-padding w3-center">
				
				<div id="du"></div>
				<br>
				<br>
				
			</div>
			</header>
		
		
		
	</body>

	<script src="main.js"></script>		<!-- Don't move this line to the top! It causes an error at Safari -->
		
</html>
