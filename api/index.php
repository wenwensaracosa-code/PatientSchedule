<?php
// Enable output buffering so session_start() and header() never fail with headers already sent
if (ob_get_level() === 0) {
    ob_start();
}
// ========================================================
// Vercel Serverless Function - Central Application Router
// Routes requests to root and subfolder PHP files/static assets
// ========================================================

$rootDir = realpath(__DIR__ . '/..');
$requestUri = $_SERVER['REQUEST_URI'] ?? '/';
$parsedUrl = parse_url($requestUri);
$rawPath = $parsedUrl['path'] ?? '/';
$path = rawurldecode($rawPath);

// Standardize home / landing route
if ($path === '/' || $path === '/index.html') {
    $indexHtml = $rootDir . DIRECTORY_SEPARATOR . 'index.html';
    if (file_exists($indexHtml)) {
        header('Content-Type: text/html; charset=UTF-8');
        readfile($indexHtml);
        exit;
    }
}

// Remove leading slash for path matching
$relPath = ltrim($path, '/\\');

// Target resolution candidate
$target = null;

// Check directory indices
if ($relPath === 'admin' || $relPath === 'admin/') {
    $target = $rootDir . DIRECTORY_SEPARATOR . 'admin' . DIRECTORY_SEPARATOR . 'index.php';
} elseif ($relPath === 'doctor' || $relPath === 'doctor/') {
    $target = $rootDir . DIRECTORY_SEPARATOR . 'doctor' . DIRECTORY_SEPARATOR . 'index.php';
} elseif ($relPath === 'patient' || $relPath === 'patient/') {
    $target = $rootDir . DIRECTORY_SEPARATOR . 'patient' . DIRECTORY_SEPARATOR . 'index.php';
} else {
    $candidate = $rootDir . DIRECTORY_SEPARATOR . str_replace('/', DIRECTORY_SEPARATOR, $relPath);
    if (is_file($candidate)) {
        $target = $candidate;
    } elseif (is_file($candidate . '.php')) {
        $target = $candidate . '.php';
    } elseif (is_dir($candidate) && is_file($candidate . DIRECTORY_SEPARATOR . 'index.php')) {
        $target = $candidate . DIRECTORY_SEPARATOR . 'index.php';
    }
}

// If no file found, return 404
if (!$target || !file_exists($target)) {
    http_response_code(404);
    header('Content-Type: text/html; charset=UTF-8');
    echo "<!DOCTYPE html><html><head><title>404 Not Found</title></head><body><h1>404 Not Found</h1><p>The requested page was not found: " . htmlspecialchars($path) . "</p></body></html>";
    exit;
}

// Security: Prevent path traversal outside rootDir
$realTarget = realpath($target);
if (!$realTarget || strpos($realTarget, $rootDir) !== 0) {
    http_response_code(403);
    echo "Forbidden";
    exit;
}

$ext = strtolower(pathinfo($realTarget, PATHINFO_EXTENSION));

// Serve static assets if routed through PHP
$mimeTypes = [
    'css'   => 'text/css',
    'js'    => 'application/javascript',
    'png'   => 'image/png',
    'jpg'   => 'image/jpeg',
    'jpeg'  => 'image/jpeg',
    'gif'   => 'image/gif',
    'svg'   => 'image/svg+xml',
    'ico'   => 'image/x-icon',
    'html'  => 'text/html; charset=UTF-8',
    'htm'   => 'text/html; charset=UTF-8',
    'woff'  => 'font/woff',
    'woff2' => 'font/woff2',
    'ttf'   => 'font/ttf',
    'json'  => 'application/json',
];

if ($ext !== 'php' && isset($mimeTypes[$ext])) {
    header('Content-Type: ' . $mimeTypes[$ext]);
    readfile($realTarget);
    exit;
}

// Execute PHP script
if ($ext === 'php') {
    // Switch working directory to target script's folder so relative includes work
    chdir(dirname($realTarget));

    // Update server variables to reflect current script
    $_SERVER['SCRIPT_FILENAME'] = $realTarget;
    $scriptRelative = '/' . ltrim(str_replace('\\', '/', substr($realTarget, strlen($rootDir))), '/');
    $_SERVER['SCRIPT_NAME'] = $scriptRelative;
    $_SERVER['PHP_SELF'] = $scriptRelative;

    require $realTarget;
    exit;
}

// Fallback for unrecognized file types
http_response_code(404);
echo "Not Found";
