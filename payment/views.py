from django.http import JsonResponse
from django.shortcuts import redirect
import stripe
from rest_framework.decorators import api_view
from django.conf import settings
from rest_framework.decorators import permission_classes
from rest_framework.permissions import AllowAny
from mailjet_rest import Client
import urllib.parse
import os
import json
from django.views.decorators.csrf import csrf_exempt
from order.models import Order
stripe.api_key = settings.STRIPE_SECRET_KEY
YOUR_DOMAIN = settings.FRONT_END_DOMAIN
MAILJET_API_KEY = settings.MAILJET_API_KEY
MAILJET_SECRET_KEY = settings.MAILJET_SECRET_KEY
import datetime
@api_view(['POST'])
@permission_classes([AllowAny])
def create_checkout_session(request):
    address = request.POST.get('address')
    comment = request.POST.get('comment')
    email = request.POST.get('email')
    phone_number = request.POST.get('phone_number')
    quantity = int(request.POST.get('quantity', 1))
    user = request.POST.get('uuid', '')
    todays_meal = request.POST.get('content')
    extraFee = int(request.POST.get('extraFee'))
    extraFee = int(extraFee * 100)
    total_price = float(request.POST.get('total_price', 19.8))
    total_price_in_cents = int(total_price * 100)
    tax_rate = 0.05
    tax_in_cents = int(total_price_in_cents * tax_rate)
    tax_in_float = tax_in_cents / 100
    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
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
                        'unit_amount': extraFee,
                    },
                    'quantity': 1,
                }
            ],
            mode='payment',
            success_url=YOUR_DOMAIN + 'success/session_id={CHECKOUT_SESSION_ID}',
            cancel_url=YOUR_DOMAIN + '?cancel=true',
            metadata={
                'address': address,
                'comment': comment,
                'phone_number': phone_number,
                'quantity': quantity,
                'total_price': total_price,
                'email': email,
                'user': user,
                'todays_meal': todays_meal,
                'extraFee': extraFee/100,
                'tax' : tax_in_float
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
    sig_header = request.headers.get('stripe-signature')
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
        tax = session['metadata']['tax']
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
        )
        encoded_address = urllib.parse.quote(address)
        order = Order.objects.get(session_id=session['id'])
        mailjet = Client(auth=(MAILJET_API_KEY, MAILJET_SECRET_KEY), version='v3.1')
        data = {
            'Messages': [
                {
                    "From": {
                        "Email": "990907pyw@gmail.com",
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
                        <p>电话号码: {order.phone_number}</p>
                        <p>电子邮件: {order.email}</p>
                        <p>日期: {order.date.strftime('%Y-%m-%d %H:%M:%S')}</p>
                        <p>价格: {order.price}</p>
                        <p>餐品数量: {order.quantity}</p>
                        <p>备注: {order.comment}</p>
                        <p>税金: {tax}元</p>
                        <p>配送费: {"免费" if extraFee == "0.0" else f"{extraFee}元"}</p>
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
                        "Email": "990907pyw@gmail.com"
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
                        <p>顾客电话: {order.phone_number}</p>
                        <p>顾客邮箱: {order.email}</p>
                        <p>下单日期: {order.date.strftime('%Y-%m-%d %H:%M:%S')}</p>
                        <p>价格: {order.price}</p>
                        <p>餐品数量: {order.quantity}</p>
                        <p>顾客备注: {order.comment}</p>
                        <p>税金: {tax}元</p>
                        <p>配送费: {"免费" if extraFee == "0.0" else f"{extraFee}元"}</p>
                        <h1>今日餐品</h1>
                        <ul>
                            {meal_list_html}
                        </ul>
                    """
                }
            ]
        }
        
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
            'comment': order.comment
        }, status=200)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
