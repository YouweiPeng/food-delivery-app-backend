from django.urls import path

from . import views

urlpatterns = [
    path('login/', views.user_login),
    path('signup/', views.user_signup),
    path('edit/', views.edit_user_info),
    path('auto_login/', views.auto_login),
    path('logout/', views.user_logout),
    path('get_code/', views.generate_verification_code),
    path('change_password/', views.change_password),
]