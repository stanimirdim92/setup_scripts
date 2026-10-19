<?php

declare(strict_types=1);

// Acme\Foo\Bar lives in src/Foo/Bar.php. No Composer.
spl_autoload_register(static function (string $class): void {
    $prefix = 'Acme\\';
    if (!str_starts_with($class, $prefix)) {
        return;
    }
    $file = __DIR__ . '/' . str_replace('\\', '/', substr($class, strlen($prefix))) . '.php';
    if (is_file($file)) {
        require $file;
    }
});
