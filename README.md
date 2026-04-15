# Jaunpur Footwear Shop

A Django template-based footwear e-commerce project for shoes, slippers, sandals and local shop products.

## Features

### Customer Side
- Home page
- Product listing
- Product search
- Brand/category/size filter
- Product detail page
- Add to cart
- Checkout
- My orders
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