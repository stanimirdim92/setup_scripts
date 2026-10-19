<?php

declare(strict_types=1);

namespace Acme\Controller;

use Acme\App;
use Acme\DuplicateChecker;
use Acme\Http;
use Acme\Places\Place;
use Acme\Places\PlacesUnavailable;

final class PlacesController
{
    public function __construct(private readonly App $app)
    {
    }

    /** GET /api/places/search?q= */
    public function search(): void
    {
        $query = trim((string) ($_GET['q'] ?? ''));
        if (mb_strlen($query) < 2) {
            Http::error('query_too_short', 422);
            return;
        }
        try {
            $places = $this->app->places()->search($query);
        } catch (PlacesUnavailable) {
            Http::error('places_unavailable', 502);
            return;
        }
        $checker = new DuplicateChecker($this->app->businesses()->all());
        $results = array_map(
            static fn (Place $place): array => $place->toArray() + ['existing' => $checker->find($place)],
            $places,
        );
        Http::json(['query' => $query, 'results' => $results]);
    }
}
