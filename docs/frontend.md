# Frontend and local preview

The Flask pages now use a shared Tailwind theme: paper tones, dark timber/olive
colours, spacious Palatino headings, and sample Malaysian courtyard and bedroom
imagery. “The Courtyard” is a temporary working name, not established branding.
All prices display in Malaysian Ringgit. No fonts, scripts or CSS require a CDN.

## Run locally

From the repository root, using the existing Python environment:

```powershell
npm ci
npm run build:css
./.venv/Scripts/python.exe -B dev_preview.py --port 5000
```

Open http://127.0.0.1:5000. The preview uses the production blueprints and
`get_db()` with an isolated `.preview/demo.db`. It seeds sample users, rooms and
reservations on first use. It does not initialize or modify `app/database/hotel.db`.
Preview data and its local session key are ignored by Git.

| Account | Email | Password |
| --- | --- | --- |
| Guest | guest@example.com | courtyard-demo |
| Receptionist | desk@example.com | courtyard-demo |
| Manager | manager@example.com | courtyard-demo |

For an already initialized database, pass an explicit path. This mode never
initializes or seeds it; bookings and edits then affect that supplied database.

```powershell
./.venv/Scripts/python.exe -B dev_preview.py --database "C:/path/to/hotel.db"
```

`npm run watch:css` recompiles during frontend work. Reload the browser after
changes. Tailwind and its CLI are build-only dev dependencies. The compiled
`static/css/site.css` is committed, so running Flask does not require Node.
The existing Flask runtime dependencies are unchanged.

## Pages and existing flows

- Public homepage, login, registration and password replacement.
- Guest stay/reservation list, signed-in room search and reservation review.
- Receptionist and manager ledgers using live reservations, today's arrivals
  and departures. Cancelled reservations remain in the full ledger, but are
  excluded from arrival/departure lists. There are no check-in/out actions.
- Existing/new guest selection and staff reservation confirmation.
- Room inventory, add-room and condition/rate editing for staff.
- Manager team list, creation, editing and deactivation confirmation.
- Empty results, server/form errors, loading and successful-save states.

Native forms retain the existing route parameters. JavaScript handles the
existing JSON endpoints, reports failures inline and prevents duplicate clicks.
The server still makes the final availability check under `BEGIN IMMEDIATE`.
Temporary credentials are displayed only in the current success panel and are
never put in browser storage. Password replacement remains required before
other authenticated features.

Room subtotals are nightly rate multiplied by nights; no payment collection or
tax calculation has been added. Housekeeper working pages remain deferred.

## App factory integration

`app/__init__.py` is untouched. The separate preview launcher makes the UI
reviewable while initialization is being finished.

The shared templates and `/assets` files are registered by `dashboard_bp`.
That blueprint also registers shared template context, money/date filters and
403/404 pages. Register `auth_bp`, `dashboard_bp`, `rooms_bp`, `bookings_bp` and
`staff_bp` in the finished factory, configure its secret key and database, and
register `close_db` for teardown. The preview launcher shows this integration
without replacing the project's factory.

## Replaceable sample imagery

These are generated sample interiors, not photographs or verified amenities of
an actual hotel. Replace them with real property imagery before public use.
Every reference and alt text lives in `app/utils/presentation.py` (`SITE_IMAGES`).
`ROOM_STORIES` maps room types to those image keys and short descriptions. Both
Jinja pages and room-search JavaScript consume the same map.

Built-in image generation was used, without the API/CLI fallback. The selected
1536 × 1024 PNG outputs are saved in the project:

- `static/images/courtyard.png`: Malaysian independent guesthouse courtyard,
  pale plaster walls, timber shutters, patterned cement tiles, cane chairs,
  tropical planting and warm natural daylight. Quiet editorial photography,
  lived-in textures, no people, signs, logos, text or watermark.
- `static/images/room.png`: modest Malaysian guesthouse bedroom, double bed
  with ivory linen, timber and cane furnishings, pale walls and shutters,
  soft window light. Natural editorial interior photography, warm and restful,
  without luxury-hotel styling, people, text, branding or watermark.
- `static/images/family.png`: matching guesthouse family bedroom with one
  double bed and one single bed, ivory linen, timber furniture, soft tropical
  daylight and natural textures. Spacious editorial interior photography,
  without people, signage, branding or watermark.

These generation briefs can be reused for replacements. Standard, deluxe and
business suite currently share the sample bedroom; they do not imply identical
real furnishings. Set distinct image keys when real room photographs exist.

## Validation

```powershell
./.venv/Scripts/python.exe -B -m unittest discover -s tests -t . -v
node --check static/js/site.js
npm run build:css
```

The frontend tests render the real templates against temporary SQLite files.
Browser checks cover guest and staff booking, room editing, role navigation,
and phone/desktop layouts. Visible focus rings, labelled fields, semantic
tables with keyboard-scrollable regions, native dialogs, live announcements,
and reduced-motion support are included. This is practical accessibility QA,
not a formal conformance audit.
