<?php

declare(strict_types=1);

namespace Acme;

use PDO;

/** The only way the app sends mail. A worker outside this repo delivers the outbox. */
final class Mailer
{
    public function __construct(private readonly PDO $pdo)
    {
    }

    public function send(string $recipient, string $subject, string $body): void
    {
        $this->pdo
            ->prepare('INSERT INTO outbox (recipient, subject, body) VALUES (?, ?, ?)')
            ->execute([$recipient, $subject, $body]);
    }
}
