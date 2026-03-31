<!DOCTYPE html>
<html lang="en">
<?php require_once __DIR__ . '/head.php'; ?>
<body onload="configurationSelected(); fieldSelected(); bkmergingSelected(); vertexSelected();">
<?php require_once __DIR__ . '/header.php'; ?>

<section class="page-section page-section--center">
	<h2 class="section-title">Submit to OSG: LUND Files</h2>
</section>

<section class="page-section page-section--center">
	<form action="submit_type2.php" method="POST">
		<table id="submission_table" class="submission-table" >
			<tr>
				<td>Configuration</td>
				<td>
					<select name="configuration" id="configuration" required
							onchange="fieldSelected(); bkmergingSelected(); vertexSelected(); softwareVersionSelected();">
					</select>
				</td>
			</tr>
			<tr>
				<td>Versions (see <a target="_blank" href="https://github.com/JeffersonLab/clas12-config#readme">README)</a></td>
				<td>
					<select name="softwarev" id="softwarev" required
							onchange="fieldSelected(); bkmergingSelected(); vertexSelected();">
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
				<td>LUND File(s) <b>Volatile</b> Location</td>
				<td><input type="text" name="lundFiles" required></td>
			</tr>
			<tr>
				<td>Example</td>
				<td><pre>/volatile/clas12/ungaro/lund/</pre></td>
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
				<td></td>
				<td>
					<input type="submit" value="Submit"><br><br>
					The submission will launch one job per LUND file.
				</td>
			</tr>
		</table>
	</form>
</section>

<script src="main.js"></script>
</body>
</html>