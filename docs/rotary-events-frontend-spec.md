# Frontend spec — Upcoming Events (add / delete)

Written for an agent working **in the frontend repo** (`rotary-frontend`, a Jekyll site).
The backend (`rotary-backend`, branch `rotary-events-crud`) already implements everything
described here. **Do not change backend code.** If something below seems to be missing,
re-read section 2 before assuming the API is wrong.

Local-only prototype: Flask on `http://localhost:8587`, Jekyll on `http://localhost:4500`,
SQLite behind the API. No deployment, no auth server beyond the existing Flask login.

---

## 1. Goal

Two surfaces, both fed by the same endpoint:

1. **Homepage (`index.md`)** — a read-only "Upcoming Events" table for every visitor.
2. **Management page (new)** — a table of all events with an add form and per-row Delete,
   visible and usable **only for a logged-in Admin**.

The backend enforces Admin-only writes. Frontend gating is UX, not security: always handle
the 401/403 responses instead of assuming a hidden button is enough.

---

## 2. API contract (final — do not propose changes)

Base path: `/api/rotary`. `pythonURI` from `assets/js/api/config.js` already resolves to
`http://localhost:8587` on localhost.

### `GET /api/rotary/events` — public

Returns a **bare JSON array**, ordered by date ascending. No pagination, no wrapper object.

```json
[
  { "id": 1, "date": "2026-11-12", "program": "Poway Rotary Parade, 9-11 AM on Poway Road", "speaker": "Community Event" },
  { "id": 2, "date": "2026-11-19", "program": "Robin's Nest Rescue", "speaker": "Jenny Ng" }
]
```

- `date` is always `YYYY-MM-DD`.
- `id` is an integer and is what DELETE needs.
- On a database problem: `503 { "message": "Failed to fetch upcoming events." }`.

### `POST /api/rotary/events` — Admin only

```json
{ "date": "2026-12-10", "program": "Holiday Potluck", "speaker": "Club Social" }
```

| Status | Body |
| --- | --- |
| `201` | `{ "id": 5, "date": "2026-12-10", "program": "Holiday Potluck", "speaker": "Club Social" }` |
| `400` | `{ "message": "Invalid event", "errors": ["date must be YYYY-MM-DD, got 'Dec 10'"] }` |
| `401` | `{ "message": "Authentication required. No session or token found.", ... }` |
| `403` | `{ "message": "Insufficient permissions. Required roles: Admin", ... }` |
| `500` | `{ "message": "Could not save the event" }` or `{ "message": "Server error in the rotary events API" }` |

Validation the backend applies — mirror it in the form so users get instant feedback:

- `date`: required, exactly `YYYY-MM-DD`. `<input type="date">` produces this natively.
- `program`: required, non-blank after trim, **max 255 characters**.
- `speaker`: required, non-blank after trim, **max 255 characters**.

### `DELETE /api/rotary/events/<id>` — Admin only

| Status | Body |
| --- | --- |
| `200` | `{ "message": "Deleted event 5", "event": { "id": 5, ... } }` |
| `404` | `{ "message": "No event with id 5" }` |
| `401` / `403` | as above |

**There is no update/edit endpoint.** Do not build an Edit button; add and delete only.

---

## 3. Authentication and the Admin check

Already implemented in the frontend — reuse it, do not build a second login:

- `assets/js/api/login.js` posts to `/api/authenticate`, the server sets a JWT cookie, and
  login.js fetches `GET /api/id` and assigns the result to **`window.user`**.
- `/api/id` returns the current user with `role`, **`is_admin`**, and `is_teacher`.
  Use `window.user?.is_admin === true` as the gate.
- All requests must send credentials. `fetchOptions` in `assets/js/api/config.js` already
  sets `credentials: 'include'` and `Content-Type: application/json` — spread it and
  override `method` (and add `body` for POST).
- Requests only work when the page is served from `http://localhost:4500`. The backend CORS
  allowlist is an exact origin list; a different port (`make dev PORT=...`) fails at the
  network level with an opaque CORS error, not a 401.

### 401 vs 403 — they mean different things

- **401** — no session at all. Treat as "not logged in": hide controls, page still renders.
- **403** — logged in, but not allowed. Two causes:
  - the account's role is not `Admin`;
  - or `{ "message": "Account pending verification." }` — the account is **inactive**
    (not yet verified). This is not a role problem and the frontend cannot fix it; surface
    the message.

---

## 4. UI requirements

### 4a. Homepage — `index.md`

`index.md` currently uses `layout: powpac` and its "Upcoming Shows and Events" section lost
the table in the Rotary → PowPAC switch. Restore a table there:

- Columns: **Date | Program | Speaker**.
- `<tbody id="upcoming-events-body">` — `assets/js/rotary-events.js` looks up exactly this id.
- Include the script as a module, with Jekyll's filter so `baseurl` is respected:

  ```html
  <script type="module" src="{{ '/assets/js/rotary-events.js' | relative_url }}"></script>
  ```

- Show only events whose `date >= today` (ISO strings compare correctly as strings).
  The backend returns all events; filtering "upcoming" is the frontend's job.
- Format the date for display (e.g. `Nov 12, 2026`) from the ISO value, using a fixed
  locale so it does not depend on the browser.
