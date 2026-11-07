# Fix notes & rollback (SMS reminders + page speed)

**Date:** 2026-11-06
**Last commit before these changes:** `23795fe` ("fixing the issue with the sms")

This file covers two separate fixes:
- **Part 1 — SMS reminders stopping every week** (3 files)
- **Part 2 — Slow appointments / visits pages** (3 files)

Each part can be rolled back on its own.

---

# Part 1 — SMS reminders

## The problem

Automatic 24h reminder SMS stopped every ~week and only came back after restarting production.

**Cause:** the hourly task queued each reminder with a 24h delay (`apply_async(eta=...)`).
With Redis, Celery keeps those delayed tasks in worker memory, and Redis re-delivers them
every hour (1h `visibility_timeout`). Copies piled up until the worker stalled / lost its
Redis connection silently. Reminders missed during that time were never retried because the
task only looked at a ±30 min window.

## What changed (3 files)

### 1. `alpha/notifications/tasks.py`
- **`schedule_appointment_reminders`**: no longer schedules with a 24h ETA. It now finds every
  `booked` appointment starting within the next 24h that has no sent reminder, and dispatches
  the send task immediately. Missed runs catch up on the next run.
- Only appointments booked at least 23h ahead get a reminder (constant
  `REMINDER_MIN_BOOKING_LEAD` at the top of the file) — same as the old behaviour.
- **`send_appointment_reminder_task`**: now idempotent. It atomically marks the
  `ScheduledNotification` as sent *before* sending, so duplicates never send twice. If sending
  raises an error, the mark is undone and the task retries. Also skips appointments that are
  not `booked` (completed / no-show / cancelled) or have already started.

### 2. `config/settings/base.py`
- Beat schedule: `crontab(minute=0)` (hourly) → `crontab(minute='*/10')` (every 10 min).
- Added Celery resilience settings (block right after `CELERY_WORKER_HIJACK_ROOT_LOGGER`):
  `CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP`, `CELERY_BROKER_CONNECTION_MAX_RETRIES = None`,
  `CELERY_BROKER_TRANSPORT_OPTIONS` (keepalive, timeouts, health check),
  `CELERY_REDIS_SOCKET_KEEPALIVE`, `CELERY_REDIS_BACKEND_HEALTH_CHECK_INTERVAL`,
  `CELERY_WORKER_CANCEL_LONG_RUNNING_TASKS_ON_CONNECTION_LOSS`,
  `CELERY_WORKER_PREFETCH_MULTIPLIER = 1`, `CELERY_WORKER_MAX_TASKS_PER_CHILD = 200`.

### 3. `docker-compose.production.yml`
- Added `restart: unless-stopped` to `django` (inherited by `celeryworker`, `celerybeat`,
  `flower`), `postgres`, `traefik`, `redis`, `nginx`.

## How to check it works

```bash
docker compose -f docker-compose.production.yml logs -f celerybeat celeryworker | grep -i reminder
```
Every 10 minutes you should see `Dispatched N appointment reminders`.
The "Scheduled notifications" page in the app shows which reminders were sent.

## How to roll back

The old versions are saved in git at commit `23795fe`. To restore all 3 files:

```bash
git checkout 23795fe -- alpha/notifications/tasks.py config/settings/base.py docker-compose.production.yml
docker compose -f docker-compose.production.yml up -d --build
```

To roll back only one part, run the `git checkout 23795fe -- <file>` line for just that file.
Example: keep the auto-restart but go back to the old reminder logic:

```bash
git checkout 23795fe -- alpha/notifications/tasks.py config/settings/base.py
```

No database migrations were added, so rolling back needs no database changes.
When celerybeat restarts, the beat schedule in the database goes back to hourly by itself.

---

# Part 2 — Slow appointments / visits pages

## The problem

The appointments list, the visits list (and in fact every page) loaded slowly.

**Causes:**
1. **Notification bell on every page** (`alpha/core/context_processors.py`): loaded the last
   50 visits and checked "is it paid?" one by one. Each check ran a separate DB query, so
   **~50 extra queries on every page load**.
2. **Visits list** (`visit_list.html`): every row used `visit.grand_total` (3x) and
   `visit.products_total` (2x), and each use ran its own query, so **~6 queries per visit row**.
   1,000 visits came to ~6,000 queries. The totals were already being calculated in the list's
   main query, but the template never used them.

## What changed (3 files)

### 1. `alpha/visits/models.py`
- `Visit.products_total` first checks for a value already calculated in the main query
  (`products_total_db`). If there is one, it uses it with **no extra query**. If not, it works
  exactly as before (other pages are unaffected).
- New helper `annotate_totals(queryset)`: calculates `products_total_db` and `grand_total_db` for
  all visits in one query. This is the same logic as the old `_annotate_grand_total` in views.py,
  moved here so it can be shared.
- New helper `recent_incomplete_visits(limit=10, recent=50)`: the 10 newest unpaid visits among
  the last 50 (same rule as before) in **one query**.

### 2. `alpha/visits/views.py`
- `_annotate_grand_total` now just points to `annotate_totals` (same behaviour).
- `VisitListView` also loads `client_package_item` in the main query (one less query per row).
- `get_incomplete_visits_count` (the bell's AJAX refresh) uses `recent_incomplete_visits()`.

### 3. `alpha/core/context_processors.py`
- `incomplete_visits` uses `recent_incomplete_visits()`: ~50 queries became 1.

**Nothing visible changed:** same pages, same numbers, same bell contents.

## Not done yet (optional next step)

Both lists still render **all** records as HTML and let DataTables page them in the browser.
This is the main remaining slowness on the appointments list. The fix would be server-side
pagination (50 rows per page). The catch is that the search box would then search on the server
instead of only filtering rows already loaded.

## How to check it works

Open the visits list and the appointments list: they should load noticeably faster.
Check that the amounts, the "incl. € products" text, the payment badges and the notification
bell (count + list) show the same values as before.

## How to roll back

```bash
git checkout 23795fe -- alpha/visits/models.py alpha/visits/views.py alpha/core/context_processors.py
docker compose -f docker-compose.production.yml up -d --build
```

No database migrations were added, so rolling back needs no database changes.

---

# Roll back everything (Part 1 + Part 2)

```bash
git checkout 23795fe -- alpha/notifications/tasks.py config/settings/base.py docker-compose.production.yml alpha/visits/models.py alpha/visits/views.py alpha/core/context_processors.py
docker compose -f docker-compose.production.yml up -d --build
```
