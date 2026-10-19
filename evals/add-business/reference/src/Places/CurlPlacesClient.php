<?php

declare(strict_types=1);

namespace Acme\Places;

/**
 * The real places API over HTTP. Selected with ACME_PLACES=http. Tests and local
 * development use FixturePlacesClient instead.
 *
 *   GET {base}/search?q=...   -> {"results": [Place, ...]}
 *   GET {base}/places/{id}    -> Place, or 404
 */
final class CurlPlacesClient implements PlacesClient
{
    public function __construct(
        private readonly string $baseUrl,
        private readonly string $apiKey,
        private readonly int $timeoutSeconds = 5,
    ) {
    }

    public function search(string $query): array
    {
        $data = $this->get('/search?' . http_build_query(['q' => $query]));
        return array_map(Place::fromArray(...), $data['results'] ?? []);
    }

    public function details(string $placeId): ?Place
    {
        $data = $this->get('/places/' . rawurlencode($placeId));
        return $data === null ? null : Place::fromArray($data);
    }

    private function get(string $path): ?array
    {
        $curl = curl_init(rtrim($this->baseUrl, '/') . $path);
        curl_setopt_array($curl, [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_TIMEOUT => $this->timeoutSeconds,
            CURLOPT_HTTPHEADER => ['Accept: application/json', 'Authorization: Bearer ' . $this->apiKey],
        ]);
        $body = curl_exec($curl);
        $status = curl_getinfo($curl, CURLINFO_RESPONSE_CODE);
        $error = curl_error($curl);
        curl_close($curl);

        if ($status === 404) {
            return null;
        }
        if ($body === false || $status !== 200) {
            throw new PlacesUnavailable("Places API failed: HTTP {$status} {$error}");
        }
        $data = json_decode((string) $body, true);
        if (!is_array($data)) {
            throw new PlacesUnavailable('Places API returned invalid JSON');
        }
        return $data;
    }
}
