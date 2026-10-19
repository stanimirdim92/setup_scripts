<?php

declare(strict_types=1);

namespace Acme;

use Acme\Places\Place;
use PDO;

final class BusinessRepository
{
    private const COLUMNS = 'id, name, place_id, cid, street, zip, city, category, website, phone, maps_url, notes, status';

    public function __construct(private readonly PDO $pdo)
    {
    }

    /** Businesses users can work with. Pending ones are still being enriched and stay hidden. */
    public function listAvailable(): array
    {
        $rows = $this->pdo
            ->query('SELECT ' . self::COLUMNS . " FROM businesses WHERE status = 'available' ORDER BY name")
            ->fetchAll();
        return array_map(self::hydrate(...), $rows);
    }

    /** Every business, pending included. The duplicate check reads these. */
    public function all(): array
    {
        $rows = $this->pdo->query('SELECT ' . self::COLUMNS . ' FROM businesses ORDER BY id')->fetchAll();
        return array_map(self::hydrate(...), $rows);
    }

    public function find(int $id): ?array
    {
        $stmt = $this->pdo->prepare('SELECT ' . self::COLUMNS . ' FROM businesses WHERE id = ?');
        $stmt->execute([$id]);
        $row = $stmt->fetch();
        return $row === false ? null : self::hydrate($row);
    }

    /** Creates a pending business from a place and opens its enrichment request. */
    public function createPending(Place $place, ?string $notes, string $requestId): array
    {
        $this->pdo->prepare(
            'INSERT INTO businesses (name, place_id, cid, street, zip, city, category, website, phone, maps_url, notes, status)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, \'pending\')'
        )->execute([
            $place->name, $place->placeId, $place->cid, $place->street, $place->zip, $place->city,
            $place->category, $place->website, $place->phone, $place->mapsUrl, $notes,
        ]);
        $id = (int) $this->pdo->lastInsertId();
        $this->pdo
            ->prepare('INSERT INTO enrichment_requests (request_id, business_id) VALUES (?, ?)')
            ->execute([$requestId, $id]);
        return (array) $this->find($id);
    }

    /** Closes every open enrichment request and makes its business available. Returns the count. */
    public function completeOpenEnrichments(): int
    {
        $this->pdo->beginTransaction();
        $ids = $this->pdo
            ->query("SELECT business_id FROM enrichment_requests WHERE status = 'open'")
            ->fetchAll(PDO::FETCH_COLUMN);
        foreach ($ids as $id) {
            $this->pdo->prepare("UPDATE businesses SET status = 'available' WHERE id = ?")->execute([$id]);
        }
        $this->pdo->exec("UPDATE enrichment_requests SET status = 'done', done_at = CURRENT_TIMESTAMP WHERE status = 'open'");
        $this->pdo->commit();
        return count($ids);
    }

    private static function hydrate(array $row): array
    {
        $row['id'] = (int) $row['id'];
        return $row;
    }
}
