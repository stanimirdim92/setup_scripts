<?php

declare(strict_types=1);

// Hidden API checks for the add-business eval. grade.sh runs this file:
//   php run.php DEST OUT_JSON FIXTURE WORK_DIR
// It starts DEST's bin/serve on free ports, resets the database before each check
// with `php bin/migrate`, and writes {"<id>": {"pass": bool, "detail": "..."}} to OUT_JSON.
// It relies only on ticket.md and the commands in the seed's CLAUDE.md.

[, $dest, $out, $fixture, $work] = $argv + [null, null, null, null, null];
if (!$dest || !$out || !$fixture || !$work) {
    fwrite(STDERR, "usage: php run.php DEST OUT_JSON FIXTURE WORK_DIR\n");
    exit(2);
}

$db = $work . '/api.sqlite';
$env = ['ACME_DB' => $db, 'ACME_PLACES' => 'fixture', 'ACME_PLACES_FIXTURE' => $fixture];

final class CheckFailed extends RuntimeException
{
}

function ok(bool $condition, string $message): void
{
    if (!$condition) {
        throw new CheckFailed($message);
    }
}

function show(mixed $value): string
{
    return substr((string) json_encode($value, JSON_UNESCAPED_SLASHES), 0, 300);
}

function free_port(): int
{
    $socket = stream_socket_server('tcp://127.0.0.1:0');
    $port = (int) substr(strrchr((string) stream_socket_get_name($socket, false), ':'), 1);
    fclose($socket);
    return $port;
}

/** Runs a command in DEST with extra env. Returns [exit code, stdout+stderr]. */
function run_in(string $dest, array $command, array $env): array
{
    $proc = proc_open($command, [1 => ['pipe', 'w'], 2 => ['redirect', 1]], $pipes, $dest, getenv() + $env);
    $output = stream_get_contents($pipes[1]);
    fclose($pipes[1]);
    return [proc_close($proc), (string) $output];
}

/** Starts bin/serve; returns [process, base URL]. */
function start_server(string $dest, array $env)
{
    $port = free_port();
    $log = fopen('php://temp', 'w+');
    $proc = proc_open(['bash', 'bin/serve'], [0 => ['file', '/dev/null', 'r'], 1 => $log, 2 => $log], $pipes, $dest, getenv() + $env + ['PORT' => (string) $port, 'HOST' => '127.0.0.1']);
    $base = "http://127.0.0.1:{$port}";
    for ($i = 0; $i < 100; $i++) {
        $socket = @fsockopen('127.0.0.1', $port, $errno, $errstr, 0.2);
        if ($socket) {
            fclose($socket);
            return [$proc, $base];
        }
        usleep(100_000);
    }
    proc_terminate($proc);
    throw new RuntimeException("bin/serve did not listen on port {$port}");
}

/** One HTTP call. Returns [status, decoded JSON or null, raw body]. */
function http(string $method, string $url, ?array $json = null): array
{
    $headers = "Accept: application/json\r\n";
    $content = null;
    if ($json !== null) {
        $content = json_encode($json);
        $headers .= "Content-Type: application/json\r\n";
    }
    $context = stream_context_create(['http' => [
        'method' => $method, 'header' => $headers, 'content' => $content,
        'ignore_errors' => true, 'timeout' => 10, 'follow_location' => 0,
    ]]);
    $body = @file_get_contents($url, false, $context);
    $status = 0;
    foreach ($http_response_header ?? [] as $line) {
        if (preg_match('#^HTTP/\S+ (\d{3})#', $line, $m)) {
            $status = (int) $m[1];
        }
    }
    $body = $body === false ? '' : $body;
    $decoded = json_decode($body, true);
    return [$status, is_array($decoded) ? $decoded : null, $body];
}

function count_rows(string $db, string $table): int
{
    $pdo = new PDO('sqlite:' . $db);
    return (int) $pdo->query("SELECT COUNT(*) FROM {$table}")->fetchColumn();
}

$results = [];
$migrate = static function () use ($dest, $env): void {
    [$code, $output] = run_in($dest, [PHP_BINARY, 'bin/migrate'], $env);
    ok($code === 0, 'php bin/migrate failed: ' . trim($output));
};
$check = static function (string $id, callable $fn) use (&$results, $migrate): void {
    try {
        $migrate();
        $fn();
        $results[$id] = ['pass' => true, 'detail' => ''];
    } catch (Throwable $e) {
        $results[$id] = ['pass' => false, 'detail' => $e->getMessage()];
    }
    fwrite(STDERR, ($results[$id]['pass'] ? 'ok   ' : 'FAIL ') . $id . ' ' . $results[$id]['detail'] . "\n");
};

