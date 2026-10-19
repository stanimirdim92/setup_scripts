<?php

declare(strict_types=1);

/** A fresh in-memory database with the schema and the seed rows. */
function test_db(): PDO
{
    $pdo = new PDO('sqlite::memory:', options: [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
    ]);
    $pdo->exec((string) file_get_contents(__DIR__ . '/../database/schema.sql'));
    $pdo->exec((string) file_get_contents(__DIR__ . '/../database/seed.sql'));
    return $pdo;
}

function fixture_places(bool $fail = false): Acme\Places\FixturePlacesClient
{
    return new Acme\Places\FixturePlacesClient(__DIR__ . '/../fixtures/places.json', $fail);
}

function assert_same(mixed $expected, mixed $actual, string $message = ''): void
{
    if ($expected !== $actual) {
        throw new RuntimeException(trim($message . ' expected ' . var_export($expected, true) . ', got ' . var_export($actual, true)));
    }
}

function assert_true(bool $condition, string $message = 'expected true'): void
{
    if (!$condition) {
        throw new RuntimeException($message);
    }
}

/** Runs $fn and requires it to throw $class. */
function assert_throws(string $class, callable $fn): void
{
    try {
        $fn();
    } catch (Throwable $e) {
        assert_true($e instanceof $class, 'expected ' . $class . ', got ' . get_class($e));
        return;
    }
    throw new RuntimeException('expected ' . $class . ', nothing was thrown');
}
