server {
        listen      80;
        server_name finance.my-server.com;
        charset     utf-8;

        access_log  /var/log/nginx/finance.my-server.com-access.log;
        error_log   /var/log/nginx/finance.my-server.com-error.log;
        client_max_body_size 75M;

        location / {
                include proxy_params;
                proxy_pass http://unix:/var/www/python/financeiro/financeiro.sock;
        }

        location /media  {
                alias /var/www/python/financeiro/media;
        }

        location /static {
                alias /var/www/python/financeiro/static;
        }
}
