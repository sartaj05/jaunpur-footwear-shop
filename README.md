# Jaunpur Footwear Marketplace

A Jaunpur-first, multi-seller footwear marketplace built with Django. Customers discover local shops, check shoe size/color availability, place orders and follow fulfillment. Sellers manage catalogs and local orders; staff review shops and coordinate operations.

> **Repository status:** Strong portfolio/interview project after a short walkthrough and accurate explanation of integration boundaries. A public launch still needs a pinned production WSGI server, staging deployment, tested backup/restore, provider rehearsal and operational ownership.

## Why this project stands out

- Local marketplace workflows for Jaunpur shops, delivery PIN coverage, pickup and local delivery.
- Multi-seller checkout, variants, shared stock reservations, seller-specific orders and audited payout batches.
- Reliability work with transactions, expiring payment reservations, webhook verification, health checks and scheduled checks.
- Interview depth in Django data boundaries, PostgreSQL row locks, Celery tasks, APIs and failure handling.
- Clear distinction between application workflows and external-provider approval.

## Current capabilities

- Search, product variants, coupons, wishlists, reviews, loyalty rewards and English/Hindi storefront.
- Customer address book, Jaunpur coverage validation, COD and configured Razorpay checkout.
- Shop pages, delivery estimates/fees, fulfillment slots, pickup/local delivery, order timeline, receipt and support.
- Seller approval/verification, CSV catalog import, stock movement, low-stock alerts, service measures and sales summaries.
- Rider route grouping, delivery status and proof workflow with offline queue/sync while the route view is open.
- Staff order/refund review, operations checks, audit records, reports and payout batch review.
- DRF APIs, Celery jobs, authorized marketplace catalog/order workflows, settlement CSV and ONDC adapter hook.

The [feature catalog](docs/Jaunpur_Footwear_Feature_Catalog.docx) lists the 25 grouped capability areas and their maturity.

## Integration boundaries

- Razorpay needs API keys and a verified webhook before live online payment.
- Amazon and Flipkart need eligible applications, seller authorization and provider access.
- ONDC includes participant onboarding and an adapter hook, not complete live network sync.
- Payout batches record settlement work; bank funds are not transferred automatically.
- WhatsApp needs approved Meta configuration and customer opt-in.

## Technology

| Layer | Stack |
| --- | --- |
| Backend | Python 3.11 in CI, Django 5.2 |
| UI | Django templates, HTML, CSS, JavaScript |
| Data | SQLite locally; PostgreSQL in production settings |
| API and jobs | Django REST Framework, Celery, Redis |
| Files | Pillow, S3-compatible media storage, ReportLab receipts |
| Quality | Django tests, GitHub Actions checks, migrations, health endpoint |

This is a server-rendered Django app. React and FastAPI are skills the maintainer is learning, not the stack used here.

## Local setup

Requirements: Python 3.11 and Git. In PowerShell:

    py -3.11 -m venv .venv
    ./.venv/Scripts/Activate.ps1
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
    python manage.py migrate
    python manage.py createsuperuser
    python manage.py runserver

Open http://127.0.0.1:8000/. Local defaults use SQLite. .env.example is a reference only; Django does not load it automatically. Set environment variables in your shell or deployment platform. Never commit real credentials.

## API routes

- GET /api/v1/products/ - paginated catalog; supports ?q= search.
- GET /api/v1/shops/ - paginated Jaunpur shops.
- /api/v1/my/orders/ - authenticated customer’s own orders.
- /health/, /sitemap.xml, /robots.txt - service and public metadata routes.

## Checks and tests

    python manage.py check
    python manage.py makemigrations --check --dry-run
    python manage.py test

On 8 October 2026 these checks passed and all 37 tests passed. Tests cover selected checkout, webhook, refund, API, seller, support, settlement, health and audit flows; they do not cover every external-provider or production scenario.

## End-to-end and stress checks

A focused local rehearsal ran 500 GET requests across storefront/catalog, shop/area, APIs, health, sitemap and robots routes; all returned HTTP 200. With 25 virtual clients on local runserver and SQLite, it measured about 41.2 requests/second, p50 182 ms, p95 1,825 ms and max 2,457 ms.

A separate PostgreSQL checkout rehearsal submitted 12 simultaneous synthetic checkouts for 12 stock units; all 12 completed and their carts cleared. It exposed a lock error caused by selecting nullable joined relations for update; the query now locks cart rows and locks each stock owner explicitly. No real customers or payment provider were involved. These are local regression results, not a production capacity guarantee.

## Production status

Production settings require DJANGO_ENV=production, DJANGO_DEBUG=false, DJANGO_SECRET_KEY, exact DJANGO_ALLOWED_HOSTS, PostgreSQL DJANGO_DATABASE_URL, CELERY_BROKER_URL and S3-compatible media by default. Configure HTTPS, CSRF trusted origins, secrets, static serving, backups, logs and provider credentials.

runserver is development-only. A production WSGI server is not pinned in requirements.txt; add the server and host start command before deployment. Run check --deploy, migrate, collectstatic and rehearse restore/payment flows in staging.

Read the [deployment guide](docs/Jaunpur_Footwear_Deployment_Setup.docx), [roadmap](docs/Jaunpur_Footwear_Roadmap.docx), [interview guide](docs/Jaunpur_Footwear_Interview_Prep.docx) and [operations notes](docs/production-operations.md).

## Launch and job-search recommendation

The project is sufficient for a strong portfolio/interview story; you do not need every future feature before applying. Close production, backup/restore, concurrency, payment reconciliation, monitoring and seller-support gates before a live pilot. Start the 2-3 month job search now while practicing Python, Django, SQL and the project walkthrough.

When comparing 40+ GitHub projects, score working demo, technical depth, test evidence, README clarity and explainable ownership. Select 3-4 complementary projects; do not list all projects just because they exist.
