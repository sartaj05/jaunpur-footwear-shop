# Jaunpur Footwear Shop

A Django template-based footwear e-commerce project for shoes, slippers, sandals and local shop products.

## Features

### Customer Side
- Jaunpur footwear shop applications with staff approval
- Staff-reviewed “Verified Jaunpur Shop” profiles
- Public Jaunpur shop directory and individual storefront pages
- Shop delivery coverage by Jaunpur PIN code
- Seller dashboard for shop-owned product and size/color stock management
- Seller bulk catalog CSV import with matching product-photo uploads
- Stable seller SKUs and marketplace product/category mappings
- One checkout split into shop-specific seller orders with separate progress
- Shop pickup and local delivery appointments with weekly time slots
- Amazon/Flipkart seller setup requests and catalog preparation CSV exports
- Flipkart seller OAuth authorization with encrypted token storage
- Amazon seller consent and LWA authorization-code exchange
- Shared stock reservations across the Jaunpur shop and authorized marketplace channels
- Unified Jaunpur, Amazon, and Flipkart seller order inbox
- Manual marketplace fee and settlement reconciliation records
- ONDC Seller Network Participant onboarding tracker for Jaunpur shops
- Per-shop commission statements and staff-recorded payout ledger
- PIN-code-targeted shop promotions
- Jaunpur loyalty points and personal ₹50 reward coupons
- PIN-clustered local rider routes and proof-of-delivery records
- Home page
- Product listing
- Product search
- Brand/category/size filter
- Product detail page
- Add to cart
- Size/color inventory variants
- Wishlist
- Coupon discounts and PIN-code delivery fees
- Cash on Delivery and Razorpay online checkout
- Customer product ratings and reviews
- My orders
- Order tracking timeline and email updates
- Opt-in English or Hindi WhatsApp order updates (Meta Cloud API configuration required)
- Return and exchange requests
- Customer login/register
- Shoe size finder
- WhatsApp order support

### Superadmin Dashboard
- Separate dashboard
- Add/edit/delete products
- Manage orders
- Update order status
- View customers
- Low stock alert
- Featured products
- Sales reports

## Tech Stack

- Python
- Django
- HTML
- CSS
- JavaScript
- SQLite
- Bootstrap Icons optional

## Project Setup

```bash
python -m venv venv
venv\Scripts\activate

pip install django pillow cryptography

python manage.py makemigrations
python manage.py migrate

python manage.py createsuperuser
python manage.py runserver
```

## Razorpay Setup

Online checkout is available after setting Razorpay API keys in the environment. Use test keys while developing; never commit your secret key.

PowerShell:

```powershell
$env:RAZORPAY_KEY_ID = "rzp_test_your_key_id"
$env:RAZORPAY_KEY_SECRET = "your_test_key_secret"
python manage.py runserver
```

Without these keys, Cash on Delivery remains available and online checkout is disabled.

## Flipkart Seller Authorization

After the Jaunpur Footwear admin approves a shop's Flipkart setup request, the shop owner can authorize that seller account from **Amazon and Flipkart setup**. Configure a registered Flipkart partner app and use this exact callback URL for the app and `FLIPKART_REDIRECT_URI`:

```text
https://your-domain.example/seller/marketplaces/flipkart/callback/
```

Set these environment values on the server:

```text
FLIPKART_CLIENT_ID
FLIPKART_CLIENT_SECRET
FLIPKART_REDIRECT_URI
MARKETPLACE_TOKEN_ENCRYPTION_KEY
```

