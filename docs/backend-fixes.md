# Backend fixes

This pass preserves the guest booking, staff booking, and staff-management steps.
It leaves top-level `app/__init__.py`, housekeeper functionality, and the draft
booking JavaScript unchanged. The subsequent frontend work is documented in
[frontend.md](frontend.md), including an isolated local preview.

## Database

- Database operations use `hashed_password` and `user_role`, matching the schema.
- The role constraint references `user_role`; the bookings statement ends with
  a semicolon; indexes and employee-counter initialization can be run repeatedly.
- `get_db()` registers SQLite's required `regexp` function, enables foreign keys,
  and uses `sqlite3.Row`, rather than the nonexistent `sqlite3.ROW`.
- The default path resolves to `app/database/hotel.db` from the database helper's
  location, independent of the terminal's working directory. An explicit Flask
  `DATABASE` configuration overrides this path, including in regression tests.

The supplied `app/database/hotel.db` was empty during review. It has not been
initialized or replaced. These fixes do not add or rename columns, tables, or
stored room values, so they require no data migration for a database already
matching the supplied schema. Editing `schema.sql` does not modify an existing
database. Inspect any separately populated database before applying schema
changes; do not delete it or blindly rerun initialization as a migration.

## Authentication

- Login and password replacement read the correct password column.
- Guest/staff profile queries bind a one-item tuple correctly.
- A temporary-password login establishes the session before redirecting to
  password replacement. Protected routes allow password replacement but require
  completion before other features. Logout remains available.
- Password confirmation reads `confirm_password`. A successful replacement clears
  the requirement and returns the user to login, retaining the original flow.
- Registration calls `rollback()` correctly. Temporary-password generation uses
  `range(length)`. Quick registration inserts the guest profile correctly, releases
  its transaction on duplicates, and remembers the new guest for staff confirmation.
- Protected routes reject deactivated accounts and refresh roles from the database,
  so staff edits also take effect for existing sessions.
- Validation errors return 400, invalid login credentials return 401, and an already
  registered email returns 409. Invalid password-change forms retain their template
  but return 400 instead of reporting a successful HTTP response.

## Rooms and bookings

- The rooms homepage names its template and the search endpoint is valid.
- Status/type validation matches `out of service` and `business suite` in the schema.
- Room creation reports success. Editing saves the numeric price, with nonfinite
  prices rejected. Search validation returns JSON consistently and normalizes dates
  before availability comparisons, matching the booking submission routes.
- Booking initialization defines the feature blueprint and imports both route files.
- Existing-guest GET initializes an empty result list; POST search returns results.
  SQL names, quoting, partial matching, parameter binding, and missing input are fixed.
- Invalid confirmation requests redirect to the generic rooms homepage.
- Confirmations retain dates and room/guest information, including room details for
  the future staff confirmation template. Selection is cleared after successful booking.
- Guest submission initializes its database connection before querying. Both submission
  routes recheck room condition and overlapping reservations inside `BEGIN IMMEDIATE`.
  A direct request cannot reserve a maintenance/out-of-service room.

## Staff and navigation

- Staff queries/inserts/updates use schema column names; query aliases keep `role`
  available to templates. Route parameters are normalized.
- Staff creation validates email. Editing checks username/email conflicts consistently
  with creation; database failures roll back and return a server error. Conflict checks
  are repeated under the write lock so concurrent requests cannot bypass them.
- Dashboard blueprint and redirect spelling is corrected. Guest, receptionist, and
  manager handlers name their templates instead of falling through without a response.

## Validation and remaining integration

Run from the repository root after installing the existing `requirements.txt`:

```powershell
./.venv/Scripts/python.exe -B -m unittest discover -s tests -t . -v
```

Tests use Flask's test client and temporary SQLite files through the production
`get_db()` helper. Explicit test-only templates verify route rendering contracts;
they do not verify a finished frontend. Coverage includes password replacement,
role restrictions, staff editing/deactivation, both staff guest-selection paths,
overlapping reservations, and concurrent booking submissions.

The application still needs your app initialization for its normal entry point.
The frontend now provides production templates and a separate local preview.
Blueprint registration, secret-key
configuration, database initialization, and teardown registration belong in that
initialization. The frontend adds the public hotel homepage while retaining the
authenticated root dispatcher for signed-in users.
