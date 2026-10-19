<?php

declare(strict_types=1);

// Test runner: php tests/run.php [filter]
// Each tests/*Test.php returns an array of 'test name' => callable. A test fails when it throws.

require __DIR__ . '/../src/bootstrap.php';
require __DIR__ . '/helpers.php';

$filter = $argv[1] ?? '';
$passed = 0;
$failed = 0;

foreach (glob(__DIR__ . '/*Test.php') as $file) {
    $tests = require $file;
    foreach ($tests as $name => $test) {
        $label = basename($file, '.php') . ' > ' . $name;
        if ($filter !== '' && !str_contains($label, $filter)) {
            continue;
        }
        try {
            $test();
            $passed++;
            echo "ok   {$label}\n";
        } catch (Throwable $e) {
            $failed++;
            echo "FAIL {$label}\n     " . get_class($e) . ': ' . $e->getMessage() . "\n";
        }
    }
}

echo "\n{$passed} passed, {$failed} failed\n";
exit($failed === 0 ? 0 : 1);
