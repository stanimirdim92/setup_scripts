<?php

declare(strict_types=1);

namespace Acme;

/** Response and request helpers for the front controller. */
final class Http
{
    public static function json(mixed $data, int $status = 200): void
    {
        http_response_code($status);
        header('Content-Type: application/json');
        echo json_encode($data, JSON_THROW_ON_ERROR | JSON_UNESCAPED_SLASHES);
    }

    /** API errors are always {"error": "<snake_case_code>"} plus optional fields. */
    public static function error(string $code, int $status, array $extra = []): void
    {
        self::json(['error' => $code] + $extra, $status);
    }

    public static function html(string $body, int $status = 200): void
    {
        http_response_code($status);
        header('Content-Type: text/html; charset=utf-8');
        echo $body;
    }

    /** Renders templates/<name>.php inside templates/layout.php. */
    public static function render(string $template, array $vars, string $title): string
    {
        $content = self::capture(dirname(__DIR__) . "/templates/{$template}.php", $vars);
        return self::capture(dirname(__DIR__) . '/templates/layout.php', ['title' => $title, 'content' => $content]);
    }

    /** The decoded JSON body, or null when it is not a JSON object. */
    public static function jsonBody(): ?array
    {
        $data = json_decode((string) file_get_contents('php://input'), true);
        return is_array($data) ? $data : null;
    }

    public static function e(?string $value): string
    {
        return htmlspecialchars((string) $value, ENT_QUOTES, 'UTF-8');
    }

    private static function capture(string $file, array $vars): string
    {
        extract($vars);
        ob_start();
        require $file;
        return (string) ob_get_clean();
    }
}
