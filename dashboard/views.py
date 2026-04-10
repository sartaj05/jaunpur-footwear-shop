from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.shortcuts import render, redirect, get_object_or_404

from products.models import Product, Brand, Category
from orders.models import Order


@staff_member_required
def superadmin_dashboard(request):
    context = {
        'total_products': Product.objects.count(),
        'total_brands': Brand.objects.count(),
        'total_categories': Category.objects.count(),
        'total_orders': Order.objects.count(),
        'total_customers': User.objects.filter(is_staff=False).count(),
        'low_stock_products': Product.objects.filter(stock__lte=5).count(),
        'recent_orders': Order.objects.select_related('user').order_by('-created_at')[:8],
    }
    return render(request, 'dashboard/superadmin_dashboard.html', context)


@staff_member_required
def dashboard_brands(request):
    brands = Brand.objects.all().order_by('name')
    return render(request, 'dashboard/brands.html', {'brands': brands})


@staff_member_required
def add_brand(request):
    if request.method == 'POST':
        Brand.objects.create(
            name=request.POST.get('name'),
            logo=request.FILES.get('logo')
        )
        return redirect('dashboard_brands')

    return render(request, 'dashboard/brand_form.html', {'brand': None})


@staff_member_required
def edit_brand(request, pk):
    brand = get_object_or_404(Brand, pk=pk)

    if request.method == 'POST':
        brand.name = request.POST.get('name')

        if request.FILES.get('logo'):
            brand.logo = request.FILES.get('logo')

        brand.save()
        return redirect('dashboard_brands')

    return render(request, 'dashboard/brand_form.html', {'brand': brand})


@staff_member_required
def delete_brand(request, pk):
    brand = get_object_or_404(Brand, pk=pk)
    brand.delete()
    return redirect('dashboard_brands')


@staff_member_required
def dashboard_categories(request):
    categories = Category.objects.all().order_by('name')
    return render(request, 'dashboard/categories.html', {'categories': categories})


@staff_member_required
def add_category(request):
    if request.method == 'POST':
        Category.objects.create(
            name=request.POST.get('name'),
            image=request.FILES.get('image')
        )
        return redirect('dashboard_categories')

    return render(request, 'dashboard/category_form.html', {'category': None})


@staff_member_required
def edit_category(request, pk):
    category = get_object_or_404(Category, pk=pk)

    if request.method == 'POST':
        category.name = request.POST.get('name')

        if request.FILES.get('image'):
            category.image = request.FILES.get('image')

        category.save()
        return redirect('dashboard_categories')

    return render(request, 'dashboard/category_form.html', {'category': category})


@staff_member_required
def delete_category(request, pk):
    category = get_object_or_404(Category, pk=pk)
    category.delete()
    return redirect('dashboard_categories')


@staff_member_required
def dashboard_products(request):
    products = Product.objects.select_related('brand', 'category').order_by('-created_at')
    return render(request, 'dashboard/products.html', {'products': products})


@staff_member_required
def add_product(request):
    brands = Brand.objects.all()
    categories = Category.objects.all()

    if request.method == 'POST':
        Product.objects.create(
            name=request.POST.get('name'),
            brand_id=request.POST.get('brand'),
            category_id=request.POST.get('category'),
            gender=request.POST.get('gender'),
            description=request.POST.get('description'),
            price=request.POST.get('price'),
            discount_price=request.POST.get('discount_price') or None,
            stock=request.POST.get('stock'),
            available_sizes=request.POST.get('available_sizes'),
            image=request.FILES.get('image'),
            is_active=True if request.POST.get('is_active') else False,
            is_featured=True if request.POST.get('is_featured') else False,
        )
        return redirect('dashboard_products')

    return render(request, 'dashboard/product_form.html', {
        'brands': brands,
        'categories': categories,
        'product': None,
    })


@staff_member_required
def edit_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    brands = Brand.objects.all()
    categories = Category.objects.all()

    if request.method == 'POST':
        product.name = request.POST.get('name')
        product.brand_id = request.POST.get('brand')
        product.category_id = request.POST.get('category')
        product.gender = request.POST.get('gender')
        product.description = request.POST.get('description')
        product.price = request.POST.get('price')
        product.discount_price = request.POST.get('discount_price') or None
        product.stock = request.POST.get('stock')
        product.available_sizes = request.POST.get('available_sizes')
        product.is_active = True if request.POST.get('is_active') else False
        product.is_featured = True if request.POST.get('is_featured') else False

        if request.FILES.get('image'):
            product.image = request.FILES.get('image')

        product.save()
        return redirect('dashboard_products')

    return render(request, 'dashboard/product_form.html', {
        'brands': brands,
        'categories': categories,
        'product': product,
    })


@staff_member_required
def delete_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product.delete()
    return redirect('dashboard_products')


@staff_member_required
def dashboard_orders(request):
    orders = Order.objects.select_related('user').order_by('-created_at')
    return render(request, 'dashboard/orders.html', {'orders': orders})


@staff_member_required
def update_order_status(request, pk):
    order = get_object_or_404(Order, pk=pk)

    if request.method == 'POST':
        order.status = request.POST.get('status')
        order.save()

    return redirect('dashboard_orders')


@staff_member_required
def dashboard_customers(request):
    customers = User.objects.filter(is_staff=False).order_by('-date_joined')
    return render(request, 'dashboard/customers.html', {'customers': customers})