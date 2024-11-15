from django.http import JsonResponse
from django.shortcuts import redirect
import stripe
from rest_framework.decorators import api_view
from django.conf import settings
from rest_framework.decorators import permission_classes
from rest_framework.permissions import AllowAny
from mailjet_rest import Client
from decimal import Decimal, ROUND_HALF_UP
from django.contrib.sessions.models import Session
from user.models import User
from django.utils import timezone
import pytz
import urllib.parse
import os
import json
from django.views.decorators.csrf import csrf_exempt
from order.models import Order
stripe.api_key = settings.STRIPE_SECRET_KEY
YOUR_DOMAIN = settings.FRONT_END_DOMAIN
MAILJET_API_KEY = settings.MAILJET_API_KEY
MAILJET_SECRET_KEY = settings.MAILJET_SECRET_KEY
DEVELOPMENT = settings.DEVELOPMENT
import datetime
@api_view(['POST'])
@permission_classes([AllowAny])
def create_checkout_session(request):
    address = request.POST.get('address')
    lon = request.POST.get('lon')
    lat = request.POST.get('lat')
    comment = request.POST.get('comment')
    email = request.POST.get('email')
    phone_number = request.POST.get('phone_number')
    quantity = int(request.POST.get('quantity', 1))
    user = request.POST.get('uuid', '')
    room_number = request.POST.get('room_number', 'N/A')
    todays_meal = request.POST.get('content')
    addOnContent = request.POST.get('addOn')
    addOnFee = float(request.POST.get('addOnFee'))
    addOnFee_in_cents = int(addOnFee * 100)
    extraFee = int(request.POST.get('extraFee'))
    extraFee_in_cents = int(extraFee * 100)
    total_price = float(request.POST.get('total_price', 23))
    total_price_in_cents = int(total_price * 100)
    tax_rate = 0.05
    tax_in_cents = int((total_price_in_cents + addOnFee_in_cents) * tax_rate)
    tax_in_float = tax_in_cents / 100
    coupon = None
    if user != '':
        user_instance = User.objects.get(uuid=user)
        if user_instance.credit < (float(total_price) + float(extraFee) + float(addOnFee) + tax_in_float) and user_instance.credit > 0:
            coupon = stripe.Coupon.create(
                amount_off=int(user_instance.credit * 100),
                duration='once',
                currency='cad',
            )
    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            discounts = [
                {
                    'coupon': coupon.id
                }
            ] if user != '' and user_instance.credit < (float(total_price) + float(extraFee) + float(addOnFee) + tax_in_float) and user_instance.credit > 0 else None,
            line_items=[
                {
                    'price_data': {
                        'currency': 'cad',
                        'product_data': {
                            'name': f'餐食 × {quantity}',
                        },
                        'unit_amount': total_price_in_cents,
                    },
                    'quantity': 1,
                },
                {
                    'price_data': {
                        'currency': 'cad',
                        'product_data': {
                            'name': '税金 (Tax)',
                        },
                        'unit_amount': tax_in_cents,
                    },
                    'quantity': 1,
                },
                {
                    'price_data': {
                        'currency': 'cad',
                        'product_data': {
                            'name': '配送费 (delivery Fee)',
                        },
                        'unit_amount': extraFee_in_cents,
                    },
                    'quantity': 1,
                },
                
                {
                    'price_data': {
                        'currency': 'cad',
                        'product_data': {
                            'name': '饮品/小吃(Add Ons)',
                        },
                        'unit_amount': addOnFee_in_cents,
                    },
                    'quantity': 1,
                }
            ],
            mode='payment',
            success_url=YOUR_DOMAIN + 'success/session_id={CHECKOUT_SESSION_ID}',
            cancel_url=YOUR_DOMAIN + '?cancel=true',
            metadata={
                'session_type': 'order',
                'address': address,
                'comment': comment,
                'phone_number': phone_number,
                'quantity': quantity,
                'total_price': Decimal(total_price + extraFee + tax_in_float + addOnFee),
                'email': email,
                'user': user,
                'todays_meal': todays_meal,
                'extraFee': extraFee/100,
                'tax' : tax_in_float,
                'room_number': room_number,
                'lon': lon,
                'lat': lat,
                'addOn': addOnContent,
                'addOnFee': addOnFee,
                'payment_method': 'card' if coupon is None else 'mix',
            }
        )
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

    return redirect(checkout_session.url, code=303)



