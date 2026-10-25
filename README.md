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
| `terminal.md` | Terminal tooling notes |

## AI tool dotfiles

The Claude Code and Codex harness lived under `dotfiles/` here until
2026-10-25. It is its own repository now, with its history:
[stanimirdim92/harness](https://github.com/stanimirdim92/harness). Its CI
workflow moved with it.
