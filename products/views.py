from django.shortcuts import render, get_object_or_404
from .models import Product, Brand, Category


def home(request):
    featured_products = Product.objects.filter(is_active=True, is_featured=True)[:8]
    categories = Category.objects.all()
    brands = Brand.objects.all()

    return render(request, 'products/home.html', {
        'featured_products': featured_products,
        'categories': categories,
        'brands': brands,
    })


def product_list(request):
    products = Product.objects.filter(is_active=True)
    brands = Brand.objects.all()
    categories = Category.objects.all()

    search = request.GET.get('search')
    brand = request.GET.get('brand')
    category = request.GET.get('category')
    size = request.GET.get('size')

    if search:
        products = products.filter(name__icontains=search)

    if brand:
        products = products.filter(brand_id=brand)

    if category:
        products = products.filter(category_id=category)

    if size:
        products = products.filter(available_sizes__icontains=size)

    return render(request, 'products/product_list.html', {
        'products': products,
        'brands': brands,
        'categories': categories,
    })


def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk, is_active=True)
    sizes = [s.strip() for s in product.available_sizes.split(',')]
    variants = product.variants.filter(is_active=True)

    return render(request, 'products/product_detail.html', {
        'product': product,
        'sizes': sizes,
        'variants': variants,
    })


def size_finder(request):
    suggested_size = None

    if request.method == 'POST':
        foot_length = float(request.POST.get('foot_length'))

        if foot_length <= 23:
            suggested_size = 'UK/India 5'
        elif foot_length <= 24:
            suggested_size = 'UK/India 6'
        elif foot_length <= 25:
            suggested_size = 'UK/India 7'
        elif foot_length <= 26:
            suggested_size = 'UK/India 8'
        elif foot_length <= 27:
            suggested_size = 'UK/India 9'
        elif foot_length <= 28:
            suggested_size = 'UK/India 10'
        else:
            suggested_size = 'UK/India 11+'

    return render(request, 'products/size_finder.html', {
        'suggested_size': suggested_size
    })
