---
name: nginx-tuning
description: House-style conventions for this repo's nginx config (nginx/nginx.conf, nginx/conf.d/*.conf) — worker/connection sizing, header policy, caching maps, upstream proxy settings. Use when adding a new vhost or changing nginx performance/security settings.
---

# nginx conventions in this repo

These are the decisions already baked into `nginx/nginx.conf` and
`nginx/conf.d/default.conf` — follow them rather than re-deriving from a
generic nginx tutorial.

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
