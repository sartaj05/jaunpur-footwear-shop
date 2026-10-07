# Jaunpur Footwear Marketplace

A Django marketplace prototype focused on footwear shops in Jaunpur, Uttar Pradesh. Customers can browse local catalogs, check size and color availability, place orders, and follow fulfillment. Sellers can manage shop catalogs and local orders, while staff review sellers and oversee marketplace operations.

> **Project status:** The repository contains working Django features and automated tests, but a real public launch still needs production hosting, provider credentials, operational checks, and broader end-to-end validation. Amazon, Flipkart, Razorpay, WhatsApp, and ONDC capabilities depend on the setup and approvals described below.

## Feature map

The [feature catalog](docs/Jaunpur_Footwear_Feature_Catalog.docx) groups the current application into 25 documented capability areas across customers, sellers, staff/platform operations, and marketplace workflows.

### Customers

- Browse and search footwear; filter by brand, category, and size, including English/Hindi catalog matches.
- View Jaunpur shop storefronts, delivery PIN-code coverage, fees, delivery estimates, and available fulfillment slots.
- Manage a cart with size/color variants, apply coupons, and choose Cash on Delivery or configured Razorpay checkout.
- Save up to ten customer delivery addresses, select one at checkout, and validate delivery against each Jaunpur shop's PIN-code coverage.
- Reserve stock for a configurable payment window (15 minutes by default); Celery Beat cancels expired unpaid Razorpay orders and releases stock.
- Use wishlists and the shoe-size finder; submit product reviews and eligible delivered-shop reviews.
- View orders and status timelines, download a personal order receipt PDF, and request returns or exchanges.
- Request cancellation before shop fulfillment starts and follow staff review plus externally recorded refund progress.
- Receive email status updates and opt-in English/Hindi WhatsApp updates when Meta Cloud API settings are configured.
- Open order-linked customer support tickets and exchange messages with staff.
- Earn Jaunpur loyalty points and use eligible reward coupons.

### Local sellers

- Apply to sell; staff review the application and shop details before approval and verification.
- Maintain a Jaunpur storefront, shop hours/contact details, PIN-code coverage, local delivery fees, and fulfillment slots.
- Manage products, size/color stock, seller SKUs, inventory movements, low-stock thresholds, and reorder suggestions.
- Import a catalog from CSV with product photos; map eligible catalog items to marketplace categories/listings.
- Review shop-specific orders created when checkout contains items from multiple shops.
- Use pickup or local delivery workflows; staff can group rider routes by PIN cluster and record proof of delivery.
- Review shop commission statements and payouts recorded by staff.

### Staff and operations

- Django admin and staff dashboards for seller approval, catalog, order status, customers, stock alerts, sales reports, and production operations alerts.
- Scheduled operations checks for failed jobs and payment webhooks, manual refund review, backup freshness, and recorded database/media restore drills. Configure backup path and alert email recipients in deployment settings.
- Staff-only sales CSV export, staff action audit records, and visible background job run outcomes.
- Customer returns/exchanges, support tickets, seller verification, commissions, and payout oversight.
- Razorpay webhook verification with signature checks and duplicate-event protection; eligible received-return refunds can be queued for staff review.
- Health endpoint at `/health/` and structured console logging.

### Marketplace and network workflows

- Amazon and Flipkart seller setup requests, authorization flows, encrypted seller-token storage, and channel catalog/order workflows for authorized accounts.
- Shared inventory reservations and a unified seller order inbox for supported Jaunpur, Amazon, and Flipkart flows.
- Seller-uploaded marketplace settlement CSV reconciliation with seller-scoped order matching and row review history.
- ONDC Seller Network Participant onboarding details, catalog snapshot handoff, and a configurable connection-check adapter hook.

**Integration boundaries:** Amazon and Flipkart actions require registered apps, authorized seller accounts, API access, and the configured credentials/roles. The settlement import is seller-uploaded; it does not fetch statements automatically. The ONDC adapter checks a configured participant connection; it does not implement live ONDC catalog, stock, order, or settlement synchronization. WhatsApp sends only for opted-in customers with an approved Meta template. Razorpay online payments need API keys and a configured webhook.

## Technology

