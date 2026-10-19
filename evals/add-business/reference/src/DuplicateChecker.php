<?php

declare(strict_types=1);

namespace Acme;

use Acme\Places\Place;

/**
 * Finds the existing business a place duplicates. Rules, in order:
 * place_id, cid, domain, name_zip, phone. Businesses of any status count.
 */
final class DuplicateChecker
{
    private const SECOND_LEVEL = ['co', 'com', 'net', 'org', 'gov', 'ac'];

    /** @param list<array> $businesses */
    public function __construct(private readonly array $businesses)
    {
    }

    /** @return array{id: int, name: string, status: string, rule: string}|null */
    public function find(Place $place): ?array
    {
        $rules = [
            'place_id' => fn (array $b): bool => $b['place_id'] !== null && $b['place_id'] === $place->placeId,
            'cid' => fn (array $b): bool => $place->cid !== null && $b['cid'] === $place->cid,
            'domain' => fn (array $b): bool => self::sameNonNull(self::rootDomain($place->website), self::rootDomain($b['website'])),
            'name_zip' => fn (array $b): bool => $place->zip !== null && $place->zip === $b['zip']
                && self::name($place->name) === self::name((string) $b['name']),
            'phone' => fn (array $b): bool => self::sameNonNull(self::phone($place->phone), self::phone($b['phone'])),
        ];
        foreach ($rules as $rule => $matches) {
            foreach ($this->businesses as $business) {
                if ($matches($business)) {
                    return [
                        'id' => (int) $business['id'],
                        'name' => $business['name'],
                        'status' => $business['status'],
                        'rule' => $rule,
                    ];
                }
            }
        }
        return null;
    }

    public static function rootDomain(?string $url): ?string
    {
        if ($url === null || trim($url) === '') {
            return null;
        }
        $url = trim($url);
        if (!preg_match('#^[a-z][a-z0-9+.-]*://#i', $url)) {
            $url = 'http://' . $url;
        }
        $host = parse_url($url, PHP_URL_HOST);
        if (!is_string($host) || $host === '') {
            return null;
        }
        $host = preg_replace('/^www\./', '', strtolower($host));
        $labels = explode('.', $host);
        $count = count($labels);
        if ($count < 2) {
            return $host;
        }
        $keep = 2;
        if ($count >= 3 && strlen($labels[$count - 1]) === 2 && in_array($labels[$count - 2], self::SECOND_LEVEL, true)) {
            $keep = 3;
        }
        return implode('.', array_slice($labels, -$keep));
    }

    public static function name(string $name): string
    {
        $name = preg_replace('/[^\p{L}\p{N}]+/u', ' ', mb_strtolower($name));
        return trim((string) preg_replace('/\s+/', ' ', (string) $name));
    }

    public static function phone(?string $phone): ?string
    {
        $digits = preg_replace('/\D/', '', (string) $phone);
        return strlen((string) $digits) < 10 ? null : substr((string) $digits, -10);
    }

    private static function sameNonNull(?string $a, ?string $b): bool
    {
        return $a !== null && $a === $b;
    }
}
