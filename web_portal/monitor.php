<!DOCTYPE html>
<html lang="en">
<?php require_once __DIR__ . '/head.php'; ?>
<body>
<?php require_once __DIR__ . '/header.php'; ?>

<div class="pdf-container" style="text-align: center;">
	<table style="margin: 0 auto;">
		<tr>
			<td colspan="2">OSG Daily Summary</td>
		</tr>

		<tr>
			<td>
				<a href="https://clasweb.jlab.org/clas12offline/osg/daily-digest/latest.pdf" target="_blank"> Latest </a>

			</td>
			<td>
				<a href="https://clasweb.jlab.org/clas12offline/osg/daily-digest/latest-logscale.pdf" target="_blank"> Latest Logscale </a>
			</td>
		</tr>
		<tr>
			<td colspan="2">
				<a href="https://clasweb.jlab.org/clas12offline/osg/daily-digest/?C=M;O=D">All Daily monitoring graphs</a>
			</td>
		</tr>
	</table>
</div>

<iframe style="position:page;   top: 50px; left:0; bottom:0; right:0; width:100%; height:1100px; border:none; margin:0; padding:50px; overflow:auto ;"
		src="https://clasweb.jlab.org/clas12offline/osg/">
</iframe>

</body>
<script src="main.js"></script>
</html>
