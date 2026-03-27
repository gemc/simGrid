<!DOCTYPE html>
<html lang="en">
<?php require_once __DIR__ . '/head.php'; ?>
<body onload="configurationSelected(); fieldSelected(); bkmergingSelected(); vertexSelected();">
<?php require_once __DIR__ . '/header.php'; ?>

<section class="page-section page-section--center">
	<form action="submit_type2.php" method="POST">
		<table id="submission_table" style="width: 70%; margin: 0 auto; text-align: center;">
			<tr>
				<td>
					<div class="tooltip">Configuration<span class="tooltiptext">Choose an experiment configuration</span></div>
				</td>
				<td>
					<select name="configuration" id="configuration" required
							onchange="fieldSelected(); bkmergingSelected(); vertexSelected(); softwareVersionSelected();">
					</select>
				</td>
			</tr>
			<tr>
				<td>
					<div class="tooltip">Versions (see <a target="_blank" href="https://github.com/JeffersonLab/clas12-config#readme">README)</a><span class="tooltiptext">Choose a gemc/coatjava versions pair for the selected experiment</span>
					</div>
				</td>
				<td>
					<select name="softwarev" id="softwarev" required
							onchange="fieldSelected(); bkmergingSelected(); vertexSelected();">
					</select>
				</td>
			</tr>
			<tr>
				<td>
					<div class="tooltip">Magnetic Fields <span class="tooltiptext">Choose one of the fields setup for the selected experiment</span></div>
				</td>
				<td>
					<select name="fields" id="fields" required onchange="bkmergingSelected()"></select>
				</td>
			</tr>
			<tr>
				<td>
					<div class="tooltip">Vertex <span class="tooltiptext">Choose how to modify the vertex</span></div>
				</td>
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
				<td>
					<div class="tooltip">LUND File(s) <b>Volatile</b> Location<span class="tooltiptext">
						Directory on /volatile/clas12 location containing lund files with extensions: .txt or .dat</span></div>
				</td>
				<td><input type="text" name="lundFiles" required></td>
			</tr>
			<tr>
				<td>Example:</td>
				<td><pre>/volatile/clas12/ungaro/lund/</pre></td>
			</tr>
			<tr>
				<td>
					<div class="tooltip">Background Merging
						<span class="tooltiptext">Choose values to merge background from random trigger. Select magnetic fields at second row first. No merging is selected by default.</span></div>
				</td>
				<td>
					<select name="bkmerging" id="bkmerging" required></select>
				</td>
			</tr>
			<tr>
				<td>
					<div class="tooltip">String Identifier (optional)
						<span class="tooltiptext">Output filename will be:<br>STRINGID-LUNDFILENAME-OSGID-JOBINDEX.hipo</span></div>
				</td>
				<td>
					<input type="text" id="user_string" name="user_string" value="" size="20" onkeydown="return /[aA-zZ0-9-]/i.test(event.key)">
				</td>
			</tr>
			<tr>
				<td style="border-left-color: white; border-bottom-color: white;"></td>
				<td>
					<input type="submit" value="Submit"><br><br>
					The submission will launch one job per LUND file.
				</td>
			</tr>
		</table>
	</form>
</section>

<script src="main.js"></script>        <!-- Don't move this line to the top! It causes an error at Safari -->
</body>
</html>