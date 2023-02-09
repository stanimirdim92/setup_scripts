server {
	listen 80;
	listen [::]:80;
	server_name api.example.com new.example.com docs.example.com portal.example.com surveys.example.com mobile.example.com;
	root /var/www/html/nettoffice-api/public;

	# Add index.php to the list if you are using PHP
	index index.php;

    charset utf-8;

	location / {
		# First attempt to serve request as file, then
		# as directory, then fall back to displaying a 404.
        try_files $uri $uri/ /index.php?$query_string;
	}

	location = /favicon.ico { access_log off; log_not_found off; }
    location = /robots.txt  { access_log off; log_not_found off; }

	# pass PHP scripts to FastCGI server

	location ~ \.php$ {
		include snippets/fastcgi-php.conf;
		# With php-fpm (or other unix sockets):
		fastcgi_pass unix:/var/run/php/php8.1-fpm.sock;
	        fastcgi_param SCRIPT_FILENAME $realpath_root$fastcgi_script_name;
    		include fastcgi_params;
	}

	include custom.d/location/security_file_access.conf;
    include custom.d/location/web_performance_filename-based_cache_busting.conf;
	include custom.d/location/web_performance_svgz-compression.conf;

}


