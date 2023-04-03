#!/bin/bash

PHP_VERSION="${1:-8.2}"

echo -e "\n Using PHP version : $PHP_VERSION"
echo -e "\n Updating System Without Upgrade"
apt-get update -y
echo -e "\n Installing PHP & Requirements"
apt-get install php$PHP_VERSION php$PHP_VERSION-fpm php$PHP_VERSION-common php$PHP_VERSION-zip php$PHP_VERSION-redis  \
        php$PHP_VERSION-simplexml php$PHP_VERSION-xml php$PHP_VERSION-pdo php$PHP_VERSION-bcmath php$PHP_VERSION-msgpack \
        php$PHP_VERSION-mbstring php$PHP_VERSION-mcrypt php$PHP_VERSION-curl php$PHP_VERSION-dev php$PHP_VERSION-gd php$PHP_VERSION-imagick \
        php$PHP_VERSION-dom php$PHP_VERSION-gmp php$PHP_VERSION-iconv  php$PHP_VERSION-intl -y


# Enabling Mod Rewrite, required for WordPress permalinks and .htaccess files
echo -e "\n Enabling Modules"
phpenmod zip  \
         redis simplexml xml \
         pdo bcmath msgpack mbstring mcrypt \
         curl gd imagick dom gmp iconv intl

service php$PHP_VERSION-fpm restart
