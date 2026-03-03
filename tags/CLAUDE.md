# tags app

Lightweight tagging system for transactions and loans. Two tag types: places (where something happened) and groups (linking related transactions together).

## Model: Tag

- `name` (CharField), `tag_type` (place/group), `color` (optional hex), `description` (optional text), `is_active` (default True), `created_at`
- Unique constraint on `(name, tag_type)`
- `display_color` property returns custom color or fallback: green (#16a34a) for places, purple (#9333ea) for groups
- Ordered by `tag_type, name`
- Soft-delete via `is_active=False` (archive) — archived tags hidden from pickers but visible on existing transactions

## Model: TransactionTag

- `transaction` FK (CASCADE), `tag` FK (PROTECT), `created_at`
- Unique constraint on `(transaction, tag)`
- Related name: `transaction_tags` on both Transaction and Tag

## Model: LoanTag

- `loan` FK (CASCADE), `tag` FK (PROTECT), `created_at`
- Unique constraint on `(loan, tag)`
- Related name: `loan_tags` on both Loan and Tag

## Design

- No ManyToManyField on Transaction/Loan — keeps dependency direction clean (tags app depends on transactions/loans, not reverse)
- `on_delete=PROTECT` on tag FK prevents accidental deletion of tags with associations
- `on_delete=CASCADE` on transaction/loan FK so deleting a transaction removes its tag associations
- No signals needed — tags are saved via helper functions in the views that use them

## Forms

- `TagForm` (ModelForm) — name, tag_type, color (type="color" input), description

## Views

CRUD:
- `TagListView` — all active tags grouped by type (places green, groups purple), with transaction counts
- `TagCreateView` / `TagUpdateView` — standard create/edit forms
- `TagDetailView` — tag metadata + all tagged transactions with totals
- `TagGroupsView` — group tags as cards with total amounts and date ranges
- `TagPlacesView` — place tags ranked by expense spending
- `TagArchiveView` (POST) — sets `is_active=False`

HTMX endpoints:
- `tag_search` — GET `/tags/search/?q=term&tag_type=place|group` → returns matching active tags as clickable items
- `tag_create_inline` — POST `/tags/create-inline/` with name + tag_type → returns new tag chip HTML

## URLs (namespace: `tags`)

- `tags:list` → `/tags/`
- `tags:create` → `/tags/add/`
- `tags:groups` → `/tags/groups/`
- `tags:places` → `/tags/places/`
- `tags:search` → `/tags/search/`
- `tags:create_inline` → `/tags/create-inline/`
- `tags:detail` → `/tags/<pk>/`
- `tags:edit` → `/tags/<pk>/edit/`
- `tags:archive` → `/tags/<pk>/archive/`

## Templates

- `tags/templates/tags/` — list, form, detail, groups, places
- `tags/templates/tags/partials/_tag_search_results.html` — HTMX search dropdown with "Create new" option
- `tags/templates/tags/partials/_tag_chip.html` — colored chip with hidden input + remove button
- `tags/templates/tags/partials/_tag_input_widget.html` — reusable widget included in transaction/transfer/loan forms. Has Place and Group sections, each with HTMX search (300ms debounce), results dropdown, selected chips area, and inline creation. Inline JS for `selectTag`/`removeTag`/`createAndSelectTag` functions.

## Integration Points

- **Transaction views** (`transactions/views.py`): `_save_transaction_tags()` and `_get_tag_context()` helpers handle saving/loading tags. Called from `TransactionCreateView`, `TransactionUpdateView`, `TransferCreateView`.
- **Loan views** (`loans/views.py`): `_save_loan_tags()` and `_get_loan_tag_context()` helpers. Called from `LoanCreateView`, `LoanDetailView`.
- **Transaction filters**: `_apply_transaction_filters()` searches tag names alongside description, and supports `tag` (specific tag ID) and `tag_type` (place/group) filter params. `.distinct()` applied to avoid M2M join duplicates.
- **Transaction list**: `prefetch_related("transaction_tags__tag")` to avoid N+1. Tag chips displayed in description column.
- **Export/import**: `export_data` includes `tags`, `transaction_tags`, `loan_tags`. `import_data` handles them in correct dependency order (backward compatible via `data.get()`).
