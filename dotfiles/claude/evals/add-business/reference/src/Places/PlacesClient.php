<?php

declare(strict_types=1);

namespace Acme\Places;

interface PlacesClient
{
    /**
     * @return list<Place>
     * @throws PlacesUnavailable when the places API cannot answer
     */
    public function search(string $query): array;

    /** @throws PlacesUnavailable when the places API cannot answer */
    public function details(string $placeId): ?Place;
}