@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def stripe_webhook(request):
    payload = request.body
    sig_header = request.headers['Stripe-Signature']
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError as e:
        return JsonResponse({'error': 'Invalid payload'}, status=400)
    except stripe.error.SignatureVerificationError as e:
        return JsonResponse({'error': 'Invalid signature'}, status=400)
    session = event['data']['object']
    if event['type'] == 'checkout.session.completed' and session['metadata']['session_type'] != 'order':
            return JsonResponse({'status': 'not for this webhook'}, status= 202)
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        address = session['metadata']['address']
        comment = session['metadata']['comment']
        email = session['metadata']['email']
        phone_number = session['metadata']['phone_number']
        quantity = session['metadata']['quantity']
        total_price = session['metadata']['total_price']
        user = session['metadata']['user']
        today_meal = session['metadata']['todays_meal']
        meal_items = today_meal.split(",")
        extraFee = session['metadata']['extraFee']
        addOnFee = session['metadata']['addOnFee']
        tax = session['metadata']['tax']
        room_number = session['metadata']['room_number']
        lon = session['metadata']['lon']
        lat = session['metadata']['lat']
        payment_method = session['metadata']['payment_method']
        lon = float(lon)
        lat = float(lat)
        addOnContent = session['metadata']['addOn']
        meal_list_html = "".join([f"<li>{meal}</li>" for meal in meal_items])
        Order.objects.create(
            address=address,
            phone_number=phone_number,
            email=email,
            price=total_price,
            quantity=quantity,
            comment=comment if comment else '未备注',
            session_id=session['id'],
            user = user,
            payment_intent=session['payment_intent'],
            delivery_fee=int(float(extraFee)),
            room_number=room_number,
            date = datetime.datetime.now(pytz.timezone("America/Edmonton")),
            lon = lon,
            lat = lat,
            addOns = addOnContent,
            addOnFee = addOnFee,
            payment_method = payment_method,
        )
        if user != '':
            user_instance = User.objects.get(uuid=user)
            if user_instance.credit > 0:
                user_instance.credit = 0.00
                user_instance.save()
        encoded_address = urllib.parse.quote(address)
        order = Order.objects.get(session_id=session['id'])
        order.date = datetime.datetime.now(pytz.timezone("America/Edmonton"))
        order.save()
        mailjet = Client(auth=(MAILJET_API_KEY, MAILJET_SECRET_KEY), version='v3.1')
        data = {
            'Messages': [
                {
                    "From": {
                        "Email": "no-reply@tastyrush.ca",
                        "Name": "Tasty Rush"
                    },
                    "To": [
                        {
                            "Email": email
                        }
                    ],
                    "Subject": f"订单{order.order_code} 已经成功下单",
                    "TextPart": f"您的订单{order.order_code} 感谢您的订购",
                    "HTMLPart": f"""
                        <h3>您的订单 {order.order_code} 感谢您的订购</h3>
                        <p>订单号: {order.order_code}</p>
                        <p>地址: <a href="https://www.google.com/maps/search/?api=1&query={encoded_address}" target="_blank">{order.address}</a></p>
                        <p>房间号: {order.room_number}</p>
                        <p>电话号码: {order.phone_number}</p>
                        <p>电子邮件: {order.email}</p>
                        <p>日期: {order.date.strftime('%Y-%m-%d %H:%M:%S')}</p>
                        <p>餐价: {order.price}元 (未含其他费用)</p>
                        <p>餐品数量: {order.quantity}</p>
                        <p>备注: {order.comment}</p>
                        <p>税金: {tax}元</p>
                        <p>配送费: {"免费" if extraFee == "0.0" else f"{extraFee}元"}</p>
                        <p>饮品/小吃: {addOnContent}</p>
                        <p>附加品费用：{"无" if addOnFee == "0.0" else f"{addOnFee}元"} </p>
                        <h1>今日餐品</h1>
                        <ul>
                            {meal_list_html}
                        </ul>
                    """
                }
            ]
        }
        data_for_stores = {
            'Messages': [
                {
                    "From": {
                        "Email": "no-reply@tastyrush.ca",
                        "Name": "Tasty Rush"
                    },
                    "To": [
                        {
                            "Email": "penggang0719@gmail.com"
                        }
                    ],
                    "Subject": f"订单{order.order_code} 已经成功下单",
                    "TextPart": f"顾客的订单{order.order_code}, 以下是信息",
                    "HTMLPart": f"""
                        <p>订单号: {order.order_code}</p>
                        <p>顾客地址: <a href="https://www.google.com/maps/search/?api=1&query={encoded_address}" target="_blank">{order.address}</a></p>
                        <p>顾客房间号: {order.room_number}</p>
                        <p>顾客电话: {order.phone_number}</p>
                        <p>顾客邮箱: {order.email}</p>
                        <p>下单日期: {order.date.strftime('%Y-%m-%d %H:%M:%S')}</p>
                        <p>餐价: {order.price}元 (未含其他费用)</p>
                        <p>餐品数量: {order.quantity}</p>
                        <p>顾客备注: {order.comment}</p>
                        <p>税金: {tax}元 </p>
                        <p>配送费: {"免费" if extraFee == "0.0" else f"{extraFee}元"}</p>
                        <p>饮品/小吃: {addOnContent}</p>
                        <p>附加品费用：{"无" if addOnFee == "0.0" else f"{addOnFee}元"} </p>
                        <h1>今日餐品</h1>
                        <ul>
                            {meal_list_html}
                        </ul>
                    """
                }
            ]
        }
        if not DEVELOPMENT:
            mailjet.send.create(data=data)
            mailjet.send.create(data=data_for_stores)
    return JsonResponse({'status': 'success'}, status=200)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_stripe_session(request, session_id):
    try:
        order = Order.objects.get(session_id=session_id[11:])
        return JsonResponse({
            'order_code': order.order_code,
            'address': order.address,
            'phone_number': order.phone_number,
            'email': order.email,
            'date': order.date.strftime('%Y-%m-%d %H:%M:%S'),
            'price': order.price,
            'quantity': order.quantity,
            'comment': order.comment,
            'room_number': order.room_number,
        }, status=200)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@api_view(['POST'])
