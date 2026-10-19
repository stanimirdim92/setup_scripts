<?php

declare(strict_types=1);

namespace Acme\Places;

/**
 * Reads places from a JSON file. The default client: deterministic, no network.
 * search() matches the whole query against the name, like the vendor's basic text search.
 */
final class FixturePlacesClient implements PlacesClient
{
    public function __construct(
        private readonly string $file,
        private readonly bool $fail = false,
    ) {
    }

    public function search(string $query): array
    {
        $needle = mb_strtolower(trim($query));
        return array_values(array_filter(
            $this->all(),
            static fn (Place $place): bool => $needle !== '' && str_contains(mb_strtolower($place->name), $needle),
        ));
    }

    public function details(string $placeId): ?Place
    {
        foreach ($this->all() as $place) {
            if ($place->placeId === $placeId) {
                return $place;
            }
        }
        return null;
    }

    /** @return list<Place> */
    private function all(): array
    {
        if ($this->fail) {
            throw new PlacesUnavailable('Fixture places client is set to fail (ACME_PLACES_FAIL=1)');
        }
        $data = json_decode((string) file_get_contents($this->file), true, flags: JSON_THROW_ON_ERROR);
        return array_map(Place::fromArray(...), $data);
    }
}
