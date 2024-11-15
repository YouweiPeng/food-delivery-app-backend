from django.urls import path
from . import views

urlpatterns = [
    path('create-checkout-session/', views.create_checkout_session, name='create-checkout-session'),
    path('webhook/', views.stripe_webhook, name='stripe-webhook'),
    path('stripe-session/<str:session_id>/', views.get_stripe_session, name='get_stripe_session'),
    path('create-checkout-session-add-money/', views.create_check_session_for_add_money, name='add_money'),
    path('add-money-webhook/', views.stripe_webhook_add_money, name='stripe-webhook-add-money'),
    path('existing-money-create-order/', views.create_order_by_existing_credit, name='create-order-existing-money'),
]