@permission_classes([AllowAny])
def create_check_session_for_add_money(request):
    amount = request.POST.get('amount')
    bouns = request.POST.get('bouns')
    uuid = request.POST.get('uuid')
    amount_in_cents = int(float(amount) * 100)
    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[
                {
                    'price_data': {
                        'currency': 'cad',
                        'product_data': {
                            'name': f'充值金额(实得{int(amount)+int(bouns)}元)',
                        },
                        'unit_amount': amount_in_cents,
                    },
                    'quantity': 1,
                }
            ],
            mode='payment',
            success_url=YOUR_DOMAIN,
            cancel_url=YOUR_DOMAIN,
            metadata={
                'session_type': 'add_money',
                'amount': amount,
                'bouns': bouns,
                'uuid': uuid,
            }
        )
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

    return redirect(checkout_session.url, code=303)

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def stripe_webhook_add_money(request):
    payload = request.body
    sig_header = request.headers['Stripe-Signature']
    endpoint_secret = settings.ADD_MONEY_WEBHOOK
    event = None
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError as e:
        return JsonResponse({'error': 'Invalid payload'}, status=400)
    except stripe.error.SignatureVerificationError as e:
        return JsonResponse({'error': 'Invalid signature'}, status=400)
    session = event['data']['object']
    if event['type'] == 'checkout.session.completed' and session['metadata']['session_type'] != 'add_money':
            return JsonResponse({'status': 'not for this webhook'}, status= 202)
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        amount = session['metadata']['amount']
        bouns = session['metadata']['bouns']
        uuid = session['metadata']['uuid']
        amount = Decimal(amount)
        bouns = Decimal(bouns)
        total = amount + bouns
        user = User.objects.get(uuid=uuid)
        user.credit += total
        user.save()
        mailjet = Client(auth=(MAILJET_API_KEY, MAILJET_SECRET_KEY), version='v3.1')
        data = {
            'Messages': [
                {
                    "From": {
                        "Email": "no-reply@tastyrush.ca",
                        "Name": "Tasty Rush"
                    },
                    "To": [
                        {
                            "Email": user.email
                        }
                    ],

                    "Subject": f"充值成功",
                    "TextPart": f"您已经成功充值，感谢您的支持！",
                    "HTMLPart": f"""
                        <h3>您已经成功充值</h3>
                        <p>充值金额: {amount}元</p>
                        <p>赠送金额: {bouns}元</p>
                        <p>总获取金额: {total}元</p>
                    """
                }
            ]
        }
        mailjet.send.create(data=data)
    return JsonResponse({'status': 'success'}, status=200)