| Area | Technologies used in this repository |
| --- | --- |
| Application | Python 3.11 in CI, Django 5.2 |
| Web UI | Django templates, HTML, CSS, JavaScript |
| Data | Django ORM and migrations; SQLite for local development; PostgreSQL for production |
| API | Django REST Framework; read-only product/shop endpoints and authenticated customer orders |
| Background work | Celery with Redis; inline task execution in local development |
| Files and documents | Pillow image handling, S3-compatible production media storage, ReportLab order receipts |
| Integrations | Razorpay, Meta WhatsApp Cloud API, Amazon SP-API, Flipkart seller APIs, ONDC participant adapter |
| Quality | Django tests and GitHub Actions checks for configuration, migration drift, and tests |

This application is server-rendered Django. React and FastAPI are skills the maintainer is learning; neither is part of this repository's stack.

## Local setup

Requirements: Python 3.11 or newer in the supported Django 5.2 range, Git, and PowerShell on Windows (or equivalent shell commands on another OS).

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open `http://127.0.0.1:8000/`. Local defaults use SQLite and do not require an `.env` loader. `.env.example` lists configuration names for reference; Django does not automatically load that file. Set optional variables in the shell or your deployment's secret/environment settings. For example:

```powershell
$env:RAZORPAY_KEY_ID = "rzp_test_your_key_id"
$env:RAZORPAY_KEY_SECRET = "your_test_key_secret"
python manage.py runserver
```

The first-party API endpoints are `/api/v1/products/`, `/api/v1/shops/`, and authenticated `/api/v1/my/orders/`. Product search accepts `?q=...`; collection responses are paginated.

## Checks and tests

Run Django's configuration and migration checks, then the test suite:

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

GitHub Actions runs these checks on pushes and pull requests to `main` and `sartaj`. Existing tests cover selected checkout, webhook, refund, API access, seller review, Hindi search, support, settlement import, health, and audit flows. They are a useful base, not proof that every real-provider or production scenario has been verified.

## Production setup overview

Production settings activate with `DJANGO_ENV=production` and require a strong `DJANGO_SECRET_KEY`, exact `DJANGO_ALLOWED_HOSTS`, `DJANGO_DATABASE_URL` pointing to PostgreSQL, `CELERY_BROKER_URL`, and an S3-compatible media bucket. Configure trusted HTTPS origins, provider credentials, static-file serving, logging, database/media backups, and a production WSGI/ASGI server. `runserver` is for development only. A production WSGI server is not currently listed in `requirements.txt`; add and pin the server selected for your hosting platform before deployment.

At minimum, validate the production configuration with:

```powershell
python manage.py check --deploy
python manage.py showmigrations
python manage.py migrate
python manage.py collectstatic --noinput
```

Run a Celery worker and scheduler as separate managed processes when background jobs are enabled:

```powershell
celery -A footwear worker -l INFO
celery -A footwear beat -l INFO
```

The scheduler must be running for expired online-payment reservations to be processed automatically. Set `ORDER_STOCK_RESERVATION_MINUTES` to a positive number of minutes to change the default window.

See [`docs/production-operations.md`](docs/production-operations.md) for operations and backup notes, and the generated [deployment and setup guide](output/pdf/Jaunpur_Footwear_Deployment_Setup.pdf) for the environment checklist and release sequence.

## Launch recommendation

The current scope is sufficient for a strong portfolio demo and Django interview discussion. For a public Jaunpur pilot, focus on a small number of verified shops and validate the complete customer-to-delivery path before expanding: production security, PostgreSQL backups and restore, race-safe stock handling, payment/webhook reconciliation, support and return operations, and real-device smoke checks. Do not wait for every roadmap feature before applying for jobs.

The feature catalog, prioritised roadmap, and interview preparation are available in `docs/`:

- [Feature catalog](docs/Jaunpur_Footwear_Feature_Catalog.docx)
- [Upcoming feature roadmap](docs/Jaunpur_Footwear_Roadmap.docx)
- [Interview preparation for a 2.3+ year Python/Django profile](docs/Jaunpur_Footwear_Interview_Prep.docx)

## Maintainer

Sartaj — Python and Django developer with 2.3+ years of experience (as provided by the maintainer). Keep personal experience claims, production metrics, and deployment statements aligned with verifiable work.
