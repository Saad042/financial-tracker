# reports app

Charts, summaries, and data analysis views. No models — reads from transactions, categories, loans.

## Views

- `ReportHubView` — landing page with top 5 spending categories for the current month, loan summary (total lent, outstanding/repaid counts and amounts), recent loans, and navigation cards linking to sub-reports and transaction search.
- `MonthlyBreakdownView` — expense spending by parent category for a selected month. Includes Chart.js donut chart, ranked category table with sub-category expansion, and month-over-month comparison bar chart. Month navigation via `?month=YYYY-MM`.
- `TrendsView` — income vs expense line chart over time. Range selector: 3, 6, or 12 months via `?months=N`. Chart.js line chart with income (green), expenses (red), net (dashed gray).

## Shared Helpers

- `_parse_month(request)` — parses `?month=YYYY-MM` from query string, defaults to current month. Same pattern as `budgets/views.py`.
- `_DecimalEncoder` / `_json()` — JSON serializer for passing Decimal values to Chart.js in templates.

## URLs (namespace: `reports`)

- `reports:hub` → `/reports/`
- `reports:monthly` → `/reports/monthly/`
- `reports:trends` → `/reports/trends/`

## Charts

Chart.js v4 loaded via CDN (`{% block extra_js %}`) only on report templates, not globally. Chart data is passed as JSON-serialized context variables using the `|safe` filter.

## Templates

- `reports/templates/reports/report_hub.html` — hub with summary cards
- `reports/templates/reports/monthly_breakdown.html` — donut + bar charts + category table
- `reports/templates/reports/trends.html` — line chart with range selector

## Notes

- Uses `python-dateutil` (`relativedelta`) for month arithmetic.
- No models in this app — all data comes from `transactions.models` and `loans.models`.
