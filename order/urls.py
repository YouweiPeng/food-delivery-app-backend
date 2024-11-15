from django.urls import path

from . import views

urlpatterns = [
    path('food/', views.getAllFoodItems),
    path('get_order/<str:uuid>', views.get_orders_for_user),
    path('get_menu/', views.get_menu),
    path('cancel_order/<str:order_code>/<str:uuid>', views.cancel_order),
    path('delivery/', views.delivery_get_order_for_today),
    path('delivery/finish_order/', views.delivery_finish_order),
    path('cancel_order_by_credit/', views.cancel_order_by_credit, name='cancel-order-by-credit'),
]