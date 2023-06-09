# Library service api
Service for managing book borrowings and payments.

### Special features:
* Supports JWT authorization.
* Allows users to create book borrowings initializing payment at once.
* Monitors book inventory.
* Creates Stripe session to every payment (optional).
* Sends telegram notification to admin when the borrowing is created (optional).
* Executes every-day task for monitoring overdue borrowings, and sends notifications to admin (optional).
* Executes every-minute task for monitoring expired stripe sessions, marks this payments as expired (optional).
* Implements return book functionality.
* Automatically create fine payment if user returned a book after expected return date.
* Implements a possibility to renew payment session if the previous one is expired.
* Forbids user to borrow another book if there are any pending payments user is supposed to pay.


### Before running (optional):

#### Telegram notifications:
- Send any message to this telegram bot - https://t.me/library_service_api_bot.
Or you can create your own telegram bot through the BotFather - https://t.me/BotFather. In this case don't forget to change TELEGRAM_TOKEN environment variable.
- Get the chat id. To do so, start a conversation with this bot https://t.me/getmyid_bot. CHAT_ID environment variable will have the same value as "Your user ID". 

#### Stripe sessions:
- Create Stripe account - https://stripe.com/en-gb-us.
- In your account move to Developers -> API keys and copy "Publishable key" and "Secret key" into .env file (STRIPE_PUBLIC_KEY and STRIPE_SECRET_KEY respectively).
- If you don't want to connect Stripe leave STRIPE_PUBLIC_KEY and STRIPE_SECRET_KEY variables as they are.

### How to run:
- Rename ".env.sample" into ".env" and populate with all required data.
- `docker-compose up --build`.

Use this admin user to explore the functionality:
* Username: `admin@test.com`
* Password: `testpassword`
