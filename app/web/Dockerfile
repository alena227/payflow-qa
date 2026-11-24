FROM nginx:1.27-alpine
COPY public/ /usr/share/nginx/html/
COPY extra/ /opt/extra/
COPY 40-theme.sh /docker-entrypoint.d/40-theme.sh
RUN sed -i 's/\r$//' /docker-entrypoint.d/40-theme.sh && chmod +x /docker-entrypoint.d/40-theme.sh
