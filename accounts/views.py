from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from orders.models import Coupon

from .models import CustomerProfile, ReferralCode, ReferralReward


def register_view(request):
    referral_code = request.POST.get('referral_code', '') if request.method == 'POST' else request.GET.get('ref', '')
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email', '').strip()
        mobile = request.POST.get('mobile')
        password = request.POST.get('password')
        address = request.POST.get('address')
        referral = ReferralCode.objects.filter(code__iexact=referral_code.strip()).select_related('user').first() if referral_code.strip() else None

        if referral_code.strip() and not referral:
            return render(request, 'accounts/register.html', {
                'error': 'That Jaunpur referral code is invalid.',
                'referral_code': referral_code,
            })

        if User.objects.filter(username=username).exists():
            return render(request, 'accounts/register.html', {
                'error': 'Username already exists'
            })

        if email and User.objects.filter(email__iexact=email).exists():
            return render(request, 'accounts/register.html', {
                'error': 'An account already uses this email address'
            })

        with transaction.atomic():
            user = User.objects.create_user(username=username, email=email, password=password)
            CustomerProfile.objects.create(
                user=user,
                mobile=mobile,
                address=address,
                city='Jaunpur'
            )
            if referral:
                ReferralReward.objects.create(referrer=referral.user, referred_user=user)
                Coupon.objects.create(
                    code=f'JP-NEW-{user.pk}',
                    discount_type='fixed',
                    discount_value='50.00',
                    usage_limit=1,
                    reserved_for=user,
                    starts_at=timezone.now(),
                    expires_at=timezone.now() + timedelta(days=90),
                )

        if referral:
            messages.success(request, 'Referral accepted. A ₹50 new-customer coupon is reserved for your Jaunpur account.')
        return redirect('login')

    return render(request, 'accounts/register.html', {'referral_code': referral_code})


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user:
            login(request, user)
            return redirect('home')

        return render(request, 'accounts/login.html', {
            'error': 'Invalid username or password'
        })

    return render(request, 'accounts/login.html')


def logout_view(request):
    logout(request)
    return redirect('home')


@login_required
def referrals_view(request):
    referral_code, _ = ReferralCode.objects.get_or_create(user=request.user)
    referrals = request.user.referral_rewards.select_related('referred_user').order_by('-created_at')
    share_url = request.build_absolute_uri(f"{reverse('register')}?ref={referral_code.code}")
    return render(request, 'accounts/referrals.html', {
        'referral_code': referral_code,
        'referrals': referrals,
        'share_url': share_url,
        'personal_coupons': request.user.reserved_coupons.filter(is_active=True).order_by('-id'),
    })
