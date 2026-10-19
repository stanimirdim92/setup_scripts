<?php /** @var string $title @var string $content */ use Acme\Http; ?>
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title><?= Http::e($title) ?> · Acme Leads</title>
    <link rel="stylesheet" href="/assets/app.css">
</head>
<body>
<header class="topbar">
    <span class="brand">Acme Leads</span>
</header>
<main class="page">
<?= $content ?>
</main>
<script src="/assets/app.js" defer></script>
</body>
</html>
