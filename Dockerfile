FROM python:3.11-slim

# Enviroment variables
ENV DEBUG=False
ENV LOG_LEVEL=WARNING
ENV ADMIN_USERNAME=admin
ENV ADMIN_PASSWORD=9FAeHdPv6p
ENV ADMIN_EMAIL=admin@wtc.com
ENV BACKUP_PATH=/backup/
ENV PORT=8000
ENV WORKERS=8
ENV ALLOWED_HOSTS=*
ENV CSRF_TRUSTED_ORIGINS=http://*127.0.0.1,https://*127.0.0.1


WORKDIR /app

# Copy & install requirements
COPY deploy/requirements requirements
RUN pip install --upgrade pip && pip install -r requirements && rm requirements

# Deploying docker enrtypoint
COPY deploy/entrypoint.sh entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Deploying code and static files
COPY src/ .
RUN python manage.py collectstatic --noinput

EXPOSE $PORT

CMD ["/bin/bash", "/app/entrypoint.sh"]
