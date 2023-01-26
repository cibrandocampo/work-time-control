#!/bin/bash

if [ ! -f db.sqlite3 ]
then
	echo "Deploying database enviroment"
	python manage.py makemigrations
	python manage.py migrate
	
	if [ -d "$BACKUP_PATH" ]; then
		last_backup=$(find $BACKUP_PATH -type f -name "*wtc_backup.xml" | sort -r | head -n 1)
		if [ -z "$last_backup" ]
		then
		    echo "Loading default user"
		    DJANGO_SUPERUSER_PASSWORD=$ADMIN_PASSWORD python manage.py createsuperuser --username $ADMIN_USERNAME --email $ADMIN_EMAIL --noinput
		else
		    echo "Loading backup database"
		    python manage.py loaddata $last_backup
		fi
	fi
fi

echo "Starting WTC server in 0.0.0.0:$PORT"
python manage.py backup_manager &
gunicorn WTC.wsgi:application -w $WORKERS --bind 0.0.0.0:$PORT
