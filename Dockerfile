FROM python:3.10-slim

# Enviroment variables
ENV BACKUP_PATH=/backup/
ENV ADMIN_USERNAME=admin
ENV ADMIN_PASSWORD=9FAeHdPv6p
ENV ADMIN_EMAIL=admin@wtc.com
ENV PORT=8000
ENV WORKERS=8

# Create directories
RUN mkdir /wtc
WORKDIR /wtc

# Install dependencies
COPY install/requirements /wtc/
RUN pip install --upgrade pip && pip install -r requirements && rm requirements

# Deploying docker enrtypoint
COPY install/entrypoint.sh /wtc/
RUN chmod +x /wtc/entrypoint.sh

# Deploying code and static files
COPY code/ /wtc/
RUN python manage.py collectstatic --noinput

EXPOSE $PORT

CMD ["/bin/bash", "/wtc/entrypoint.sh"]
