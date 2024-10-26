from django.urls import path

from . import views

urlpatterns = [
    path('food/', views.getAllFoodItems),
    path('create/', views.create_order),
    path('get_order/<str:uuid>', views.get_orders_for_user),
]