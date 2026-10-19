-- The whole schema. bin/migrate runs this file, then seed.sql.
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

-- Every outgoing email. Acme\Mailer is the only writer.
CREATE TABLE outbox (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    recipient  TEXT NOT NULL,
    subject    TEXT NOT NULL,
    body       TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
