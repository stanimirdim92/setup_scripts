# setup_scripts

Server and workstation setup: web stack configuration, kernel tuning, and
provisioning scripts.

| Path | Contents |
| --- | --- |
| `nginx/` | Dockerfile, `nginx.conf`, site config, logrotate |
| `php/fpm/` | PHP-FPM, `php.ini`, and pool configuration |
| `redis/` | Dockerfile and `redis.conf` |
| `database/` | MySQL `my.cnf` |
| `linux/etc/` | `limits.conf` and network `sysctl` tuning |
| `tools/php_update.sh` | Installs a PHP version and its extensions (run as root; `./tools/php_update.sh 8.3`) |
| `docs/terminal.md` | Terminal tooling notes |
| `docs/ai-engineer-route.md` | AI engineering learning roadmap; `.html` is the same roadmap as an interactive page with progress tracking |

## AI tool dotfiles

`dotfiles/` holds the Claude Code and Codex harness: agents, commands, skills,
hooks, its tools and tests, its decision records, and its observation log.
Start with [dotfiles/README.md](dotfiles/README.md) and
[dotfiles/ARCHITECTURE.md](dotfiles/ARCHITECTURE.md).

`.github/workflows/ci.yml` runs the harness's self-tests. It stays at the root
because GitHub reads workflows only from there.
