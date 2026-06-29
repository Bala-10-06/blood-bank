# SQL and Run Instructions

This file explains how to set up the MySQL schema and start the Blood Bank Flask app.

## 1. Prerequisites

- Python 3 installed
- MySQL server installed and running locally
- A terminal opened in `d:\bloodbank\blood-bank`

## 2. Create and activate a Python virtual environment

```powershell
python -m venv venv
.\venv\Scripts\activate
```

## 3. Install dependencies

```powershell
pip install -r requirements.txt
```

## 4. Create the MySQL database and table

### Option A: Use the MySQL CLI (recommended)

```powershell
mysql -u root -p < schema.sql
```

Enter your MySQL password when prompted.

### Option B: If the MySQL CLI is not installed

The project can also use Python to create the database and schema.

```powershell
python -c "import mysql.connector; conn=mysql.connector.connect(host='127.0.0.1', user='root', password='6379'); cursor=conn.cursor(); sql=open('schema.sql','r',encoding='utf-8').read();
for result in cursor.execute(sql, multi=True): pass
conn.commit(); cursor.close(); conn.close(); print('schema applied')"
```

Adjust the `user` and `password` values if your MySQL credentials differ.

## 5. Create the local environment file

```powershell
copy .env.example .env
```

Open `.env` and update these values:

- `MYSQL_HOST` (usually `127.0.0.1`)
- `MYSQL_PORT` (usually `3306`)
- `MYSQL_USER`
- `MYSQL_PASSWORD`
- `MYSQL_DATABASE`
- `SECRET_KEY`
- `ADMIN_ID`
- `ADMIN_PASSWORD`

## 6. Start the Flask app

```powershell
python app.py
```

## 7. Open the app in the browser

Visit:

```text
http://127.0.0.1:5000
```

## 8. Troubleshooting

- `The MySQL database was not found.`
  - Run `mysql -u root -p < schema.sql` or use the Python schema command above.

- `Table 'blood_bank.donors' doesn't exist`
  - The schema was not applied. Run the SQL schema file again.

- `Registration failed: 1045` or connection refused
  - Confirm `.env` matches your local MySQL credentials.
  - Ensure MySQL is running.

- `.env` changes not loading
  - Stop and restart the Flask app after editing `.env`.
