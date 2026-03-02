# expense_tracker (project config)

Django project configuration module.

## settings.py

- SQLite database at `db.sqlite3` in project root
- Timezone: `Asia/Karachi`
- Tailwind: standalone v4 via `theme` app, `TAILWIND_APP_NAME = "theme"`
- HTMX: `HtmxMiddleware` in middleware stack
- Browser reload: enabled in DEBUG via middleware + URL include
- Project-level templates dir: `BASE_DIR / "templates"`

## urls.py

Root URL configuration:
- `/` → `DashboardView` (core app)
- `/accounts/` → accounts app URLs
- `/transactions/` → transactions app URLs
- `/transfers/add/` → `TransferCreateView` (name: `transfer_create`)
- `/admin/` → Django admin
- `/__reload__/` → browser reload (DEBUG only)
