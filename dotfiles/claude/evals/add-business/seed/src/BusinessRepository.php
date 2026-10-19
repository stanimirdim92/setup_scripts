<?php

declare(strict_types=1);

namespace Acme;

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

    public function find(int $id): ?array
    {
        $stmt = $this->pdo->prepare('SELECT ' . self::COLUMNS . ' FROM businesses WHERE id = ?');
        $stmt->execute([$id]);
        $row = $stmt->fetch();
        return $row === false ? null : self::hydrate($row);
    }

    private static function hydrate(array $row): array
    {
        $row['id'] = (int) $row['id'];
        return $row;
    }
}
