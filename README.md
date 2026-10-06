# Jaunpur Footwear Shop

A Django template-based footwear e-commerce project for shoes, slippers, sandals and local shop products.

## Features

### Customer Side
- Jaunpur footwear shop applications with staff approval
- Public Jaunpur shop directory and individual storefront pages
- Shop delivery coverage by Jaunpur PIN code
- Seller dashboard for shop-owned product and size/color stock management
- One checkout split into shop-specific seller orders with separate progress
- Shop pickup and local delivery appointments with weekly time slots
- Amazon/Flipkart seller setup requests and catalog preparation CSV exports
- ONDC Seller Network Participant onboarding tracker for Jaunpur shops
- Per-shop commission statements and staff-recorded payout ledger
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

pip install django pillow

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
