from datetime import timedelta
import re
import secrets

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from orders.models import Coupon

from .models import CustomerAddress, CustomerProfile, LoyaltyAccount, LoyaltyTransaction, ReferralCode, ReferralReward


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


@login_required
def customer_preferences(request):
    profile, _ = CustomerProfile.objects.get_or_create(user=request.user, defaults={'mobile': ''})
    loyalty_account, _ = LoyaltyAccount.objects.get_or_create(user=request.user)
    if request.method == 'POST' and request.POST.get('action') == 'save_preferences':
        pincode = request.POST.get('pincode', '').strip()
        mobile = request.POST.get('mobile', '').strip()
        if pincode and not re.fullmatch(r'[1-9][0-9]{5}', pincode):
            messages.error(request, 'Enter a valid six-digit Jaunpur-area PIN code or leave it blank.')
        elif mobile and not re.fullmatch(r'[+0-9 ()-]{10,18}', mobile):
            messages.error(request, 'Enter a valid phone number.')
        else:
            profile.pincode = pincode
            profile.mobile = mobile
            profile.preferred_language = request.POST.get('preferred_language', 'en') if request.POST.get('preferred_language') in ('en', 'hi') else 'en'
            profile.email_order_updates = request.POST.get('email_order_updates') == 'on'
            profile.whatsapp_order_updates = request.POST.get('whatsapp_order_updates') == 'on'
            profile.save(update_fields=[
                'pincode', 'mobile', 'preferred_language', 'email_order_updates', 'whatsapp_order_updates',
            ])
            if pincode:
                request.session['delivery_pincode'] = pincode
            else:
                request.session.pop('delivery_pincode', None)
            request.session['site_language'] = profile.preferred_language
            messages.success(request, 'Your Jaunpur delivery and WhatsApp preferences were saved.')
            response = redirect('customer_preferences')
            response.set_cookie(settings.LANGUAGE_COOKIE_NAME, profile.preferred_language, max_age=60 * 60 * 24 * 365, samesite='Lax')
            return response
    elif request.method == 'POST' and request.POST.get('action') == 'redeem_points':
        with transaction.atomic():
            loyalty_account = LoyaltyAccount.objects.select_for_update().get(pk=loyalty_account.pk)
            redeem_points = 100
            if loyalty_account.points < redeem_points:
                messages.error(request, 'You need 100 Jaunpur points to claim a ₹50 coupon.')
            else:
                coupon_code = f'JP-LOY-{request.user.pk}-{secrets.token_hex(3).upper()}'
                Coupon.objects.create(
                    code=coupon_code,
                    discount_type='fixed',
                    discount_value='50.00',
                    usage_limit=1,
                    reserved_for=request.user,
                    starts_at=timezone.now(),
                    expires_at=timezone.now() + timedelta(days=90),
                )
                loyalty_account.points -= redeem_points
                loyalty_account.save(update_fields=['points', 'updated_at'])
                LoyaltyTransaction.objects.create(
                    account=loyalty_account,
                    transaction_type='redeemed',
                    points=redeem_points,
                    coupon_code=coupon_code,
                    note='Redeemed for a ₹50 Jaunpur Footwear coupon',
                )
                messages.success(request, f'Coupon {coupon_code} is ready. It is reserved for your account for 90 days.')
                return redirect('customer_preferences')
    return render(request, 'accounts/preferences.html', {
        'profile': profile,
        'loyalty_account': loyalty_account,
        'loyalty_transactions': loyalty_account.transactions.all()[:20],
        'personal_coupons': request.user.reserved_coupons.filter(is_active=True).order_by('-id'),
    })


@login_required
def address_book(request):
    addresses = CustomerAddress.objects.filter(user=request.user)
    if request.method == 'POST':
        action = request.POST.get('action', 'save')
        if action == 'delete':
            address = get_object_or_404(addresses, pk=request.POST.get('address_id'))
            was_default = address.is_default
            address.delete()
            if was_default:
                next_address = addresses.first()
                if next_address:
                    next_address.is_default = True
                    next_address.save(update_fields=['is_default', 'updated_at'])
            messages.success(request, 'Saved delivery address removed.')
            return redirect('address_book')
        if action == 'set_default':
            address = get_object_or_404(addresses, pk=request.POST.get('address_id'))
            with transaction.atomic():
                CustomerAddress.objects.filter(user=request.user, is_default=True).update(is_default=False)
                address.is_default = True
                address.save(update_fields=['is_default', 'updated_at'])
            messages.success(request, f'{address.label} is now your default delivery address.')
            return redirect('address_book')

        address_id = request.POST.get('address_id', '').strip()
        address = get_object_or_404(addresses, pk=address_id) if address_id else None
        label = request.POST.get('label', '').strip()[:40] or 'Home'
        recipient_name = request.POST.get('recipient_name', '').strip()
        mobile = request.POST.get('mobile', '').strip()
        address_text = request.POST.get('address', '').strip()
        city = request.POST.get('city', 'Jaunpur').strip()[:100] or 'Jaunpur'
        pincode = request.POST.get('pincode', '').strip()
        if not recipient_name or not address_text or len(address_text) > 1000:
            messages.error(request, 'Enter a recipient name and a complete address of up to 1,000 characters.')
        elif not re.fullmatch(r'[+0-9 ()-]{10,18}', mobile):
            messages.error(request, 'Enter a valid phone number.')
        elif not re.fullmatch(r'[1-9][0-9]{5}', pincode):
            messages.error(request, 'Enter a valid six-digit PIN code.')
        elif not address and addresses.count() >= 10:
            messages.error(request, 'You can save up to 10 delivery addresses.')
        else:
            make_default = request.POST.get('is_default') == 'on' or not addresses.exists()
            with transaction.atomic():
                if make_default:
                    CustomerAddress.objects.filter(user=request.user, is_default=True).update(is_default=False)
                if address:
                    address.label = label
                    address.recipient_name = recipient_name
                    address.mobile = mobile
                    address.address = address_text
                    address.city = city
                    address.pincode = pincode
                    address.is_default = make_default or address.is_default
                    address.save()
                else:
                    CustomerAddress.objects.create(
                        user=request.user,
                        label=label,
                        recipient_name=recipient_name,
                        mobile=mobile,
                        address=address_text,
                        city=city,
                        pincode=pincode,
                        is_default=make_default,
                    )
            messages.success(request, 'Delivery address saved to your Jaunpur account.')
            return redirect('address_book')

    edit_id = request.GET.get('edit', '')
    editing_address = addresses.filter(pk=edit_id).first() if edit_id else None
    return render(request, 'accounts/address_book.html', {
        'addresses': addresses,
        'editing_address': editing_address,
    })