try {
    $migrate();
    [$server, $base] = start_server($dest, $env);
    [$failServer, $failBase] = start_server($dest, $env + ['ACME_PLACES_FAIL' => '1']);
} catch (Throwable $e) {
    fwrite(STDERR, 'setup failed: ' . $e->getMessage() . "\n");
    file_put_contents($out, json_encode(['_setup' => ['pass' => false, 'detail' => $e->getMessage()]]));
    exit(1);
}

$search = static fn (string $q): array => http('GET', $base . '/api/places/search?q=' . rawurlencode($q));
$create = static fn (array $body): array => http('POST', $base . '/api/businesses', $body);
$listIds = static function () use ($base): array {
    [$status, $body] = http('GET', $base . '/api/businesses');
    ok($status === 200 && isset($body['businesses']), "GET /api/businesses: HTTP {$status}");
    return array_column($body['businesses'], 'id');
};
$page = static function () use ($base): string {
    [$status, , $raw] = http('GET', $base . '/businesses');
    ok($status === 200, "GET /businesses: HTTP {$status}");
    return $raw;
};
$created = static function (string $placeId, array $extra = []) use ($create): array {
    [$status, $body] = $create(['place_id' => $placeId] + $extra);
    ok($status === 201, "POST {$placeId}: expected 201, got {$status} " . show($body));
    ok(is_array($body['business'] ?? null), 'POST response has no business: ' . show($body));
    return $body;
};
$ids = static fn (array $body): array => array_column($body['results'] ?? [], 'place_id');
$sameSet = static function (array $expected, array $actual, string $label): void {
    sort($expected);
    sort($actual);
    ok($expected === $actual, "{$label}: expected " . show($expected) . ', got ' . show($actual));
};

$check('BASE-2', static function () use ($listIds, $page): void {
    $ids = $listIds();
    ok(in_array(101, $ids, true), 'available business 101 missing from GET /api/businesses');
    ok(!in_array(103, $ids, true), 'pending business 103 listed by GET /api/businesses');
    $html = $page();
    ok(str_contains($html, 'Bluefin Sushi Bar'), 'available business missing from /businesses');
    ok(!str_contains($html, 'Mission Street Hardware'), 'pending business shown on /businesses');
});

$check('API-01', static function () use ($search): void {
    foreach (['', 'a', ' a ', 'S'] as $q) {
        [$status, $body] = $search($q);
        ok($status === 422, 'q=' . show($q) . ": expected 422, got {$status}");
        ok(($body['error'] ?? null) === 'query_too_short', 'q=' . show($q) . ': error ' . show($body));
    }
    [$status] = $search('su');
    ok($status === 200, "q=\"su\": expected 200, got {$status}");
});

$check('API-02', static function () use ($search, $ids, $sameSet): void {
    $cases = [
        'sunrise' => ['plc_F201', 'plc_F202'],
        'sunrise oakland' => ['plc_F202'],
        'Sunrise, 94122' => ['plc_F201'],
        'SUNRISE   bakery  94607' => ['plc_F202'],
        'berkeley' => ['plc_F206'],
        'irving' => ['plc_F201'],
        'gym' => ['plc_F204'],
        'bakery' => ['plc_F201', 'plc_F202', 'plc_F205'],
        'bakery san francisco' => ['plc_F201', 'plc_F205'],
        'sunrise berkeley' => [],
        'zzzz' => [],
    ];
    foreach ($cases as $q => $expected) {
        [$status, $body] = $search($q);
        ok($status === 200, "q=\"{$q}\": HTTP {$status}");
        ok(($body['query'] ?? null) !== null, "q=\"{$q}\": no query field");
        $sameSet($expected, $ids($body), "q=\"{$q}\"");
    }
});

$check('API-03', static function () use ($search, $fixture): void {
    [$status, $body] = $search('tidewater');
    ok($status === 200 && count($body['results'] ?? []) === 1, 'q="tidewater": ' . $status . ' ' . show($body));
    $result = $body['results'][0];
    $place = array_values(array_filter(
        json_decode((string) file_get_contents($fixture), true),
        static fn (array $p): bool => $p['place_id'] === 'plc_F203',
    ))[0];
    foreach ($place as $key => $value) {
        ok(array_key_exists($key, $result) && $result[$key] === $value, "field {$key}: expected " . show($value) . ', got ' . show($result[$key] ?? '(missing)'));
    }
    ok(array_key_exists('existing', $result) && $result['existing'] === null, 'existing should be null: ' . show($result['existing'] ?? '(missing)'));
});