- Empty state: one row spanning all three columns, text `No upcoming events.`
- Error state: one row, `Failed to fetch upcoming events.` (already what the existing script does).
- **No add/delete controls on the homepage.**

### 4b. Management page — new file (suggested `events.md`)

Front matter, matching the rest of the site:

```yaml
---
layout: powpac
title: Events
---
```

Contents:

1. **Add form** (only rendered/usable for an Admin)
   - `date` — `<input type="date" required>`
   - `program` — text, `maxlength="255"`, `required`
   - `speaker` — text, `maxlength="255"`, `required`
   - submit button `Add event`; disabled while a request is in flight
   - on `201`: clear the form, refetch the table, announce success
   - on `400`: show each string from `errors` inline — not `alert(response)` and not
     "undefined". The body is `{ message, errors: [] }`.
   - on `401`/`403`: hide the form and show the message (see section 3)

2. **Table of all events** (no date filter here): **Date | Program | Speaker | Actions**
   - Actions cell holds a `Delete` button per row.
   - Delete: `confirm()` first, then `DELETE /api/rotary/events/<id>`; on `200` refetch
     (or remove the row), on `404` treat as already gone and refetch.
   - Empty state row spanning all four columns: `No events yet.`
   - Error state as on the homepage.

3. **Role gating**
   - `window.user?.is_admin` is `true` → form + Actions column visible.
   - Otherwise → no form, no Actions column. A short note such as
     `Sign in as an administrator to add or remove events.` is fine, but never render
     a disabled-looking control that will 403 when clicked.

`login.js` runs on `DOMContentLoaded`, so `window.user` may be `null` for a moment after
load. Either await it or re-render the gated parts once it is set; do not permanently hide
the controls based on the first (empty) read.

---

## 5. Reuse, do not reinvent

| Existing file | What to use |
| --- | --- |
| `assets/js/api/config.js` | `pythonURI`, `fetchOptions`, `baseurl`. Never hardcode `localhost:8587`. Note this file has Jekyll front matter and is regenerated on build. |
| `assets/js/rotary-events.js` | Already does GET + render into `#upcoming-events-body` with the exact date/program/speaker fields. Re-wire it (and extend it) rather than starting over. |
| `assets/js/api/login.js` | Establishes `window.user`; do not duplicate login. |
| `_layouts/powpac.html` | Layout for the new page; `index.md` already uses it. |

There is no generic POST/DELETE helper — write explicit `fetch` calls with
`{ ...fetchOptions, method: 'POST', body: JSON.stringify(...) }`.

---

## 6. Gotchas

- **Dates:** ISO only. `Dec 10` is rejected with a 400. `<input type="date">` avoids this.
- **Trailing spaces:** the backend trims, but it rejects an all-whitespace program or
  speaker. Trim before sending so the error is immediate.
- **Deleted sample data does not come back.** The backend seeds a fresh database once. If
  the list is empty during a demo, either add events through the form or reset the backend
  database: run `scripts/db_init.py` in the backend repo, or delete
  `instance/volumes/user_management.db` and restart Flask. Do not "fix" it on the frontend.
- **`baseurl` is `/portfolio`.** The dev site is served at
  `http://localhost:4500/portfolio/...`. Use `relative_url` for asset and link paths;
  the API origin is unaffected.
- **Jekyll watch:** `make dev` rebuilds on file changes. If a change does not appear,
  check `/tmp/jekyll4500.log` before blaming the API.
- **No optimistic UI.** Refetch after a write; it is one small GET and avoids duplicated
  or stale rows.

---

## 7. Acceptance checklist

- [ ] Homepage shows the seeded events ordered by date, formatted readably.
- [ ] Homepage hides events whose date is in the past.
- [ ] Homepage renders correctly when logged out (still calls the API, no controls).
- [ ] Logged out on the management page: no form, no Delete buttons, no console errors.
- [ ] Logged in as a non-Admin: same as logged out, plus a clear "administrator" note.
- [ ] Logged in as Admin: form visible; adding a valid event returns 201 and the new row
      appears in the management table and on the homepage.
- [ ] Invalid date / blank program / blank speaker: the backend's `errors` text is shown
      inline; no request is left spinning.
- [ ] Deleting asks for confirmation, removes the row, and stays gone after a reload.
- [ ] Deleting the last event shows `No events yet.`, not a broken table.
- [ ] No hardcoded backend URL outside `config.js`; no new login flow.
- [ ] No Edit button, no update endpoint assumed.

---

## 8. Manual verification

```bash
# terminal A — backend
cd ~/dragon-rg/rotary-backend
source venv/bin/activate
git checkout rotary-events-crud
python main.py                # http://localhost:8587

# terminal B — frontend
cd ~/dragon-rg/rotary-frontend
make dev                      # http://localhost:4500/portfolio/
```

```bash
curl -s http://localhost:8587/api/rotary/events    # sanity check the contract
```

Then: load the homepage logged out → log in as the team's Admin account → reload the
management page → add and delete an event → log out and confirm the controls disappear.

## 9. Out of scope

Edit/update, drag-to-reorder, pagination, search/filtering beyond the upcoming filter,
event images or links, time-of-day, timezone handling, and anything involving deployment.
