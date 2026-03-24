<?php
	ini_set('display_errors', 1);
	ini_set('display_startup_errors', 1);
	error_reporting(E_ALL);

	header("Content-Type: image/png");

	// Create image
	$img = imagecreatetruecolor(400, 60);
	$background  = imagecolorallocate($img, 255, 255, 255);
	$text_colour = imagecolorallocate($img, 0, 0, 0);
	imagefilledrectangle($img, 0, 0, 400, 60, $background);

	// Use REMOTE_USER instead of PHP_AUTH_USER
	$user = isset($_SERVER['REMOTE_USER']) ? $_SERVER['REMOTE_USER'] : 'no auth user';

	// Full path to a real TTF file (adjust if needed)
	$font = '/usr/share/fonts/dejavu/DejaVuSans.ttf';

	// Simple safety check so we see *something* even if font is wrong
	if (!is_readable($font)) {
	    imagestring($img, 3, 10, 20, "Font not readable", $text_colour);
	} else {
    	imagettftext($img, 40, 0, 10, 45, $text_colour, $font, $user);
	}

	// Output PNG
	imagepng($img);
	imagedestroy($img);
?>