$check('API-04', static function () use ($search): void {
    $cases = [
        ['bluefin', 'plc_F101', 101, 'domain', 'available'],
        ['golden gate', 'plc_F102', 102, 'name_zip', 'available'],
        ['mission', 'plc_A003', 103, 'place_id', 'pending'],
        ['harbor', 'plc_F104', 104, 'cid', 'available'],
        ['cedar', 'plc_F105', 105, 'phone', 'available'],
    ];
    foreach ($cases as [$q, $placeId, $id, $rule, $status]) {
        [, $body] = $search($q);
        $hit = array_values(array_filter($body['results'] ?? [], static fn ($r) => ($r['place_id'] ?? null) === $placeId))[0] ?? null;
        ok($hit !== null, "q=\"{$q}\": {$placeId} not in results");
        $e = $hit['existing'] ?? null;
        ok(is_array($e), "{$placeId}: existing is " . show($e));
        ok(($e['id'] ?? null) === $id, "{$placeId}: existing.id expected {$id}, got " . show($e['id'] ?? null));
        ok(($e['rule'] ?? null) === $rule, "{$placeId}: rule expected {$rule}, got " . show($e['rule'] ?? null));
        ok(($e['status'] ?? null) === $status, "{$placeId}: status expected {$status}, got " . show($e['status'] ?? null));
        ok(is_string($e['name'] ?? null) && $e['name'] !== '', "{$placeId}: existing.name missing");
    }
    foreach (['fitness' => 'plc_F204', 'northside' => 'plc_F206', 'bayview' => 'plc_F205'] as $q => $placeId) {
        [, $body] = $search($q);
        $hit = array_values(array_filter($body['results'] ?? [], static fn ($r) => ($r['place_id'] ?? null) === $placeId))[0] ?? null;
        ok($hit !== null && array_key_exists('existing', $hit) && $hit['existing'] === null, "{$placeId} should have existing: null, got " . show($hit));
    }
});

$check('API-05', static function () use ($failBase): void {
    [$status, $body] = http('GET', $failBase . '/api/places/search?q=sunrise');
    ok($status === 502, "expected 502, got {$status}");
    ok(($body['error'] ?? null) === 'places_unavailable', 'error ' . show($body));
});

$check('API-06', static function () use ($created, $listIds, $page): void {
    $body = $created('plc_F201', ['notes' => 'Met at the trade fair']);
    ok(is_string($body['request_id'] ?? null) && preg_match('/^REQ-[A-Z0-9]{6,}$/', $body['request_id']) === 1, 'request_id ' . show($body['request_id'] ?? null));
    $b = $body['business'];
    ok(is_int($b['id'] ?? null), 'business.id is not an integer: ' . show($b['id'] ?? null));
    ok(($b['status'] ?? null) === 'pending', 'status ' . show($b['status'] ?? null));
    ok(($b['name'] ?? null) === 'Sunrise Bakery' && ($b['zip'] ?? null) === '94122' && ($b['place_id'] ?? null) === 'plc_F201', 'business ' . show($b));
    ok(($b['notes'] ?? null) === 'Met at the trade fair', 'notes ' . show($b['notes'] ?? null));
    ok(!in_array($b['id'], $listIds(), true), 'pending business is in GET /api/businesses');
    ok(!str_contains($page(), 'Sunrise Bakery'), 'pending business is on /businesses');

    $other = $created('plc_F203', ['notes' => '']);
    ok(array_key_exists('notes', $other['business']) && $other['business']['notes'] === null, 'empty notes should be null, got ' . show($other['business']['notes'] ?? '(missing)'));
    ok($other['request_id'] !== $body['request_id'], 'request IDs repeat');
});

$check('API-07', static function () use ($create, $db): void {
    $before = count_rows($db, 'businesses');
    foreach ([[], ['place_id' => ''], ['notes' => 'x']] as $payload) {
        [$status, $body] = $create($payload);
        ok($status === 422 && ($body['error'] ?? null) === 'invalid_request', 'payload ' . show($payload) . ": {$status} " . show($body));
    }
    [$status, $body] = $create(['place_id' => 'plc_F201', 'notes' => str_repeat('a', 1001)]);
    ok($status === 422 && ($body['error'] ?? null) === 'invalid_request', "1001-char notes: {$status} " . show($body));
    [$status, $body] = $create(['place_id' => 'plc_nope']);
    ok($status === 404 && ($body['error'] ?? null) === 'place_not_found', "unknown place: {$status} " . show($body));
    ok(count_rows($db, 'businesses') === $before, 'a rejected request created a business');
});

