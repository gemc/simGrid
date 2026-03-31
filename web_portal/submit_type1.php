<!DOCTYPE html>
<html lang="en">
<?php require_once __DIR__ . '/head.php'; ?>
<body>
<?php require_once __DIR__ . '/header.php'; ?>


<div class="w3-center">

	<?php
		require_once __DIR__ . '/common.php';

		$project       = 'CLAS12';
		$configuration = $_POST['configuration'];
		$softwarev     = $_POST['softwarev'];
		$mcgenv        = $_POST['mcgenv'];
		$generator     = $_POST['generator'];
		$genOptions    = $_POST['genOptions'];
		$nevents       = $_POST['nevents'];
		$jobs          = $_POST['jobs'];
		$totalevents   = $_POST['totalevents'];
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
		$scard_file    = '/var/www/gemc-runtime/scard_type1_' . preg_replace('/[^A-Za-z0-9_.-]/', '_', $username) . '_' . $timestamp . '.txt';
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
			!empty($mcgenv) &&
			!empty($generator) &&
			!empty($nevents) &&
			!empty($jobs) &&
			!empty($totalevents) &&
			!empty($fields) &&
			!empty($bkmerging)
		) {
			$fp = fopen($scard_file, 'w');

			fwrite($fp, 'project: '.$project.PHP_EOL);
			fwrite($fp, 'configuration: '.$configuration.PHP_EOL);
			fwrite($fp, 'softwarev: '.$softwarev.PHP_EOL);
			fwrite($fp, 'mcgenv: '.$mcgenv.PHP_EOL);
			fwrite($fp, 'generator: '.$generator.PHP_EOL);
			fwrite($fp, 'genOptions: '.$genOptions.PHP_EOL);
			fwrite($fp, 'nevents: '.$nevents.PHP_EOL);
			fwrite($fp, 'jobs: '.$jobs.PHP_EOL);
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
					 . ' -f ' . escapeshellarg($scard_file);

			$log_file = preg_replace('/\.txt$/', '.log', $scard_file);

			file_put_contents($log_file, "COMMAND: $command\n\n");

			$cmd_with_log = $command . ' >> ' . escapeshellarg($log_file) . ' 2>&1';

			$lines = [];
			$return_code = 0;
			exec($cmd_with_log, $lines, $return_code);

			$output = implode("\n", $lines);
			$submission_ok = ($return_code === 0);
	}
	else {
	echo("<h2> All fields are required </h2>");
	die();
	}

	?>

<?php if ($submission_ok): ?>
<h4 style="text-align: center;">Your job was successfully submitted with the following parameters.</h4>
<?php else: ?>
<h4>Submission failed.</h4>
<p>Please contact support and include this log file:</p>
<p><code><?php echo htmlspecialchars($log_file, ENT_QUOTES, 'UTF-8'); ?></code></p>
<?php endif; ?>

<?php if ($submission_ok): ?>
<table class="submission-table" style="width: 50%; margin: 0 auto; border-collapse: collapse;">
	<tr>
		<td style="width: 40%; text-align: center;">Project</td>
		<td style="text-align: left;"> <?php echo($project); ?> </td>
	</tr>
	<tr>
		<td style="width: 40%; text-align: center;">Configuration</td>
		<td style="text-align: left;"><?php echo($configuration); ?></td>
	</tr>
	<tr>
		<td style="width: 40%; text-align: center;">Software Versions</td>
		<td style="text-align: left;"><?php echo($softwarev); ?></td>
	</tr>
	<tr>
		<td style="width: 40%; text-align: center;">MC Gen Versions</td>
		<td style="text-align: left;"><?php echo($mcgenv); ?></td>
	</tr>
	<tr>
		<td style="width: 40%; text-align: center;">Magnetic Fields</td>
		<td style="text-align: left;"><?php echo($fields); ?></td>
	</tr>
	<tr>
		<td style="width: 40%; text-align: center;">Generator</td>
		<td style="text-align: left;"> <?php echo($generator); ?> </td>
	</tr>
	<tr>
		<td style="width: 40%; text-align: center;">Generator Options</td>
		<td style="text-align: left;"><?php echo($genOptions); ?></td>
	</tr>
	<tr>
		<td style="width: 40%; text-align: center;"> Target Position and Length</td>
		<td style="text-align: left;"><?php echo($zposition); ?></td>
	</tr>
	<tr>
		<td style="width: 40%; text-align: center;"> Beamspot</td>
		<td style="text-align: left;"><?php echo($beam); ?></td>
	</tr>
	<tr>
		<td style="width: 40%; text-align: center;"> Raster</td>
		<td style="text-align: left;"><?php echo($raster); ?></td>
	</tr>

	<tr>
		<td style="width: 40%; text-align: center;"> User Choice: <br/> 0=ignore generator vertex <br/> 1=relative to generator vertex</td>
		<td style="text-align: left;"><?php echo($vertex_choice); ?></td>
	</tr>
	<tr>
		<td style="width: 40%; text-align: center;">Number of Events per Job</td>
		<td style="text-align: left;"><?php echo($nevents); ?></td>
	</tr>
	<tr>
		<td style="width: 40%; text-align: center;">Number of Jobs</td>
		<td style="text-align: left;"><?php echo($jobs); ?></td>
	</tr>
	<tr>
		<td style="width: 40%; text-align: center;"> Total Number of Events</td>
		<td style="text-align: left;"><?php echo($totalevents); ?> M</td>
	</tr>
	<tr>
		<td style="width: 40%; text-align: center;"> Background Merging</td>
		<td style="text-align: left;"> <?php echo($bkmerging); ?></td>
	</tr>
	<tr>
		<td style="width: 40%; text-align: center;"> Output Type</td>
		<td style="text-align: left;"> <?php echo($output_type); ?></td>
	</tr>
	<tr>
		<td style="width: 40%; text-align: center;"> String Identifier:</td>
		<td style="text-align: left;"><?php echo($string_id); ?></td>
	</tr>
</table>
<h4 style="text-align: center;">Output will be at /volatile/clas12/osg/<?php echo($username); ?>.</h4>
<?php endif; ?>
</div>

</body>
<script src="main.js"></script>        <!-- Don't move this line to the top! It causes an error at Safari -->
</html>
