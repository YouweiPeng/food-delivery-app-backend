from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from .models import FoodGroup, Order, Menu
from .serializers import OrderSerializer
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from mailjet_rest import Client
from rest_framework import status
import uuid
from .serializers import MenuSerializer
from user.models import User
from django.contrib.sessions.models import Session
from django.utils import timezone
from django.http import JsonResponse
import stripe
from django.conf import settings
stripe.api_key = settings.STRIPE_SECRET_KEY
MAILJET_API_KEY = settings.MAILJET_API_KEY
MAILJET_SECRET_KEY = settings.MAILJET_SECRET_KEY
@api_view(['GET'])
@permission_classes([AllowAny])
def getAllFoodItems(request):
    res = {
        "Week_1": {
            "Monday": [],
            "Tuesday": [],
            "Wednesday": [],
            "Thursday": [],
            "Friday": [],
            "Saturday": [],
            "Sunday": []
        },
        "Week_2": {
            "Monday": [],
            "Tuesday": [],
            "Wednesday": [],
            "Thursday": [],
            "Friday": [],
            "Saturday": [],
            "Sunday": []
        }
    }
    food_groups = FoodGroup.objects.all()
    day_map = {
        'MON': 'Monday',
        'TUE': 'Tuesday',
        'WED': 'Wednesday',
        'THU': 'Thursday',
        'FRI': 'Friday',
        'SAT': 'Saturday',
        'SUN': 'Sunday'
    }
    for food_group in food_groups:
        food_item = food_group.food
        food_data = {
            "name": food_item.name,
            "description": food_item.description,
            "picture_base64": food_item.picture if food_item.picture else None
        }
        if food_group.week == 'WEEK1':
            res['Week_1'][day_map[food_group.day]].append(food_data)
        elif food_group.week == 'WEEK2':
            res['Week_2'][day_map[food_group.day]].append(food_data)

    return Response(res, status=200)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_orders_for_user(request, uuid):
    session_id = request.COOKIES.get('sessionid')
    if not session_id:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    session = Session.objects.get(session_key=session_id)
    if session.expire_date < timezone.now():
        return JsonResponse({'error': 'Session expired'}, status=400)
    session_data = session.get_decoded()
    user_uuid = session_data.get('_auth_user_id')
    user = User.objects.get(uuid=user_uuid)
    orders = Order.objects.filter(user=uuid).order_by('-date')
    serializer = OrderSerializer(orders, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_menu(request):
    menu = Menu.objects.all()
    menu_serializer = MenuSerializer(menu, many=True)
    return Response(menu_serializer.data, status=status.HTTP_200_OK)

@api_view(['PUT'])
@permission_classes([AllowAny])
def cancel_order(request, order_code, uuid):
    session_id = request.COOKIES.get('sessionid')
    if not session_id:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    session = Session.objects.get(session_key=session_id)
    if session.expire_date < timezone.now():
        return JsonResponse({'error': 'Session expired'}, status=400)
    order = Order.objects.get(order_code=order_code, user=uuid)
    if order.cancel_time < timezone.now():
        return JsonResponse({'error': 'Order cannot be cancelled, already passed cancel time'}, status=400)
    if order.status != 'pending':
        return JsonResponse({'error': 'Order cannot be cancelled'}, status=400)
    try:
        stripe.Refund.create(
            payment_intent=order.payment_intent,
            amount = int(int(order.price + order.delivery_fee) * 100 - 0.062 * int(order.price + order.delivery_fee) * 100 - 0.3 * 100)
        )
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
    order.status = 'refunded'
    order.save()
    mailjet = Client(auth=(MAILJET_API_KEY, MAILJET_SECRET_KEY), version='v3.1')
    data = {
        'Messages': [
            {
                "From": {
                    "Email": "990907pyw@gmail.com",
                },
                "To": [
                    {
                        "Email": order.email,
                    }
                ],
                "Subject": "您的订单已取消",
                "TextPart": f"您的订单{order.order_code} 已取消",
                "HTMLPart": f"""
                <h3>您的订单{order.order_code} 已取消， 您将在 5-10个工作日看到退款入账</h3>
                <h1>订单详情</h1>
                <p>订单号: {order.order_code}</p>
                <p>订单日期: {timezone.localtime(order.date).strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p>地址: {order.address}</p>
                <p>电话号码: {order.phone_number}</p>
                <p>电子邮件: {order.email}</p>
                <p>餐品价格: {order.price}</p>
                <p>配送费: {order.delivery_fee}</p>
                <p>由于stripe平台条款, 会收取6-10%作为手续费</p>
                """
            }
        ]
    }
    mailjet.send.create(data=data)
    return JsonResponse({'message': 'Order cancelled successfully'}, status=200)



@api_view(['GET'])
@permission_classes([AllowAny])
def delivery_get_order_for_today(request):
    session_id = request.COOKIES.get('sessionid')
    if not session_id:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    session = Session.objects.get(session_key=session_id)
    if session.expire_date < timezone.now():
        return JsonResponse({'error': 'Session expired'}, status=400)
    today = timezone.localdate()
    orders = Order.objects.filter(cancel_time__date=today, status='pending')
    serializer = OrderSerializer(orders, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

from django.utils.html import escape

@api_view(['POST'])
@permission_classes([AllowAny])
def delivery_finish_order(request):
    session_id = request.COOKIES.get('sessionid')
    if not session_id:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    session = Session.objects.get(session_key=session_id)
    if session.expire_date < timezone.now():
        return JsonResponse({'error': 'Session expired'}, status=400)
    order_code = request.data.get("order_code")
    id = request.data.get("id")
    image = request.FILES.get("image") 
    order = Order.objects.get(order_code=order_code, id=id)
    order.status = 'delivered'
    if image:
        order.upload_image = image
        order.save()
    
    mailjet = Client(auth=(MAILJET_API_KEY, MAILJET_SECRET_KEY), version='v3.1')
    data = {
        'Messages': [
            {
                "From": {
                    "Email": "990907pyw@gmail.com"
                },
                "To": [
                    {
                        "Email": order.email,
                    }
                ],
                "Subject": "您的订单已送达",
                "TextPart": f"您的订单{order.order_code} 已送达",
                "HTMLPart": f"""
                <h3>您的订单{order.order_code} 已送达</h3>
                <h1>订单详情</h1>
                <p>订单号: {order.order_code}</p>
                <p>订单日期: {timezone.localtime(order.date).strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p>地址: {escape(order.address)}</p>
                <p>电话号码: {escape(order.phone_number)}</p>
                <p>电子邮件: {escape(order.email)}</p>
                <p>餐品价格: {order.price}</p>
                """,
                "Attachments": [
                    {
                        "ContentType": "image/png",
                        "Filename": "配送员送达图片",
                        "Base64Content": order.image
                    }
                ] if image else []
                
            }
        ]
    }
    mailjet.send.create(data=data)
    return JsonResponse({'message': 'Order finished successfully', "order_code": order_code}, status=200)