$duplicate = static function (string $placeId, int $id, string $rule) use ($create, $db): void {
    $before = count_rows($db, 'businesses');
    [$status, $body] = $create(['place_id' => $placeId, 'notes' => 'dup?']);
    ok($status === 409, "{$placeId}: expected 409, got {$status} " . show($body));
    ok(($body['error'] ?? null) === 'duplicate', 'error ' . show($body));
    ok(($body['existing']['id'] ?? null) === $id, "existing.id expected {$id}: " . show($body['existing'] ?? null));
    ok(($body['existing']['rule'] ?? null) === $rule, "rule expected {$rule}: " . show($body['existing'] ?? null));
    ok(count_rows($db, 'businesses') === $before, 'a duplicate was created');
};
$check('API-08', static fn () => $duplicate('plc_A003', 103, 'place_id'));
$check('API-09', static fn () => $duplicate('plc_F104', 104, 'cid'));
$check('API-10', static fn () => $duplicate('plc_F101', 101, 'domain'));
$check('API-11', static fn () => $duplicate('plc_F102', 102, 'name_zip'));
$check('API-12', static fn () => $duplicate('plc_F105', 105, 'phone'));

$check('API-13', static function () use ($created, $create, $search, $db): void {
    $first = $created('plc_F201');
    $newId = $first['business']['id'];
    [$status, $body] = $create(['place_id' => 'plc_F201']);
    ok($status === 409 && ($body['existing']['id'] ?? null) === $newId && ($body['existing']['rule'] ?? null) === 'place_id', "second submit: {$status} " . show($body));

    [, $body] = $search('sunrise');
    $byId = array_column($body['results'] ?? [], null, 'place_id');
    ok(($byId['plc_F201']['existing']['id'] ?? null) === $newId, 'search does not mark the new pending business: ' . show($byId['plc_F201'] ?? null));
    ok(array_key_exists('plc_F202', $byId) && $byId['plc_F202']['existing'] === null, 'same name in another ZIP marked as existing: ' . show($byId['plc_F202'] ?? null));

    $created('plc_F202'); // same name, other ZIP: not a duplicate
    $created('plc_F204'); // no website, no phone
    $created('plc_F206'); // no website, no phone: nulls never match
    ok(count_rows($db, 'businesses') === 10, 'expected 10 businesses, got ' . count_rows($db, 'businesses'));
});

$check('API-14', static function () use ($created, $dest, $env, $listIds, $page, $base): void {
    $body = $created('plc_F203');
    $id = $body['business']['id'];
    [$code, $output] = run_in($dest, [PHP_BINARY, 'bin/enrich'], $env);
    ok($code === 0, "php bin/enrich exited {$code}: " . trim($output));
    ok(preg_match('/Enriched [1-9]\d* business\(es\)/', $output) === 1, 'output: ' . trim($output));
    ok(in_array($id, $listIds(), true), 'business missing from GET /api/businesses after enrich');
    [, $list] = http('GET', $base . '/api/businesses');
    $row = array_values(array_filter($list['businesses'], static fn ($b) => $b['id'] === $id))[0];
    ok($row['status'] === 'available', 'status after enrich ' . show($row['status']));
    ok(str_contains($page(), 'Tidewater Books'), 'business missing from /businesses after enrich');
    [$code, $output] = run_in($dest, [PHP_BINARY, 'bin/enrich'], $env);
    ok($code === 0 && str_contains($output, 'Enriched 0 business(es)'), 'second run: ' . trim($output));
});

$check('API-15', static function () use ($created, $dest, $env, $db): void {
    $created('plc_F201');
    $created('plc_F203', ['notes' => 'Please email the owner']);
    [$code] = run_in($dest, [PHP_BINARY, 'bin/enrich'], $env);
    ok($code === 0, 'php bin/enrich failed');
    ok(count_rows($db, 'outbox') === 0, 'outbox has ' . count_rows($db, 'outbox') . ' message(s)');
});

$check('API-16', static function () use ($created): void {
    $body = $created('plc_F203', [
        'name' => 'Typed By Hand', 'street' => '1 Fake St', 'zip' => '00000', 'city' => 'Nowhere',
        'website' => 'https://typed.example', 'phone' => '000', 'status' => 'available',
    ]);
    $b = $body['business'];
    $expected = ['name' => 'Tidewater Books', 'street' => '77 Main St', 'zip' => '94105', 'city' => 'San Francisco',
        'website' => 'https://www.tidewaterbooks.com', 'phone' => '+1 415-555-0303', 'status' => 'pending'];
    foreach ($expected as $key => $value) {
        ok(($b[$key] ?? null) === $value, "{$key}: expected " . show($value) . ', got ' . show($b[$key] ?? null));
    }
});

proc_terminate($server);
proc_terminate($failServer);
proc_close($server);
proc_close($failServer);

file_put_contents($out, json_encode($results, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES));
exit(0);
