<?php

declare(strict_types=1);

namespace Acme\Controller;

use Acme\App;
use Acme\Http;

final class BusinessController
{
    public function __construct(private readonly App $app)
    {
    }

    /** GET /businesses */
    public function index(): void
    {
        $businesses = $this->app->businesses()->listAvailable();
        Http::html(Http::render('businesses', ['businesses' => $businesses], 'Businesses'));
    }

    /** GET /api/businesses */
    public function apiIndex(): void
    {
        Http::json(['businesses' => $this->app->businesses()->listAvailable()]);
    }
}
