FROM nginx:latest

RUN apt-get update &&  \
    apt-get upgrade -y && \
    apt-get install -y \
    logrotate

COPY nginx.conf /etc/nginx/nginx.conf
COPY conf.d/default.conf /etc/nginx/conf.d/default.conf

# Cache dir
RUN mkdir -p /nginx-cache/app_ai

# Create 'messages' file used from 'logrotate'
RUN touch /var/log/messages

# Copy 'logrotate' config file
COPY logrotate/nginx /etc/logrotate.d/

EXPOSE 80 443
