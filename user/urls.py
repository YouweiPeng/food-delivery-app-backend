from django.urls import path

from . import views

urlpatterns = [
    path('login/', views.user_login),
    path('signup/', views.user_signup),
    path('edit/', views.edit_user_info),
    path('auto_login/', views.auto_login),
    path('logout/', views.user_logout),
]