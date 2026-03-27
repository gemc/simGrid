<?php
$currentPage = basename($_SERVER['SCRIPT_NAME']);

function navLink(string $file, string $label, string $currentPage): string
{
	$text = ($currentPage === $file)
		? '<h3><b>' . htmlspecialchars($label, ENT_QUOTES, 'UTF-8') . '</b></h3>'
		: htmlspecialchars($label, ENT_QUOTES, 'UTF-8');

	return '<li><a href="' . htmlspecialchars($file, ENT_QUOTES, 'UTF-8') . '">' . $text . '</a></li>';
}
?>

<header class="w3-panel w3-container" id="myHeader">
	<ul id="nav">
		<?php
		echo navLink('index.php',     'Home',      $currentPage);
		echo navLink('about.php',     'About',     $currentPage);
		echo navLink('osgStats.php',  'OSG Stats', $currentPage);
		echo navLink('monitor.php',   'Monitors',  $currentPage);
		echo navLink('fairshare.php', 'Fairshare', $currentPage);
		?>
	</ul>

	<div class="w3-center">
		<h1 id="title" class="w3-xlarge w3-opacity"></h1>
		<?php $user = $_SERVER['REMOTE_USER'] ?? 'no auth user'; ?>
		<h4><i>Logged in as <?php echo htmlspecialchars($user, ENT_QUOTES, 'UTF-8'); ?></i></h4>
	</div>
</header>