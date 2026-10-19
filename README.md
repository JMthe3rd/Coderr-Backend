# Coderr Backend

Django REST Framework backend for the Developer Akademie Coderr marketplace.

## Current scope

All 23 documented method/route combinations are implemented: registration,
login, profiles, offers, packages, orders, reviews and platform statistics.
The core frontend workflow and local checklist checks have passed. See
[the verification report](docs/VERIFICATION.md) for evidence and the remaining
external PM-test and GitHub publication requirements. See
[the implementation plan](docs/PLAN.md) for the full endpoint matrix,
data model, checklist and unresolved specification details.

## Local setup

Use Python 3.13. Run these commands from the Coderr directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

On Windows, activate with `.venv\Scripts\Activate.ps1` in PowerShell.
For runtime dependencies only, install `requirements.txt`.

The API runs at `http://127.0.0.1:8000/api/` and Django admin at
`http://127.0.0.1:8000/admin/`. Staff accounts created with createsuperuser
have no marketplace profile by default; create one in admin if required.

## Authentication

POST `/api/registration/` with JSON:

```json
{
  "username": "example_user",
  "email": "example@example.com",
  "password": "Secure-Coderr-729!",
  "repeated_password": "Secure-Coderr-729!",
  "type": "customer"
}
```

Supported types: `customer`, `business`. Passwords must satisfy Django's
configured password validators. POST `/api/login/` with `username` and
`password`. Both return `token`, `username`, `email` and `user_id`.
Use `Authorization: Token YOUR_TOKEN` for future protected endpoints.

## Profiles

Authenticated users can read `GET /api/profile/{user_id}/` and the unpaginated
lists `GET /api/profiles/business/` and `GET /api/profiles/customer/`.
Only the owner can `PATCH /api/profile/{user_id}/` (including for staff).
Editable fields: `first_name`, `last_name`, `email`, `location`, `tel`,
`description`, `working_hours` and `file`. Unspecified fields remain unchanged.
Username, role, user ID and creation time are read-only. Profile lookup uses
user IDs rather than profile primary keys. Optional text fields return empty
strings; an absent profile image returns null.

Send text updates as JSON. Upload `file` using multipart form data. Only valid
JPEG, PNG and WebP images up to 5 MB are accepted. The upload timestamp is
recorded when the file field changes. Send `{"file": null}` as JSON to clear
the image reference. Replaced or cleared files remain on disk; automatic
orphan-file cleanup is not yet implemented. Uploaded media is served locally
under `/media/`. Profile lists omit email; authenticated detail responses
include email as specified by the course API.

## Offers

| Method | Route | Access |
| --- | --- | --- |
| GET | `/api/offers/` | Public, paginated |
| POST | `/api/offers/` | Business accounts |
| GET | `/api/offers/{id}/` | Authenticated accounts |
| PATCH, DELETE | `/api/offers/{id}/` | Offer creator |
| GET | `/api/offerdetails/{id}/` | Authenticated accounts |

Creation requires `title`, `description` and exactly three `details`, one each
with `offer_type` set to `basic`, `standard` and `premium`. Each package needs
`title`, `revisions`, `delivery_time_in_days`, `price` and a `features` list.
Revisions allow -1 (unlimited) or nonnegative integers. Delivery is at least
one day; prices are nonnegative decimal values with at most two decimal places.
Price accepts JSON numbers or decimal strings and is returned as a JSON number.
Ownership always comes from authentication.

PATCH may update only some fields and only some packages. Every submitted
package needs its `offer_type`; existing package IDs and unspecified data are
preserved. If an `id` is submitted, it must match the existing package tier.
Parent and package writes are transactional. Reads contain package links;
POST and PATCH return the complete nested package data.

List query parameters: `creator_id`, `min_price`, `max_delivery_time`, `search`
(title and description), `ordering` (`updated_at`, `min_price`, optionally
prefixed with `-`), `page` and `page_size`. Price and delivery filters use the
minimum across an offer's packages. Default page size is 6; permitted explicit
sizes are 1 through 100. Numeric filter errors return 400; an unavailable page
returns 404. Filters only apply to the list, not individual object routes.

Send JSON for ordinary writes. To include an `image`, use multipart form data
with `details` encoded as a JSON string. Images follow the profile upload
rules (JPEG, PNG, WebP, at most 5 MB). An image can be cleared with JSON
`{"image": null}`. Old files currently remain on disk after replacement,
clearing or offer deletion. Offers and packages are editable in Django admin;
admin forms do not replace API validation and permissions.

## Orders

| Method | Route | Access |
| --- | --- | --- |
| GET | `/api/orders/` | Authenticated; only orders where the user is a participant |
| POST | `/api/orders/` | Customer accounts |
| PATCH | `/api/orders/{id}/` | The order's business participant |
| DELETE | `/api/orders/{id}/` | Staff accounts, including unrelated staff |
| GET | `/api/order-count/{business_user_id}/` | Authenticated |
| GET | `/api/completed-order-count/{business_user_id}/` | Authenticated |

