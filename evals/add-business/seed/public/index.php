<?php

declare(strict_types=1);

// Front controller. bin/serve passes every request through here.

$path = (string) parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH);
if (PHP_SAPI === 'cli-server' && $path !== '/' && is_file(__DIR__ . $path)) {
    return false; // let the built-in server send static files
}

require __DIR__ . '/../src/bootstrap.php';

use Acme\App;
use Acme\Controller\BusinessController;
use Acme\Router;

$app = App::fromEnv();
$businesses = new BusinessController($app);

$router = new Router();
$router->get('/', static function (): void {
    header('Location: /businesses', true, 302);
});
$router->get('/businesses', $businesses->index(...));
$router->get('/api/businesses', $businesses->apiIndex(...));

$router->dispatch($_SERVER['REQUEST_METHOD'] ?? 'GET', $path);
