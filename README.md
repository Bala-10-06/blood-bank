# Blood Bank

A simple Blood Bank web application with a Python Flask backend, MySQL storage, a donor registration module, and a login module.

## Modules

### Register module

The registration form collects:

- User ID
- Password
- Aadhar number
- Name
- Blood group from a dropdown menu
- Age, limited to 18 through 55
- Height, limited to 120 cm through 220 cm
- Weight, limited to 45 kg through 200 kg
- Address
- Phone number
- Bad habits, with Yes or No options

Passwords are stored as secure hashes rather than plain text.

### Login module

The login form verifies the user by User ID and password. Successful users are redirected to a dashboard.

## Setup

1. Create and activate a Python virtual environment.
2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Create the MySQL database and table:

   ```bash
   mysql -u root -p < schema.sql
   ```

4. For a step-by-step SQL and run guide, see `SQL_RUN.md`.

   ```bash
   mysql -u root -p < schema.sql
   ```

4. Create your local environment file from the sample and update the values for your machine. The Flask app loads this `.env` file automatically at startup:

   ```bash
   cp .env.example .env
   ```

   The sample includes database settings, a Flask `SECRET_KEY`, and admin credentials:

   ```bash
   MYSQL_HOST=localhost
   MYSQL_USER=root
   MYSQL_PASSWORD=your_database_password
   MYSQL_DATABASE=blood_bank
   SECRET_KEY=replace-this-secret
   ADMIN_ID=admin
   ADMIN_PASSWORD=change-this-admin-password
   ```

   `MYSQL_PASSWORD` must match the password you use for the same MySQL user in MySQL Workbench. After changing `.env`, stop and restart the Flask app so the new value is loaded.

5. Run the application:

   ```bash
   python app.py
   ```

6. Open `http://127.0.0.1:5000` in a browser.