@api_view(['POST'])
@permission_classes([AllowAny])
def create_order_by_existing_credit(request):
    uuid = request.POST.get('uuid', '')
    user = User.objects.get(uuid=uuid)
    address = request.POST.get('address')
    lon = request.POST.get('lon')
    lat = request.POST.get('lat')
    comment = request.POST.get('comment')
    email = request.POST.get('email')
    phone_number = request.POST.get('phone_number')
    quantity = int(request.POST.get('quantity', 1))
    room_number = request.POST.get('room_number', 'N/A')
    todays_meal = request.POST.get('content')
    meal_items = todays_meal.split(",")
    meal_items_html = "".join([f"<li>{meal}</li>" for meal in meal_items])
    addOnContent = request.POST.get('addOn')
    addOnFee = float(request.POST.get('addOnFee'))
    addOnFee_in_cents = int(addOnFee * 100)
    extraFee = int(request.POST.get('extraFee'))
    total_price = float(request.POST.get('total_price', 23))
    total_price_in_cents = int(total_price * 100)
    tax_rate = 0.05
    tax_in_cents = int((total_price_in_cents + addOnFee_in_cents) * tax_rate)
    tax = tax_in_cents / 100
    tax_in_float = tax_in_cents / 100
    payment_method = 'credit'
    rounded_ground_total = Decimal(float(total_price) + float(extraFee) + float(addOnFee) + tax_in_float).quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)
    if user.credit < (rounded_ground_total) and user.credit > 0:
        return JsonResponse({'error': 'Not enough credit'}, status=400)
    try:
        order = Order.objects.create(
            address=address,
            phone_number=phone_number,
            email=email,
            price=Decimal(total_price + extraFee + tax_in_float + addOnFee),
            quantity=quantity,
            comment=comment,
            user = uuid,
            delivery_fee=extraFee,
            room_number=room_number,
            date = datetime.datetime.now(pytz.timezone("America/Edmonton")),
            lon = lon,
            lat = lat,
            addOns = addOnContent,
            addOnFee = addOnFee,
            payment_method = payment_method,
        )
        user.credit -= rounded_ground_total
        user.save()
        order.save()
        encoded_address = urllib.parse.quote(address)
        mailjet = Client(auth=(MAILJET_API_KEY, MAILJET_SECRET_KEY), version='v3.1')
        data = {
            'Messages': [
                {
                    "From": {
                        "Email": "no-reply@tastyrush.ca",
                        "Name": "Tasty Rush"
                    },
                    "To": [
                        {
                            "Email": email
                        }
                    ],
                    "Subject": f"订单{order.order_code} 已经成功下单",
                    "TextPart": f"您的订单{order.order_code} 感谢您的订购",
                    "HTMLPart": f"""
                        <h3>您的订单 {order.order_code} 感谢您的订购</h3>
                        <p>订单号: {order.order_code}</p>
                        <p>地址: <a href="https://www.google.com/maps/search/?api=1&query={encoded_address}" target="_blank">{order.address}</a></p>
                        <p>房间号: {order.room_number}</p>
                        <p>电话号码: {order.phone_number}</p>
                        <p>电子邮件: {order.email}</p>
                        <p>日期: {order.date.strftime('%Y-%m-%d %H:%M:%S')}</p>
                        <p>餐价: {order.price}元 (未含其他费用)</p>
                        <p>餐品数量: {order.quantity}</p>
                        <p>备注: {order.comment}</p>
                        <p>税金: {tax}元</p>
                        <p>配送费: {"免费" if extraFee == "0.0" else f"{extraFee}元"}</p>
                        <p>饮品/小吃: {addOnContent}</p>
                        <p>附加品费用：{"无" if addOnFee == "0.0" else f"{addOnFee}元"} </p>
                        <h1>今日餐品</h1>
                        <ul>
                            {meal_items_html}
                        </ul>
                    """
                }
            ]
        }
        data_for_stores = {
            'Messages': [
                {
                    "From": {
                        "Email": "no-reply@tastyrush.ca",
                        "Name": "Tasty Rush"
                    },
                    "To": [
                        {
                            "Email": "penggang0719@gmail.com"
                        }
                    ],
                    "Subject": f"订单{order.order_code} 已经成功下单",
                    "TextPart": f"顾客的订单{order.order_code}, 以下是信息",
                    "HTMLPart": f"""
                        <p>订单号: {order.order_code}</p>
                        <p>顾客地址: <a href="https://www.google.com/maps/search/?api=1&query={encoded_address}" target="_blank">{order.address}</a></p>
                        <p>顾客房间号: {order.room_number}</p>
                        <p>顾客电话: {order.phone_number}</p>
                        <p>顾客邮箱: {order.email}</p>
                        <p>下单日期: {order.date.strftime('%Y-%m-%d %H:%M:%S')}</p>
                        <p>餐价: {order.price}元 (未含其他费用)</p>
                        <p>餐品数量: {order.quantity}</p>
                        <p>顾客备注: {order.comment}</p>
                        <p>税金: {tax}元 </p>
                        <p>配送费: {"免费" if extraFee == "0.0" else f"{extraFee}元"}</p>
                        <p>饮品/小吃: {addOnContent}</p>
                        <p>附加品费用：{"无" if addOnFee == "0.0" else f"{addOnFee}元"} </p>
                        <h1>今日餐品</h1>
                        <ul>
                            {meal_items_html}
                        </ul>
                    """
                }
            ]
        }
        if not DEVELOPMENT:
            mailjet.send.create(data=data)
            mailjet.send.create(data=data_for_stores)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
    return redirect(YOUR_DOMAIN, code=303)
                    
    
    