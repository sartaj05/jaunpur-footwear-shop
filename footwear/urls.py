from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from .health import health_check
from .seo import public_sitemap, robots_txt

urlpatterns = [
    path('health/', health_check, name='health_check'),
    path('sitemap.xml', public_sitemap, name='public_sitemap'),
    path('robots.txt', robots_txt, name='robots_txt'),
    path('api/v1/', include('api.urls')),
    path('admin/', admin.site.urls),

    path('', include('products.urls')),
    path('accounts/', include('accounts.urls')),
    path('orders/', include('orders.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('shops/', include('shops.urls')),
    path('support/', include('support.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
