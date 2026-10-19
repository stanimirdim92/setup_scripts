<?php

declare(strict_types=1);

namespace Acme\Places;

/** One place as the places API returns it. */
final readonly class Place
{
    public function __construct(
        public string $placeId,
        public ?string $cid,
        public string $name,
        public ?string $street,
        public ?string $zip,
        public ?string $city,
        public ?string $category,
        public ?string $website,
        public ?string $phone,
        public ?string $mapsUrl,
    ) {
    }

    public static function fromArray(array $data): self
    {
        return new self(
            (string) $data['place_id'],
            $data['cid'] ?? null,
            (string) $data['name'],
            $data['street'] ?? null,
            $data['zip'] ?? null,
            $data['city'] ?? null,
            $data['category'] ?? null,
            $data['website'] ?? null,
            $data['phone'] ?? null,
            $data['maps_url'] ?? null,
        );
    }

    public function toArray(): array
    {
        return [
            'place_id' => $this->placeId,
            'cid' => $this->cid,
            'name' => $this->name,
            'street' => $this->street,
            'zip' => $this->zip,
            'city' => $this->city,
            'category' => $this->category,
            'website' => $this->website,
            'phone' => $this->phone,
            'maps_url' => $this->mapsUrl,
        ];
    }
}
