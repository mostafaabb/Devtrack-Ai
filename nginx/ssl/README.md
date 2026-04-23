# Self-signed cert for development/testing
# Replace with real certificates from Let's Encrypt for production
#
# To generate self-signed certs for testing:
#   openssl req -x509 -newkey rsa:4096 -nodes \
#     -keyout key.pem -out cert.pem -days 365 \
#     -subj '/CN=localhost'
#
# For production with Let's Encrypt:
#   certbot certonly --webroot -w /var/www/certbot -d yourdomain.com
#
# Then copy to this directory:
#   cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem ./cert.pem
#   cp /etc/letsencrypt/live/yourdomain.com/privkey.pem ./key.pem
