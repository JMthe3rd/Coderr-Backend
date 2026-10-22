# Coderr implementation plan

Source: https://cdn.developerakademie.com/courses/Backend/EndpointDoku/index.html?name=coderr
Retrieved: 2026-10-19. The accompanying JSON preserves request and response examples.

## Endpoint and permission matrix

| Method | Route | Access | Progress |
|---|---|---|---|
| POST | `/api/registration/` | Public | Implemented |
| POST | `/api/login/` | Public | Implemented |
| GET | `/api/profile/{pk}/` | Der Benutzer muss authentifiziert sein. | Implemented |
| PATCH | `/api/profile/{pk}/` | Der Benutzer kann NUR sein eigenes Profil bearbeiten. | Implemented |
| GET | `/api/profiles/business/` | Der Benutzer muss authentifiziert sein. | Implemented |
| GET | `/api/profiles/customer/` | Der Benutzer muss authentifiziert sein. | Implemented |
| GET | `/api/offers/` | Public | Implemented |
| POST | `/api/offers/` | Nur User vom type 'business' dürfen Angebote erstellen | Implemented |
| GET | `/api/offers/{id}/` | Der Benutzer muss authentifiziert sein | Implemented |
| PATCH | `/api/offers/{id}/` | Nur Ersteller des Angebotes können dies verändern. | Implemented |
| DELETE | `/api/offers/{id}/` | Nur Ersteller des Angebotes können dies löschen. | Implemented |
| GET | `/api/offerdetails/{id}/` | Der Benutzer muss authentifiziert sein. | Implemented |
| GET | `/api/orders/` | Der Benutzer muss authentifiziert sein. | Implemented |
| POST | `/api/orders/` | Der Benutzer muss authentifiziert sein und vom typ 'customer' sein. | Implemented |
| PATCH | `/api/orders/{id}/` | Nur ein Benutzer vom typ 'business' kann den Status einer Bestellung aktualisieren. | Implemented |
| DELETE | `/api/orders/{id}/` | Nur Admin-Benutzer (Staff) dürfen Bestellungen löschen. | Implemented |
| GET | `/api/order-count/{business_user_id}/` | Der Benutzer muss authentifiziert sein. | Implemented |
| GET | `/api/completed-order-count/{business_user_id}/` | Der Benutzer muss authentifiziert sein. | Implemented |
| GET | `/api/reviews/` | Jeder authentifizierte Benutzer kann Bewertungen lesen. | Implemented |
| POST | `/api/reviews/` | Nur authentifizierte Benutzer mit einem Kundenprofil dürfen Bewertungen erstellen. Jeder authentifizierte Benutzer kann Bewertungen lesen. | Implemented |
| PATCH | `/api/reviews/{id}/` | Nur der Ersteller der Bewertung darf diese Aktion durchführen. | Implemented |
| DELETE | `/api/reviews/{id}/` | Nur der Ersteller der Bewertung darf diese Aktion durchführen. | Implemented |
| GET | `/api/base-info/` | Public | Implemented |

## Planned data model

- Django User: username, email, password hash, first_name, last_name.
- UserProfile: one-to-one User, role, file, location, tel, description, working_hours, timestamps.
- Offer: business User, title, image, description, timestamps.
- OfferDetail: Offer, title, revisions, delivery_time_in_days, decimal price, features, offer_type. Unique (offer, offer_type). Exactly basic, standard and premium when creating an offer.
- Order: customer User, business User, snapshot of purchased detail fields, status and timestamps. Later offer changes must not change a purchase.
- Review: business User, reviewer User, rating, description, timestamps. Unique (business_user, reviewer).

## Decisions and documentation ambiguities

- Use Django's standard User model for accounts. Profile API identifiers refer to user IDs.
- Optional profile text uses empty strings rather than null.
- Order status changes are restricted to the associated business user. The documentation only explicitly names the business role; object ownership is an additional access-control decision.
- Review PATCH mentions admin in request text but author-only in permissions: follow author-only permissions unless clarified.
- Duplicate review POST lists both 400 and 403: use its explicit duplicate-specific 403 entry, protected by a database uniqueness constraint.
- Customer profile list example includes uploaded_at, while its prose mentions additional business fields: preserve this distinction in dedicated serializers.
- Profile files use ImageField plus image content validation: JPEG, PNG and WebP, maximum 5 MB.
- Password validation uses Django validators. Email uniqueness is not specified and is not currently enforced beyond standard Django User behavior.

## Delivery sequence

1. Foundation, registration and login, including negative tests.
2. Profile API and validated image uploads.
3. Offers and details, transactions, filters and pagination.
4. Order snapshots, permissions and counters.
5. Reviews and public base statistics.
6. Frontend integration, coverage and checklist audit.

## Definition of done

- All documented endpoints and response shapes; explicit permissions and expected status codes.
- Methods/functions at most 14 lines; one responsibility, PEP8, English docstrings.
- ModelSerializer for CRUD; explicit fields; API code under each app/api.
- Usable admin, complete dependencies, English startup README.
- Backend-only repository, migrations tracked, database and media excluded.
- Course PM tests must reach at least 95% coverage; local tests do not establish this result.

## Order implementation notes

- Order endpoints use only the needed DRF mixins with GenericViewSet so that
  single-order GET and PUT are not exposed.
- Purchased package fields are snapshots without a foreign key to OfferDetail;
  deleting an offer therefore cannot remove its historical orders.
- Status PATCH accepts only status; staff deletion is independent of profile.
- No additional status-transition policy is inferred from the three statuses.

## Review and statistics implementation notes

- Review ratings use a 1-to-5 integer scale. This is an implementation decision;
  the supplied endpoint text does not explicitly define the range.
- No prior purchase is required because the API does not specify that rule.
- PATCH permits rating and/or description; review participants are immutable.
- Database uniqueness protects concurrent duplicate submissions, with duplicate
  constraint errors translated to 403 after the failed transaction rolls back.
- Public base statistics live in core/api and aggregate across all reviews.
- All 23 method/route combinations are implemented. Core frontend integration,
  local coverage measurement and the local checklist audit passed. External
  course PM tests and GitHub publication remain pending; see VERIFICATION.md.

## Order lookup and permission precedence

Authenticated PATCH/DELETE requests look up the order first: missing orders
return 404, and existing orders with insufficient write privileges return 403.
Authentication still runs first, so anonymous requests return 401.
