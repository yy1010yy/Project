# The Courtyard

A hotel reservation and management web app built for a CS50 final project.
Guests can find available rooms and book stays. Receptionists and managers can
manage room inventory and make reservations for guests, while managers also
manage staff accounts. Prices are displayed in Malaysian Ringgit (MYR).

## Features

- Guest registration, login, logout, and password changes.
- Access controls for guests, receptionists, and managers.
- Room search by stay dates and optional room type.
- Guest booking confirmation and a personal reservation list.
- Staff bookings for existing guests or newly created guest accounts.
- Availability checks inside a database transaction to prevent conflicting bookings.
- Staff dashboards showing reservations, today's arrivals, and departures.
- Room creation, nightly rate editing, and room condition updates.
- Manager tools to create, edit, and deactivate staff accounts.
- Temporary passwords that must be changed before accessing protected features.
- Shared responsive templates, local assets, and custom error pages.

## Technology

| Layer | Tools |
| --- | --- |
| Backend | Python, Flask, feature-based Blueprints |
| Database | SQLite through the shared `get_db()` helper |
| Sessions | Flask-Session with filesystem storage |
| Frontend | Jinja templates, HTML, CSS, JavaScript, Tailwind CSS |
| Configuration | Environment variables and python-dotenv |
| Tests | Python unittest and Flask's test client |

## Local setup

The commands below use Windows PowerShell. Run them from the repository root.
Python is required. Node.js and npm are needed only when rebuilding the CSS;
the compiled stylesheet is included in the repository.

### 1. Create and activate a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

If `.venv` already exists, activate it and install any missing requirements.
Activation applies to the current terminal session. Without activation, use
`.\.venv\Scripts\python.exe` instead of `python` in the commands below.

### 2. Configure the environment

If you already have a configured `.env`, keep it. Otherwise:

```powershell
Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_hex(32))"
```

Copy the generated value into `SECRET_KEY` in `.env`:

```dotenv
SECRET_KEY=your-generated-secret
FLASK_APP=app
```

Use the generated value, rather than the placeholder above. `.env` is ignored by
Git; `.env.example` is the reusable configuration template. An existing
`SECRET_KEY` environment variable takes precedence over the `.env` value.

### 3. Initialize the database

```powershell
python -m flask --app app init-db
```

This applies `app/database/schema.sql` to `app/database/hotel.db`, creating missing
tables and initializing employee ID counters. Run it for initial setup. Repeating
it preserves existing rows and counters, but it does not migrate an older schema.
App startup does not initialize or seed the database.

### 4. Start the app

The current factory sets `SESSION_COOKIE_SECURE=True`, which requires HTTPS for
session cookies. For local development over HTTP, set `SESSION_COOKIE_SECURE=False`
in `app/__init__.py` before starting. Use `True` when serving the app over HTTPS.

```powershell
python -m flask --app app run --debug
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000). Stop the server with **Ctrl+C**.
Debug mode reloads the server when Python files change.

`--app app` loads the `app` package and calls `create_app()` in `app/__init__.py`.
This runs the main application using `app/database/hotel.db`.

## First accounts and rooms

An initialized database has no accounts, rooms, or reservations. Public
registration creates guest accounts. Creating staff through the website requires
an existing manager account.

To create the first manager in a fresh database, open a separate terminal, activate
the environment, and start the Flask shell:

```powershell
python -m flask --app app shell
```

Enter the following Python statements. Use an unused name and email address.
The password prompt hides what you type.

```python
from getpass import getpass
from werkzeug.security import generate_password_hash
from app.db import get_db
from app.staff.utility import assign_employee_id

username = input("Manager name: ").strip()
email = input("Manager email: ").strip().lower()
password_hash = generate_password_hash(getpass("Manager password: "))

db = get_db()
db.execute("BEGIN IMMEDIATE")
employee_id = assign_employee_id(db, "manager")
cursor = db.execute(
    "INSERT INTO users (username, email, hashed_password, user_role) VALUES (?, ?, ?, ?)",
    (username, email, password_hash, "manager"),
)
db.execute(
    "INSERT INTO staff (user_id, employee_id) VALUES (?, ?)",
    (cursor.lastrowid, employee_id),
)
db.commit()
exit()
```

Log in with that manager account. Use **Rooms** to add inventory and **Our team**
to create staff accounts. Staff and guests created with temporary passwords must
replace those passwords after logging in.

Supported room types are `standard`, `deluxe`, `family`, and `business suite`.
Room conditions are `clean`, `dirty`, `maintenance`, and `out of service`.
Rooms under maintenance or out of service cannot be booked. A guest can check in
on the same date another booking checks out.

## Project structure

```text
app/
  __init__.py           App factory, configuration, and init-db command
  db.py                 Shared database connection and teardown
  auth/                 Authentication and password management
  bookings/             Guest and staff booking routes
  dashboard/            Role dashboards and shared presentation setup
  rooms/                Availability search and room inventory
  staff/                Staff account management
  utils/                Shared validation, access, and presentation helpers
  database/schema.sql   Database schema
templates/              Jinja pages and reusable components
static/                 Compiled CSS, JavaScript, and sample images
frontend/styles.css     Tailwind source and theme
tests/                  Backend, frontend rendering, and factory tests
docs/                   Additional frontend and backend notes
.env.example            Environment configuration template
```

Shared static files are served at `/assets/` by the dashboard blueprint.
Session files are stored in `instance/sessions/`. Local database files, sessions,
virtual environments, and `.env` are ignored by Git.

## Frontend development

After installing Node.js and npm:

```powershell
npm ci
npm run build:css
```

To rebuild automatically while editing styles or templates:

```powershell
npm run watch:css
```

Edit `frontend/styles.css`; Tailwind writes the generated stylesheet to
`static/css/site.css`. Reload the browser after frontend changes.

## Testing

With the virtual environment active:

```powershell
python -B -m unittest discover -s tests -t . -v
```

Tests use temporary SQLite databases. They cover app initialization, authentication,
role restrictions, password changes, room availability, booking conflicts,
concurrent submissions, staff management, templates, and local assets.

If Node.js is installed, check the shared JavaScript syntax with:

```powershell
node --check static/js/site.js
```

## Current scope

- Housekeeper accounts are supported by the schema and staff management, but the
  housekeeper dashboard is unfinished.
- Staff dashboards display booking statuses; check-in, check-out, and cancellation
  actions are not implemented.
- Payments and tax calculations are not implemented. Stay totals use nightly rate
  multiplied by the number of nights.
- The hotel name and generated interior images are sample branding and imagery.

## Further documentation

- [Frontend notes](docs/frontend.md): templates, assets, and the optional demo
  preview. Demo accounts belong to that preview and are not created by `init-db`.
- [Backend notes](docs/backend-fixes.md): database behavior and previous backend fixes.
