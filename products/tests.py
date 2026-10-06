from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from .models import Brand, Category, Product


class HindiCatalogSearchTests(TestCase):
    def setUp(self):
        brand = Brand.objects.create(name="Local Shoes")
        category = Category.objects.create(name="Sports Shoes")
        self.product = Product.objects.create(
            name="Everyday Runner",
            name_hi="आरामदायक जूते",
            brand=brand,
            category=category,
            description="Lightweight footwear",
            description_hi="हल्के और आरामदायक जूते",
            price=Decimal("899.00"),
            stock=5,
            available_sizes="7,8,9",
            image="products/everyday-runner.jpg",
        )

    def test_hindi_search_matches_hindi_catalog_text_and_localizes_page(self):
        session = self.client.session
        session["site_language"] = "hi"
        session.save()

        response = self.client.get(reverse("product_list"), {"search": "जूते"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'lang="hi"')
        self.assertContains(response, self.product.name_hi)
        self.assertEqual(list(response.context["products"]), [self.product])

    def test_english_category_term_finds_hindi_named_product(self):
        response = self.client.get(reverse("product_list"), {"search": "shoes"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["products"]), [self.product])
