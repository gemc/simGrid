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

	<body>
		<header class="w3-panel w3-opacity w3-container" id="myHeader">
			<ul id="nav">
				<li><a href="index.php">     Home</a></li>
				<li><a href="about.html">    About</a></li>
				<li><a href="disk.php">      Disk Usage</a></li>
				<li><a href="osgStats.html"> OSG Stats</a></li>
			</ul>

			<div class="w3-center">
				<h1 id="title" class="w3-xlarge w3-opacity"></h1>
				<h2 class="w3-xlarge" style="text-align:center">Logged in as <img width = "160" src="username.php"/></h2>
				<br/><br/>
			</div>
		</header>

		<div class="w3-center">

			<?php
				$project       = 'CLAS12';
				$configuration = $_POST['configuration'];
				$generator     = $_POST['generator'];
				$genOptions    = $_POST['genOptions'];
				$nevents       = $_POST['nevents'];
				$jobs          = $_POST['jobs'];
				$totalevents   = $_POST['totalevents'];
				$fields		   = $_POST['fields'];
				$bkmerging     = $_POST['bkmerging'];
            $username      = $_SERVER['PHP_AUTH_USER'];
				$client_ip     = $_SERVER['REMOTE_ADDR'];
				$uri		      = $_SERVER['REQUEST_URI'];
				$fname         = 'submissions/'.uniqid($username.'.type1.', true);

				if (!empty($project) && !empty($configuration) && !empty($fields)&& !empty($bkmerging) && !empty($generator) && !empty($nevents) && !empty($jobs) ) {
					$fp = fopen($fname, 'w');
					fwrite($fp, 'project: '.$project.PHP_EOL);
					fwrite($fp, 'connection: mysql'.PHP_EOL);
					fwrite($fp, 'type: 1'.PHP_EOL);
					fwrite($fp, 'username: '.$username.PHP_EOL);
					fwrite($fp, 'configuration: '.$configuration.PHP_EOL);
					fwrite($fp, 'generator: '.$generator.PHP_EOL);
					fwrite($fp, 'genOptions: '.$genOptions.PHP_EOL);
					fwrite($fp, 'nevents: '.$nevents.PHP_EOL);
					fwrite($fp, 'njobs: '.$jobs.PHP_EOL);
					fwrite($fp, 'client_ip: '.$client_ip.PHP_EOL);
					fwrite($fp, 'fields: '.$fields.PHP_EOL);
					fwrite($fp, 'bkmerging: '.$bkmerging.PHP_EOL);
					if (strpos($uri, 'test/clas12osg/webPortal') !== false) {
						fwrite($fp, 'version: test'.PHP_EOL);
					} else {
						fwrite($fp, 'version: production'.PHP_EOL);
					}
					fclose($fp);
					if (strpos($uri, 'test/clas12osg/webPortal') !== false) {
						$command = escapeshellcmd('../client/SubMit.py -t '.$fname);
						$output = shell_exec($command);
					} else {
						$command = escapeshellcmd('../client/SubMit.py '.$fname);
						$output = shell_exec($command);
					}
				}
				else {
					echo("<h2> All fields are required </h2>");
					die();
				}
			?>


			<h4>Your job was successfully submitted with the following parameters.</h4>
			<table style="text-align: center;width: 50%;"align="center">
				<tr>
					<td>Project</td>
					<td> <?php echo($project); ?> </td>
				</tr>
				<tr>
					<td>Configuration</td>
					<td><?php echo($configuration); ?></td>
				</tr>
				<tr>
					<td>Magnetic Fields</td>
					<td><?php echo($fields); ?></td>
				</tr>
				<tr>
					<td>Generator</td>
					<td> <?php echo($generator); ?> </td>
				</tr>
				<tr>
					<td>Generator Options</td>
					<td><?php echo($genOptions); ?></td>
				</tr>
				<tr>
					<td>Number of Events / Job</td>
					<td><?php echo($nevents); ?></td>
				</tr>
				<tr>
					<td>Number of Jobs</td>
					<td><?php echo($jobs); ?></td>
				</tr>
				<tr>
					<td> Total Number of Events </td>
					<td><?php echo($totalevents); ?> M</td>
				</tr>
				<tr>
					<td> Background Merging </td>
					<td> <?php echo($bkmerging); ?> M</td>
				</tr>
			</table>
			<h4>Output is synced hourly at /lustre/expphy/volatile/clas12/osg2/<?php echo($username); ?>.</h4>
		</div>
	</body>

	<script src="main.js"></script>		<!-- Don't move this line to the top! It causes an error at Safari -->

</html>
