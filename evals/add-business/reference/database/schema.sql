-- The whole schema. bin/migrate runs this file, then seed.sql.
DROP TABLE IF EXISTS enrichment_requests;
DROP TABLE IF EXISTS outbox;
DROP TABLE IF EXISTS businesses;

CREATE TABLE businesses (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL,
    place_id   TEXT,
    cid        TEXT,
    street     TEXT,
    zip        TEXT,
    city       TEXT,
    category   TEXT,
    website    TEXT,
    phone      TEXT,
    maps_url   TEXT,
    notes      TEXT,
    status     TEXT NOT NULL DEFAULT 'available' CHECK (status IN ('pending', 'available')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX businesses_status ON businesses (status);

-- One row per "add business" request. bin/enrich works through the open ones.
CREATE TABLE enrichment_requests (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id  TEXT NOT NULL UNIQUE,
    business_id INTEGER NOT NULL REFERENCES businesses (id),
    status      TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'done')),
    created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    done_at     TEXT
);

CREATE INDEX enrichment_requests_status ON enrichment_requests (status);

-- Every outgoing email. Acme\Mailer is the only writer.
CREATE TABLE outbox (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    recipient  TEXT NOT NULL,
    subject    TEXT NOT NULL,
    body       TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
