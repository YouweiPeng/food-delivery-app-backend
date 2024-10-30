from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from .models import FoodGroup, Order, Menu
from .serializers import OrderSerializer
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
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


@api_view(['POST'])
@permission_classes([AllowAny])
def create_order(request):
    data = request.data
    try:
        order = Order.objects.create(**data)

        return Response({
            'message': 'Order created successfully',
            'order_code': order.order_code,
            'address': order.address,
            'phone_number': order.phone_number,
            'email': order.email,
            'date': order.date.strftime('%Y-%m-%d %H:%M:%S'),
            'price': order.price,
            'quantity': order.quantity,
            'comment': order.comment
        }, status=status.HTTP_201_CREATED)

    except KeyError as e:
        return Response({
            'error': f'Missing field: {str(e)}'
        }, status=status.HTTP_400_BAD_REQUEST)

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
    if order.status != 'pending':
        return JsonResponse({'error': 'Order cannot be cancelled'}, status=400)
    try:
        stripe.Refund.create(
            payment_intent=order.payment_intent,
            amount = int(int(order.price) * 100 - 0.062 * int(order.price) * 100 - 0.3 * 100)
        )
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
    order.status = 'refunded'
    order.save()
    return JsonResponse({'message': 'Order cancelled successfully'}, status=200)
