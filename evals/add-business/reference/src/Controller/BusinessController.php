<?php

declare(strict_types=1);

namespace Acme\Controller;

use Acme\App;
use Acme\DuplicateChecker;
use Acme\Http;
use Acme\Places\PlacesUnavailable;

final class BusinessController
{
    private const MAX_NOTES = 1000;

    public function __construct(private readonly App $app)
    {
    }

    /** GET /businesses */
    public function index(): void
    {
        $businesses = $this->app->businesses()->listAvailable();
        Http::html(Http::render('businesses', ['businesses' => $businesses], 'Businesses'));
    }

    /** GET /api/businesses */
    public function apiIndex(): void
    {
        Http::json(['businesses' => $this->app->businesses()->listAvailable()]);
    }

    /**
     * POST /api/businesses {"place_id": "...", "notes": "..."}
     * Creates the business as pending and opens its enrichment request.
     */
    public function create(): void
    {
        $body = Http::jsonBody();
        $placeId = is_string($body['place_id'] ?? null) ? trim($body['place_id']) : '';
        $notes = $body['notes'] ?? null;
        if ($placeId === '' || ($notes !== null && !is_string($notes)) || mb_strlen((string) $notes) > self::MAX_NOTES) {
            Http::error('invalid_request', 422);
            return;
        }
        $notes = trim((string) $notes) === '' ? null : trim((string) $notes);

        try {
            $place = $this->app->places()->details($placeId);
        } catch (PlacesUnavailable) {
            Http::error('places_unavailable', 502);
            return;
        }
        if ($place === null) {
            Http::error('place_not_found', 404);
            return;
        }

        $pdo = $this->app->pdo();
        $repository = $this->app->businesses();
        // IMMEDIATE takes the write lock first, so two requests cannot both pass the duplicate check.
        $pdo->exec('BEGIN IMMEDIATE');
        try {
            $existing = (new DuplicateChecker($repository->all()))->find($place);
            if ($existing !== null) {
                $pdo->exec('ROLLBACK');
                Http::error('duplicate', 409, ['existing' => $existing]);
                return;
            }
            $requestId = 'REQ-' . strtoupper(bin2hex(random_bytes(4)));
            $business = $repository->createPending($place, $notes, $requestId);
            $pdo->exec('COMMIT');
        } catch (\Throwable $e) {
            $pdo->exec('ROLLBACK');
            throw $e;
        }
        Http::json(['request_id' => $requestId, 'business' => $business], 201);
    }
}
