# library-service-api

for telegram:
Send your Telegram bot (t.me/library_service_api_bot) a message (any random message)

How to run:
* Crate venv: `python -m venv venv`
* Activate it: `source venv/bin/activate`
* Install requirements: `pip install requirements.txt`
* Run migrations: `python manage.py migrate`
* Run Redis server: `docker run -d -p 6379:6379 redis`
* Run Celery worker for tasks handling: `celery -A library_service_api worker -l INFO`
* Run Celery beat for task scheduling: `celery -A library_service_api beat -l INFO --scheduler django_celery_beat.schedulers:DatabaseScheduler`
* Create schedule for running sync in DB
* Run app: `python manage.py runserver`
