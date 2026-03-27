<!DOCTYPE HTML>
<html>
<?php require_once __DIR__ . '/head.php'; ?>

<body>
<header class="w3-panel w3-container" id="myHeader">
	<ul id="nav">
		<li><a href="index.php"> Home</a></li>
		<li><a href="about.html"> About</a></li>
		<li><a href="osgStats.html"><h3><b>OSG Stats</b></h3></a></li>
		<li><a href="monitor.html"> Monitors</a></li>
		<li><a href="fairshare.html"> Fairshare</a></li>
	</ul>

	<div class="w3-center">
		<h1 id="title" class="w3-xlarge w3-opacity"></h1>
		<?php $user = $_SERVER['REMOTE_USER'] ?? 'no auth user'; ?>
		<h4><i>Logged in as <?php echo htmlspecialchars($user, ENT_QUOTES, 'UTF-8'); ?></i></h4>
		<br/><br/>
	</div>
</header>

<iframe style="position:fixed;  left:0; bottom:0; right:0; width:100%; height:80%; border:none; margin:0; padding:0; overflow:hidden; z-index:999999;"
		src="https://gracc.opensciencegrid.org/d/000000080/vo-summary?orgId=1&from=now-7d&to=now&var-interval=$__auto_interval_interval&var-vo=All&var-type=Payload&var-Filter=ProjectName%7C%3D%7CCLAS12">
</iframe>

</body>

<script src="main.js"></script>        <!-- Don't move this line to the top! It causes an error at Safari -->

</html>
