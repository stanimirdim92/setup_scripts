<?php

declare(strict_types=1);

namespace Acme\Places;

/**
 * Reads places from a JSON file. The default client: deterministic, no network.
 * search() is multi-token: each token of the query must be found in the name,
 * street, ZIP, city or category.
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
        $tokens = preg_split('/[\s,]+/u', mb_strtolower(trim($query)), flags: PREG_SPLIT_NO_EMPTY);
        if ($tokens === []) {
            return [];
        }
        return array_values(array_filter(
            $this->all(),
            static function (Place $place) use ($tokens): bool {
                $fields = array_map(
                    static fn (?string $value): string => mb_strtolower((string) $value),
                    [$place->name, $place->street, $place->zip, $place->city, $place->category],
                );
                foreach ($tokens as $token) {
                    $found = false;
                    foreach ($fields as $field) {
                        if (str_contains($field, $token)) {
                            $found = true;
                            break;
                        }
                    }
                    if (!$found) {
                        return false;
                    }
                }
                return true;
            },
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
