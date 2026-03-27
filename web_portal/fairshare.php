<!DOCTYPE html>
<html lang="english">
<?php require_once __DIR__ . '/head.php'; ?>

<body onload="fairshareToTable();">
<header class="w3-panel w3-container" id="myHeader">
	<ul id="nav">
		<li><a href="index.php"> Home</a></li>
		<li><a href="about.html"> About</a></li>
		<li><a href="osgStats.html"> OSG Stats</a></li>
		<li><a href="monitor.html"> Monitors</a></li>
		<li><a href="fairshare.html"><h3><b>Fairshare</b></h3></a></li>
	</ul>

	<div class="w3-center">
		<h1 id="title" class="w3-xlarge w3-opacity"></h1>
		<?php $user = $_SERVER['REMOTE_USER'] ?? 'no auth user'; ?>
		<h4><i>Logged in as <?php echo htmlspecialchars($user, ENT_QUOTES, 'UTF-8'); ?></i></h4>
		<br/><br/>
	</div>

	<div class="w3-padding w3-center">
		<br/><br/>
		<h2 class="w3-xlarge" style="text-align:center">Fairshare Summary</h2>
		<div id="fairshare_summary"></div>
		<br/><br/>
	</div>
</header>

<div class="w3-padding w3-center">
	<br/><br/>
	<h2 class="w3-xlarge" style="text-align:center">Summary: jobs per user</h2>
	<div id="fairshare_user_summary"></div>
	<br/><br/>

	<h2 class="w3-xlarge" style="text-align:center">Pending Jobs Fairshare Priority</h2>
	<div id="fairshare"></div>
	<br/><br/>
</div>

</body>

<script src="main.js?v=3"></script>
</html>