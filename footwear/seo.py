from xml.sax.saxutils import escape

from django.http import HttpResponse
from django.db.models import Q
from django.urls import reverse
from django.utils.text import slugify

from products.models import Product
from shops.models import Shop, ShopCoverage


def public_sitemap(request):
    urls = {
        request.build_absolute_uri(reverse('home')),
        request.build_absolute_uri(reverse('product_list')),
        request.build_absolute_uri(reverse('shop_directory')),
    }
    for shop in Shop.objects.filter(status='approved').only('slug'):
        urls.add(request.build_absolute_uri(reverse('shop_page', kwargs={'slug': shop.slug})))
    products = Product.objects.filter(is_active=True).filter(Q(shop__isnull=True) | Q(shop__status='approved')).only('pk')
    for product in products:
        urls.add(request.build_absolute_uri(reverse('product_detail', kwargs={'pk': product.pk})))
    area_names = ShopCoverage.objects.filter(shop__status='approved', is_active=True).exclude(area_name='').values_list('area_name', flat=True)
    for area_slug in {slugify(name) for name in area_names if slugify(name)}:
        urls.add(request.build_absolute_uri(reverse('shop_area', kwargs={'area_slug': area_slug})))
    entries = ''.join(f'<url><loc>{escape(url)}</loc></url>' for url in sorted(urls))
    return HttpResponse(
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f'{entries}</urlset>',
        content_type='application/xml; charset=utf-8',
    )


def robots_txt(request):
    sitemap_url = request.build_absolute_uri(reverse('public_sitemap'))
    return HttpResponse(f'User-agent: *\nAllow: /\nSitemap: {sitemap_url}\n', content_type='text/plain; charset=utf-8')
