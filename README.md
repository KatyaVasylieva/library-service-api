# Library service api
Service for managing book borrowings and payments.

### Special features:
* Supports JWT authorization.
* Allows users to create book borrowings initializing payment at once.
* Monitors book inventory.
* Creates Stripe session to every payment.
* Sends telegram notification to admin when the borrowing is created.
* Executes every-day task for monitoring overdue borrowings, and sends notifications to admin.
* Executes every-minute task for monitoring expired stripe sessions, marks this payments as expired.
* Implements return book functionality.
* Automatically create fine payment if user returned a book after expected return date.
* Implements a possibility to renew payment session if the previous one is expired.
* Forbids user to borrow another book if there are any pending payments user is supposed to pay.


### Before running:
- Send any message to this telegram bot - t.me/library_service_api_bot.
- Get chat id. You'll be receiving notifications in this chat.

### How to run:
- Rename .env.sample into .env and populate with all required data.
- `docker-compose up --build`
- Create admin user
- Create periodic tasks for sending notifications about overdue and marking expired sessions.
