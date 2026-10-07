# AGENTS.md


## Reports
- When reporting information to me, be concise. You are allowed to scacrifice grammar for concision


## Stack
- Flask backend
- SQLite
- HTML, CSS, JavaScript
- Tailwind as CSS framework


## Architecture
- Flask Blueprints organized by features
- Shared helpers belong in utils/


## Database
- SQLite is currently used
- Do not create a second database connection system
- Do not modify the schema without explaining the migration


## Code style
- Use `get_db()` for database connection
- Double quotes for string if such syntax is allowed
- Prefer readable code over clever code
- Don't introduce dependencies without asking and explaining