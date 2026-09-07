#!/usr/bin/env bash
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "php_update.sh must run as root (apt-get/service need it)." >&2
  exit 1
fi

PHP_VERSION="${1:-8.2}"

echo -e "\n Using PHP version : $PHP_VERSION"
echo -e "\n Updating System Without Upgrade"
apt-get update -y
echo -e "\n Installing PHP & Requirements"
# iconv, dom, simplexml, and pdo are bundled into php-common/php-xml, not
# separate packages — listing them here made apt-get fail to locate them and
# abort the whole install.
apt-get install -y "php$PHP_VERSION" "php$PHP_VERSION-fpm" "php$PHP_VERSION-common" "php$PHP_VERSION-zip" "php$PHP_VERSION-redis" \
        "php$PHP_VERSION-xml" "php$PHP_VERSION-bcmath" "php$PHP_VERSION-msgpack" \
        "php$PHP_VERSION-mbstring" "php$PHP_VERSION-mcrypt" "php$PHP_VERSION-curl" "php$PHP_VERSION-dev" "php$PHP_VERSION-gd" "php$PHP_VERSION-imagick" \
        "php$PHP_VERSION-gmp" "php$PHP_VERSION-intl"

# Enabling the installed extension modules
echo -e "\n Enabling Modules"
phpenmod zip \
         redis xml \
         bcmath msgpack mbstring mcrypt \
         curl gd imagick gmp intl

service "php$PHP_VERSION-fpm" restart
