<?php
require_once __DIR__ . '/common.php';
$currentPage = basename($_SERVER['SCRIPT_NAME'] ?? '');

function navLink(string $file, string $label, string $currentPage): string
{
	$isActive = ($currentPage === $file);
	$class = $isActive ? 'nav-link is-active' : 'nav-link';

	return '<li class="nav-item"><a class="' . $class . '" href="' . htmlspecialchars($file, ENT_QUOTES, 'UTF-8') . '">' .
		htmlspecialchars($label, ENT_QUOTES, 'UTF-8') .
		'</a></li>';
}
?>

<header class="site-header" id="myHeader">
	<nav class="site-nav" aria-label="Primary">
		<ul id="nav" class="nav-list">
			<?php
			echo navLink('index.php',     'Home',      $currentPage);
			echo navLink('about.php',     'About',     $currentPage);
			echo navLink('osgStats.php',  'OSG Stats', $currentPage);
			echo navLink('monitor.php',   'Monitors',  $currentPage);
			echo navLink('fairshare.php', 'Fairshare', $currentPage);
			?>
		</ul>
	</nav>

	<div class="site-header__brand">
		<h1 id="title" class="site-title"><?php echo htmlspecialchars($portalTitle, ENT_QUOTES, 'UTF-8'); ?></h1>
		<?php $user = $_SERVER['REMOTE_USER'] ?? 'no auth user'; ?>
		<p class="site-user">Logged in as <?php echo htmlspecialchars($user, ENT_QUOTES, 'UTF-8'); ?></p>
	</div>
</header>