Create a purchase using `{"offer_detail_id": 1}`. The server derives the
customer from authentication and the business from the selected package's offer.
Title, revisions, delivery time, price, features and package tier are copied
into a purchase snapshot. These terms survive edits or deletion of the source
offer. Forged purchase terms, participant IDs and initial status are ignored.
An order starts with status `in_progress`; repeated purchases are permitted.
A malformed package ID returns 400 and a nonexistent package returns 404.

The unpaginated order list includes only purchases involving the authenticated
user, including for staff. Staff may delete unrelated orders but do not gain
a global list or status-editing rights. PATCH must contain only `status`, with
one of `in_progress`, `completed` or `cancelled`. Other or missing fields return
400; customers and unrelated businesses cannot update status. No extra status
transition restrictions are imposed by the current course specification.
Single-order GET and full replacement with PUT are not exposed.

Counters return `order_count` for running orders and `completed_order_count`
for completed orders of the specified business. Cancelled orders are excluded.
An existing business with no orders returns zero; missing accounts and
non-business accounts return 404. Counts reflect status changes immediately.

In admin, staff can inspect purchased terms and edit status; creation is
available through the API. Purchase fields remain read-only in admin.
Deleting a source offer preserves orders. Deleting a participating user
currently cascades to that user's orders.

## Reviews and platform statistics

| Method | Route | Access |
| --- | --- | --- |
| GET | `/api/reviews/` | Authenticated accounts; unpaginated list |
| POST | `/api/reviews/` | Customer accounts |
| PATCH, DELETE | `/api/reviews/{id}/` | Review author only, without staff override |
| GET | `/api/base-info/` | Public |

Create a review with `business_user` (an existing business user's account ID),
`rating` (an integer from 1 to 5) and nonempty `description`. The server derives
`reviewer` from authentication; a submitted reviewer ID is ignored. A prior
order is not required by the course API. Only one review per customer/business
pair is permitted. A database uniqueness constraint protects simultaneous
submissions; duplicate pairs return 403. Invalid fields or a non-business target
return 400. After deleting a review, its author may create a fresh review.

PATCH accepts `rating`, `description` or both. Empty updates, invalid ratings,
empty descriptions and attempts to change business or author return 400.
The review list supports `business_user_id`, `reviewer_id` and `ordering`
(`updated_at` or `rating`, optionally prefixed with `-`). Account filters can
be combined; malformed account IDs return 400. GET on a single review and
full replacement with PUT are not exposed. Reviews are manageable in admin;
API author-only permissions do not apply to Django admin's staff permissions.

The specification inconsistently mentions 400 and 403 for duplicates and an
admin override for PATCH. This implementation follows its explicit duplicate
403 entry and author-only permission rule. The rating scale is implemented as
1 through 5; the supplied endpoint text does not explicitly state its bounds.

`/api/base-info/` returns `review_count`, `average_rating`,
`business_profile_count` and `offer_count`. The average includes all reviews
and is rounded to one decimal, returning 0.0 when no reviews exist. The other
fields return zero on an empty database. Statistics reflect review changes
and deletion immediately.

## Verification

```bash
python manage.py check
python manage.py test
python -m coverage run manage.py test
python -m coverage report -m
python -m coverage html
python manage.py makemigrations --check --dry-run
python -m ruff check .
python -m ruff format --check .
```

The local suite has 97 passing tests. Combined statement/branch coverage is
98.67% (displayed as 99% by coverage.py): 663/670 statements and 79/82 branches.
The committed `.coveragerc` measures all five application/project packages,
excluding tests and migrations, and requires at least 95%. HTML output is saved
to `htmlcov/index.html` and is excluded from Git. These local results do not
confirm the course PM tests or their separate required 95% coverage.

## Frontend and development settings

Keep the course frontend separate from this backend repository. Local CORS
origins are `http://localhost:5500` and `http://127.0.0.1:5500`.
KanMind also uses port 8000; stop it before starting Coderr on that port.
The tested frontend is available separately at:
https://github.com/Developer-Akademie-Backendkurs/project.Coderr

To run it in a separate terminal from its own directory:

```bash
python3 -m http.server 5500 --bind 127.0.0.1
```

Open `http://127.0.0.1:5500/`. The supplied `shared/scripts/config.js` already
uses `http://127.0.0.1:8000/api/`; no frontend edits were needed. Registration
for both roles, profile editing/image upload, offer creation/editing, search,
purchasing, customer/business order views, status updates, review creation/
editing and homepage statistics were manually verified. Filter/pagination,
deletions and invalid-input/access-control scenarios also have API tests;
not every combination was repeated in the browser.

Fresh installations contain no demo accounts. The frontend guest-login button
uses hardcoded credentials for accounts that must exist separately; this
backend does not seed those accounts. Use registration for normal local tests.
The integration run left synthetic accounts `integration_business` and
`integration_customer`, one offer, one completed order and one review in the
local database. These records and the uploaded avatar are not part of Git.

SQLite and uploaded media stay local and are excluded from Git. Migrations
are tracked. DEBUG, the fallback secret key and local media serving are for
local development. Public deployment is outside the current setup.
