---
name: nginx
description: nginx conventions and tuning — worker/connection sizing, header policy, caching, reverse-proxy/upstream settings, TLS. Use whenever adding a vhost or changing nginx config, in this repo or any other project.
---

# nginx conventions

General good practice, plus (marked explicitly) the specific decisions
already baked into this repo's `nginx/nginx.conf` and
`nginx/conf.d/default.conf` as a worked example to match against rather
than a from-scratch tutorial.

## General

- Put sizing/security directives that apply to every vhost in `http{}`
  once — `worker_connections`, `client_max_body_size`, gzip types,
  security headers. Never re-declare a global directive per-vhost;
  drift between vhosts is the most common nginx config bug.
- Prefer `map{}` blocks keyed on `$sent_http_content_type` (or similar)
  over per-`location` `add_header`/`expires` — one source of truth
  instead of N copies that go stale independently.
- Reverse proxy: always set `proxy_set_header Host/X-Real-IP/X-Forwarded-For/X-Forwarded-Proto`,
  decide `proxy_buffering` deliberately (off for streaming/SSE, on for
  everything else), and give each upstream its own named
  `proxy_cache_path`/cache key — never share a cache zone across apps.
- TLS: `ssl_protocols TLSv1.2 TLSv1.3` minimum, a modern cipher list,
  `ssl_stapling on`, and more than one DNS `resolver` for redundancy if
  the config resolves upstream hostnames dynamically.
- Always deny dotfiles and common sensitive extensions
  (`.bak|.conf|.sql|.env|...`) at the server level — one regex, not
  per-location.

## This repo's conventions (worked example)

**Global vs. per-vhost**: sizing (`worker_connections 10000`,
`client_max_body_size 20m`), the gzip type list, the `$expires`/`$cache_control`
maps, and every security header live once in `nginx.conf`'s `http{}` block.
`conf.d/*.conf` files only define `server{}` blocks and `location{}` rules —
never re-declare a global directive per-vhost.

**Vhost shape** (`conf.d/default.conf` is the template): an HTTP `server{}`
that does nothing but ACME-challenge + `return 301 https://...`, then one
HTTPS `server{}` with `reuseport backlog=1024`, its own `access_log`/`error_log`,
and the proxy block. Copy this shape for new vhosts instead of inventing a
new structure.

**Reverse proxy block**: `proxy_buffering off`, `proxy_redirect off`,
generous 315s timeouts, and an explicit `proxy_cache_path`/`proxy_cache_key`
pair per app (`MY_APP_TAG`/`MY_APP_FOLDER`) — give each new upstream its own
cache zone name, don't share one across apps.

**Sensitive-file deny list**: the regex blocking `.bak|.conf|.sql|...` and
dotfiles (`location ~* /\.(?!well-known\/)`) is the safety net for anything
accidentally left in the webroot. When adding a new static extension type,
check whether it needs adding to this deny list too (e.g. anything that
could contain secrets).

**TLS / resolver**: `ssl_protocols TLSv1.2 TLSv1.3` with the existing modern
cipher list, and a multi-provider DNS `resolver` list (Cloudflare, Google,
OpenDNS, Quad9, Verisign) for redundancy — don't collapse it to a single
resolver.

**Cache-Control / Expires**: driven by the `$expires` and `$cache_control`
maps keyed on `$sent_http_content_type`, not per-location `add_header`. Add
new content types there, not inline in a `location` block.
