<!DOCTYPE html>
<html lang="en">
<?php require_once __DIR__ . '/head.php'; ?>
<body onload="configurationSelected(); fieldSelected(); bkmergingSelected(); update_mcgen_versions(); vertexSelected();">
<?php require_once __DIR__ . '/header.php'; ?>

<section class="page-section page-section--center">
	<h2 class="section-title">Submit to OSG: Generator</h2>
</section>

<section class="page-section page-section--center">
	<form action="submit_type1.php" method="POST">
		<table id="submission_table" class="submission-table">
			<tr>
				<td>Configuration</td>
				<td>
					<select name="configuration" id="configuration" required
							onchange="fieldSelected(); bkmergingSelected(); vertexSelected(); softwareVersionSelected();">
					</select>
				</td>
			</tr>
			<tr>
				<td><a target="_blank" href="https://github.com/JeffersonLab/clas12-config#readme">Software Versions</a></td>
				<td>
					<select name="softwarev" id="softwarev" required
							onchange="fieldSelected(); bkmergingSelected(); vertexSelected();">
					</select>
				</td>
			</tr>
			<tr>
				<td><a target="_blank" href="https://github.com/JeffersonLab/clas12-mcgen#readme">MC Gen Versions</a>
					<br>Consider <a href="about.html#gen-test">testing the generators</a> before submission.
				</td>
				<td>
					<select name="mcgenv" id="mcgenv" required>
					</select>
				</td>
			</tr>
			<tr>
				<td>Magnetic Fields</td>
				<td>
					<select name="fields" id="fields" required onchange="bkmergingSelected()"></select>
				</td>
			</tr>
			<tr>
				<td>Vertex</td>
				<td style="text-align: left;">
					<div class="checkbox-container">
						<input type="checkbox" id="zposition-check" checked onchange="vertexSelected();"/>
						<label for="zposition-check">z: adjust for target position and semi-length</label>
						<input type="text" id="zposition-show" name="zposition-show" value="" readonly size="20">
					</div>

					<div class="checkbox-container">
						<input type="checkbox" id="beamspot-check" checked onchange="vertexSelected();"/>
						<label for="beamspot-check">x/y: smear beamspot</label>
						<input type="text" id="beamspot-show" name="beamspot-show" value="" readonly size="50">
					</div>

					<div class="checkbox-container">
						<input type="checkbox" id="raster-check" checked onchange="vertexSelected();"/>
						<label for="raster-check">x/y: raster</label>
						<input type="text" id="raster-show" name="raster-show" value="" readonly size="20">
					</div>

					<div>
						<fieldset id="vertex_user_selection" name="vertex_user_selection" style="border: 0; text-align: center;">
							<input type="radio" id="ignore" name="vuser_selection" value="0" checked>
							<label for="ignore">Ignore Generator Vertex</label>

							<input type="radio" id="relative" name="vuser_selection" value="1">
							<label for="relative">Relative to Generator Vertex</label>
						</fieldset>
					</div>
				</td>
			</tr>
			<tr>
				<td>Generator</td>
				<td>
					<select name="generator" id="generator" required onchange="genSelected(this)">
						<option selected hidden value=""></option>
						<option value="clas12-elSpectro"> clas12-elSpectro</option>
						<option value="clasdis"> clasdis</option>
						<option value="claspyth"> claspyth</option>
						<option value="deep-pipi-gen"> deep-pipi-gen</option>
						<option value="dvcsgen"> dvcsgen</option>
						<option value="genKYandOnePion"> genKYandOnePion</option>
						<option value="inclusive-dis-rad"> inclusive-dis-rad</option>
						<option value="JPsiGen"> JPsiGen</option>
						<option value="MCEGENpiN_radcorr"> MCEGENpiN_radcorr</option>
						<option value="TCSGen"> TCSGen</option>
						<option value="twopeg"> twopeg</option>
						<option value="genepi"> genepi</option>
						<option value="onepigen"> onepigen</option>
						<option value="gibuu"> gibuu</option>
						<option value="clas-stringspinner"> clas-stringspinner</option>
						<option value="gemc"> gemc</option>
					</select>
				</td>
			</tr>
			<tr>
				<td>Generator Options</td>
				<td>
					<input type="text" name="genOptions" id="genOptions" style="min-width: 200px;">
					<div id="generatorLink">
						<a href="#" target="_blank"></a>
					</div>
				</td>
			</tr>
			<tr>
				<td colspan="2">
					Once you have chosen the generator, review the linked documentation and insert the desired options above.<br/>
					Note: Do not utilize the following options, as they are automatically included: <br/><br/>
					<code>--docker, output file name, --trig</code>.
				</td>
			</tr>
			<tr>
				<td>Number of Events per Job</td>
				<td><input type="number" name="nevents" id="box2" oninput="calculate();" min="1" max="5000" required></td>
			</tr>
			<tr>
				<td>Number of Jobs</td>
				<td><input type="number" name="jobs" id="box1" oninput="calculate();" min="0" max="10000" required></td>
			</tr>
			<tr>
				<td>Total Number of Events</td>
				<td><input type="number" name="totalevents" id="result" readonly> M</td>
			</tr>
			<tr>
				<td>Background Merging</td>
				<td>
					<select name="bkmerging" id="bkmerging" required></select>
				</td>
			</tr>
			<tr>
				<td>String Identifier (optional)</td>
				<td>
					<input type="text" id="user_string" name="user_string" value="" size="20" onkeydown="return /[aA-zZ0-9-]/i.test(event.key)">
				</td>
			</tr>
			<tr>
				<td>Output Type</td>
				<td>
					<div>
						<fieldset id="sim_output_type" name="sim_output_type" style="border: 0; text-align: center;">
							<input type="radio" id="dst" name="output_type" value="0" checked>
							<label for="dst">DST</label>

							<input type="radio" id="gemc" name="output_type" value="1">
							<label for="gemc">GEMC Only</label>
						</fieldset>
					</div>
				</td>
			</tr>
			<tr>
				<td></td>
				<td><input type="submit" value="Submit"></td>
			</tr>
		</table>
	</form>
</section>

<script src="main.js"></script>
</body>
</html>