<!DOCTYPE html>
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

	<body>
		<header class="w3-panel w3-opacity w3-container" id="myHeader">
			<ul id="nav">
				<li><a href="index.php">     Home</a></li>
				<li><a href="about.html">    About</a></li>
				<li><a href="osgStats.html"> OSG Stats</a></li>
				<li><a href="fairshare.html"> Fairshare</a></li>
			</ul>

			<div class="w3-center">
				<h1 id="title" class="w3-xlarge w3-opacity"></h1>
				<?php $user = $_SERVER['REMOTE_USER'] ?? 'no auth user'; ?>
				<h4><i>Logged in as <?php echo htmlspecialchars($user, ENT_QUOTES, 'UTF-8'); ?></i></h4>
				<br/><br/>
			</div>
		</header>

		<div class="w3-center">
			
			<?php
				require_once __DIR__ . '/common.php';

				$project       = 'CLAS12';
				$configuration = $_POST['configuration'];
				$softwarev     = $_POST['softwarev'];
				$lundFiles     = $_POST['lundFiles'];
				$username      = $_SERVER['REMOTE_USER'];
				$client_ip     = $_SERVER['REMOTE_ADDR'];
				$fields		   = $_POST['fields'];
				$bkmerging     = $_POST['bkmerging'];
    			$zposition     = $_POST['zposition-show'];
				$raster        = $_POST['raster-show'];
				$beam          = $_POST['beamspot-show'];
				$vertex_choice = $_POST['vuser_selection'];
				$string_id     = $_POST['user_string'];
				$output_type   = $_POST['output_type'];
				$uri		   = $_SERVER['REQUEST_URI'];
				$timestamp     = date('Y-m-d_H-i-s');
				$scard_file    = '/var/www/gemc-runtime/scard_type2_' . preg_replace('/[^A-Za-z0-9_.-]/', '_', $username) . '_' . $timestamp . '.txt';
				$command = $submit_script;

				function yesorno($cond){
					$val = "no";
					if($cond) $val="yes";
					return $val;
				}

				if (
					!empty($project) &&
					!empty($configuration) &&
					!empty($softwarev) &&
					!empty($lundFiles) &&
					!empty($fields) &&
					!empty($bkmerging)
				) {

					$fp = fopen($scard_file, 'w');

					fwrite($fp, 'project:  '.$project.PHP_EOL);
					fwrite($fp, 'configuration: '.$configuration.PHP_EOL);
					fwrite($fp, 'softwarev: '.$softwarev.PHP_EOL);
					fwrite($fp, 'generator: '.$lundFiles.PHP_EOL);
					fwrite($fp, 'client_ip: '.$client_ip.PHP_EOL);
					fwrite($fp, 'dstOUT: yes'.PHP_EOL);
					fwrite($fp, 'fields: '.$fields.PHP_EOL);
					fwrite($fp, 'bkmerging: '.$bkmerging.PHP_EOL);
					fwrite($fp, 'zposition: '.$zposition.PHP_EOL);
					fwrite($fp, 'raster: '.$raster.PHP_EOL);
					fwrite($fp, 'beam: '.$beam.PHP_EOL);
					fwrite($fp, 'vertex_choice: '.$vertex_choice.PHP_EOL);
					fwrite($fp, 'string_id: '.$string_id.PHP_EOL);
					fwrite($fp, 'output_type: '.$output_type.PHP_EOL);
					if ($IS_DEVEL_MODE) {
						fwrite($fp, 'submission: devel'.PHP_EOL);
    					$command .= ' --database CLAS12TEST';
					} else {
						fwrite($fp, 'submission: production'.PHP_EOL);
					}
					fclose($fp);
					$command .= ' -u ' . escapeshellarg($username)
							 . ' ' . escapeshellarg($scard_file);
					$output = shell_exec($command);
				}
				else {
					echo "All field are required";
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
					<td>Software Versions</td>
					<td><?php echo($softwarev); ?></td>
				</tr>
				<tr>
					<td>Magnetic Fields</td>
					<td><?php echo($fields); ?></td>
				</tr>
				<tr>
					<td>Lund File Location</td>
					<td> <?php echo($lundFiles); ?> </td>
				</tr>
					<td> Target Position and Length </td>
					<td><?php echo($zposition); ?></td>
                </tr>
                <tr>
                    <td> Beamspot </td>
                    <td><?php echo($beam); ?></td>
                </tr>                <tr>
                    <td> Raster </td>
                    <td><?php echo($raster); ?></td>
                </tr>

                <tr>
                    <td> User Choice: <br/> 0=ignore generator vertex <br/> 1=relative to generator vertex  </td>
                    <td><?php echo($vertex_choice); ?></td>
                </tr>
				<tr>
					<td> Background Merging </td>
					<td> <?php echo($bkmerging); ?> M</td>
				</tr>
				<tr>
					<td> Output Type </td>
					<td> <?php echo($output_type); ?></td>
				</tr>
				<tr>
                    <td> String Identifier: </td>
                    <td><?php echo($string_id); ?></td>
                </tr>
			</table>
			<h4>Output is synced hourly at /volatile/clas12/osg/<?php echo($username); ?>.</h4>
		</div>
	</body>

	<script src="main.js"></script>		<!-- Don't move this line to the top! It causes an error at Safari -->

</html>
