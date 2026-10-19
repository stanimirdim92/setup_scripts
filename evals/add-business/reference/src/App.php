<?php

declare(strict_types=1);

namespace Acme;

use Acme\Places\CurlPlacesClient;
use Acme\Places\FixturePlacesClient;
use Acme\Places\PlacesClient;
use PDO;

/**
 * Builds the shared services from environment variables. One instance per request.
 *
 *   ACME_DB              SQLite file (default var/app.sqlite)
 *   ACME_PLACES          "fixture" (default) or "http"
 *   ACME_PLACES_FIXTURE  fixture file (default fixtures/places.json)
 *   ACME_PLACES_FAIL     "1" makes the fixture client fail every call
 *   ACME_PLACES_URL, ACME_PLACES_KEY   the real places API (http only)
 */
final class App
{
    private ?PDO $pdo = null;

    private function __construct(
        private readonly string $root,
        private readonly array $env,
    ) {
    }

    public static function fromEnv(): self
    {
        return new self(dirname(__DIR__), getenv());
    }

    public function root(): string
    {
        return $this->root;
    }

    public function dbPath(): string
    {
        return $this->env['ACME_DB'] ?? $this->root . '/var/app.sqlite';
    }

    public function pdo(): PDO
    {
        if ($this->pdo === null) {
            $path = $this->dbPath();
            if (!is_dir(dirname($path))) {
                mkdir(dirname($path), 0777, true);
            }
            $this->pdo = new PDO('sqlite:' . $path, options: [
                PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
                PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
            ]);
            $this->pdo->exec('PRAGMA busy_timeout = 5000');
        }
        return $this->pdo;
    }

    public function businesses(): BusinessRepository
    {
        return new BusinessRepository($this->pdo());
    }

    public function mailer(): Mailer
    {
        return new Mailer($this->pdo());
    }

    public function places(): PlacesClient
    {
        if (($this->env['ACME_PLACES'] ?? 'fixture') === 'http') {
            return new CurlPlacesClient(
                (string) ($this->env['ACME_PLACES_URL'] ?? ''),
                (string) ($this->env['ACME_PLACES_KEY'] ?? ''),
            );
        }
        return new FixturePlacesClient(
            $this->env['ACME_PLACES_FIXTURE'] ?? $this->root . '/fixtures/places.json',
            ($this->env['ACME_PLACES_FAIL'] ?? '') === '1',
        );
    }
}