Generate a Fernet key once with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`. Keep the same key in a secret manager across deploys and back it up securely; changing it makes previously stored marketplace tokens unreadable. Seller tokens are encrypted before they are stored. Flipkart partner app access and each seller's authorization are required. This connection implements seller authorization and token storage; catalog and order API sync is a separate workflow. See the [Flipkart Seller API documentation](https://seller.flipkart.com/api-docs/FMSAPI.html).

## Amazon Seller Authorization

An approved seller can enter the Amazon marketplace IDs they use and authorize the registered SP-API application. Register this callback URL in the app and set it as `AMAZON_REDIRECT_URI`:

```text
https://your-domain.example/seller/marketplaces/amazon/callback/
```

Configure `AMAZON_APPLICATION_ID`, `AMAZON_LWA_CLIENT_ID`, `AMAZON_LWA_CLIENT_SECRET`, `AMAZON_REDIRECT_URI`, and the shared `MARKETPLACE_TOKEN_ENCRYPTION_KEY` on the server. `AMAZON_AUTHORIZATION_URL` defaults to the India Seller Central consent URL; set it to the Seller Central domain for the target marketplace region. Set `AMAZON_OAUTH_VERSION=beta` only when testing an app in Draft status. Amazon requires SP-API developer/app registration and seller authorization, and public apps may require Amazon approval before sellers can authorize them. The callback exchanges Amazon's authorization code through LWA and encrypts the returned seller tokens. Product, inventory, and order operations are implemented separately. See Amazon's [SP-API onboarding](https://developer-docs.amazon.com/sp-api/docs/onboarding-overview) and [connection guide](https://developer-docs.amazon.com/sp-api/docs/connecting-to-the-selling-partner-api).

## Shared Marketplace Stock and Orders

In the marketplace product catalog, map every sellable size/color SKU and enter the quantity reserved for each channel. The sum of marketplace reservations cannot exceed current stock; Jaunpur storefront checkout can only use the unreserved units. When a channel order is imported, the matching shared stock and that channel's reservation are reduced. Unmapped SKUs and stock shortages are shown in the order inbox.

Flipkart inventory sync also needs the seller's fulfillment location ID and each listing's Flipkart product ID. Amazon shared-stock sync currently supports one Amazon marketplace ID per connection and seller-fulfilled listings. The Amazon connection needs approved Orders and listing API roles. Select **Sync orders and reserved stock now** in the marketplace hub, or run this command from a scheduled job:

```powershell
python manage.py sync_marketplace_channels
python manage.py sync_marketplace_channels --shop-id 12 --channel amazon
```

Set `AMAZON_SP_API_ENDPOINT` for the seller's SP-API region. The default points at Amazon's EU endpoint used for Jaunpur's India marketplace. `FLIPKART_API_BASE_URL` defaults to `https://api.flipkart.net/sellers`. Seller API access and approval are required. The order inbox stores no Amazon or Flipkart buyer contact/address fields. Fees and settlements are entered from marketplace statements in the inbox; this release does not import settlement reports automatically. The Amazon order importer uses the current [Orders API v2026-01-01](https://developer-docs.amazon.com/sp-api/reference/searchorders) and the Flipkart [seller order API](https://seller.flipkart.com/api-docs/order-api-docs/OMAPIRef.html).

## WhatsApp Order Updates

WhatsApp messages are sent only when the customer opts in under **Jaunpur rewards & preferences** and the Cloud API settings below are configured. Use an approved WhatsApp message template with three body placeholders for order number, customer name, and order status. The same template must have the selected English and Hindi language variants.

PowerShell:

```powershell
$env:WHATSAPP_GRAPH_API_VERSION = "vXX.X"
$env:WHATSAPP_PHONE_NUMBER_ID = "your_phone_number_id"
$env:WHATSAPP_ACCESS_TOKEN = "your_access_token"
$env:WHATSAPP_ORDER_TEMPLATE = "your_approved_template_name"
python manage.py runserver
```

Get the API version and template approval from your Meta Business account. Never commit the access token. For the official send-message request format, see the [Meta WhatsApp Cloud API documentation](https://developers.facebook.com/docs/whatsapp/cloud-api/overview).

## ONDC Seller Network Participant Onboarding

An approved Jaunpur seller can record its Seller Network Participant and application details from **ONDC seller onboarding**. The Jaunpur admin reviews the participant and confirms whether it supports retail; after the shop profile and catalog pass the readiness checklist, the seller can download a JSON catalog snapshot for manual handoff. Admins can track participant confirmation, catalog export, production approval, and the externally confirmed live status.

This workflow prepares seller information and the catalog handoff. It does not connect to ONDC, submit data to a participant, synchronize inventory/orders, or activate production traffic. Complete participant onboarding, network credentials, and live order/inventory integration with an eligible [ONDC Seller Network Participant](https://www.ondc.org/pages/seller-network-participants.html) before launch. The exported stock is a timestamped snapshot; it must not be treated as live stock synchronization.
