from django.contrib import admin
from .models import Order, FoodGroup, FoodItem
# Register your models here.

admin.site.register(Order)
admin.site.register(FoodGroup)
admin.site.register(FoodItem)