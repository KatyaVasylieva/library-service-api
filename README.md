# Library service api
Service for managing book borrowings and payments.

### Special features:
* Supports JWT authorization.
* Allows users to create book borrowings initializing payment at once.
* Monitors book inventory.
* Creates Stripe session to every payment.
* Sends telegram notification to admin when the borrowing is created (optional).
* Executes every-day task for monitoring overdue borrowings, and sends notifications to admin (optional).
* Executes every-minute task for monitoring expired stripe sessions, marks this payments as expired.
* Implements return book functionality.
* Automatically create fine payment if user returned a book after expected return date.
* Implements a possibility to renew payment session if the previous one is expired.
* Forbids user to borrow another book if there are any pending payments user is supposed to pay.


### Before running (optional):
- Send any message to this telegram bot - https://t.me/library_service_api_bot.
Or you can create your own telegram bot through the BotFather - https://t.me/BotFather. In this case don't forget to change TELEGRAM_TOKEN environment variable.
- Get the chat id. To do so, start a conversation with this bot https://t.me/getmyid_bot. CHAT_ID environment variable will have the same value as "Your user ID". 

### How to run:
- Rename ".env.sample" into ".env" and populate with all required data.
- `docker-compose up --build`
- Get the id of "library_service_api-web" container by running `docker ps`
- Load test data by running `docker exec -it <container_id>  python manage.py loaddata test_data.json`.

Test data already includes implemented periodic tasks. Use this admin user to explore the functionality:
* Username: `admin@test.com`
* Password: `testpassword`
