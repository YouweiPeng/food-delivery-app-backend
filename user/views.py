from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import make_password
from django.contrib.auth import get_user_model
from .serializers import UserSerializer
User = get_user_model()
from django.http import JsonResponse
from django.contrib.auth import login, authenticate, logout
from django.conf import settings
from django.utils import timezone
from django.contrib.sessions.models import Session
from django.utils import timezone
from django.contrib.auth import get_user_model
FRONT_END_DOMAIN = settings.FRONT_END_DOMAIN
User = get_user_model()
@api_view(['POST'])
@permission_classes([AllowAny])
def user_login(request):
    username_or_email = request.data.get("username").lower()
    password = request.data.get("password")
    try:
        get_user = User.objects.get(username=username_or_email)
    except User.DoesNotExist:
        try:
            get_user = User.objects.get(email=username_or_email)
        except User.DoesNotExist:
            return JsonResponse({'error': 'Invalid credentials'}, status=400)
    user = authenticate(username=get_user.username, password=password)
    if user is not None:
        login(request, user)
        response = JsonResponse({
            'message': 'Logged in successfully',
            'uuid': user.uuid,
            'username': user.username,
            'email': user.email,
            'address': user.address,
            'phone_number': user.phone_number,
            'room_number': user.room_number,
            'is_staff': user.is_staff,
        })
        response.set_cookie(
            'sessionid', 
            request.session.session_key, 
            httponly=True, 
            secure=True, 
            samesite='None',
        )
        
        response['Access-Control-Allow-Credentials'] = True
        response['Access-Control-Allow-Origin'] = FRONT_END_DOMAIN
        
        return response
    else:
        return JsonResponse({'error': 'Invalid credentials'}, status=400)




@api_view(['GET'])
@permission_classes([AllowAny])
def auto_login(request):
    session_id = request.COOKIES.get('sessionid')

    if session_id:
        try:

            session = Session.objects.get(session_key=session_id)

            # Check if the session has not expired
            if session.expire_date > timezone.now():
                # Get the session data
                session_data = session.get_decoded()

                # Get the user UUID stored in the session
                user_uuid = session_data.get('_auth_user_id')

                # Fetch the user associated with the session
                if user_uuid:
                    user = User.objects.get(uuid=user_uuid)  # Use uuid instead of id
                    return JsonResponse({
                        'loggedIn': True,
                        'uuid': user.uuid,
                        'username': user.username,
                        'email': user.email,
                        'address': user.address,
                        'phone_number': user.phone_number,
                        'room_number': user.room_number,
                        'is_staff': user.is_staff,
                    })

        except Session.DoesNotExist:
            pass

    # If session does not exist or user is not authenticated
    return JsonResponse({'loggedIn': False}, status=200)


@api_view(['POST'])
@permission_classes([AllowAny])
def user_signup(request):
    username = request.data.get("username").lower()
    password = request.data.get("password")
    email = request.data.get("email")
    address = request.data.get("address")
    phone_number = request.data.get("phone_number")
    room_number = request.data.get("room_number")
    if User.objects.filter(email=email).exists():
        return Response({'error': '邮箱已被注册'}, status=status.HTTP_400_BAD_REQUEST)
    if User.objects.filter(phone_number=phone_number).exists():
        return Response({'error': '电话号码已被注册'}, status=status.HTTP_400_BAD_REQUEST)
    user = User(username=username, password=make_password(password), email = email, address = address, phone_number = phone_number, room_number = room_number)
    user.save()
    return Response({'message': 'User created successfully', 'uuid': user.uuid, 'is_staff':user.is_staff}, status=status.HTTP_201_CREATED)

@api_view(['PUT'])
@permission_classes([AllowAny])
def edit_user_info(request):
    session_id = request.COOKIES.get('sessionid')
    if not session_id:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    session = Session.objects.get(session_key=session_id)
    if session.expire_date < timezone.now():
        return JsonResponse({'error': 'Session expired'}, status=400)
    session_data = session.get_decoded()
    user_uuid = session_data.get('_auth_user_id')
    user = User.objects.get(uuid=user_uuid)
    if request.method == 'PUT':
        serializer = UserSerializer(user, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
@api_view(['POST'])
@permission_classes([AllowAny])
def user_logout(request):
    logout(request)
    response = JsonResponse({'message': 'Logged out successfully'})
    response.delete_cookie('sessionid')
    return response