<?php

declare(strict_types=1);

namespace Acme;

/** Method + path routing. "{id}" in a pattern matches digits and is passed to the handler. */
final class Router
{
    /** @var list<array{string, string, callable}> */
    private array $routes = [];

    public function get(string $pattern, callable $handler): void
    {
        $this->routes[] = ['GET', $pattern, $handler];
    }

    public function post(string $pattern, callable $handler): void
    {
        $this->routes[] = ['POST', $pattern, $handler];
    }

    public function dispatch(string $method, string $path): void
    {
        foreach ($this->routes as [$routeMethod, $pattern, $handler]) {
            $regex = '#^' . str_replace('\{id\}', '(\d+)', preg_quote($pattern, '#')) . '$#';
            if ($routeMethod === $method && preg_match($regex, $path, $m)) {
                $handler(...array_map('intval', array_slice($m, 1)));
                return;
            }
        }
        if (str_starts_with($path, '/api/')) {
            Http::error('not_found', 404);
            return;
        }
        Http::html('<h1>Not found</h1>', 404);
    }
}
