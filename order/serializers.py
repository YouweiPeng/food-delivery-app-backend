from rest_framework import serializers
from .models import Order, FoodItem, FoodGroup, Menu

class FoodItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = FoodItem
        fields = ['name', 'description', 'picture']

class FoodGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = FoodGroup
        fields = '__all__'

class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = '__all__'
class MenuSerializer(serializers.ModelSerializer):
    monday = FoodItemSerializer(many=True, read_only=True)
    tuesday = FoodItemSerializer(many=True, read_only=True)
    wednesday = FoodItemSerializer(many=True, read_only=True)
    thursday = FoodItemSerializer(many=True, read_only=True)
    friday = FoodItemSerializer(many=True, read_only=True)
    saturday = FoodItemSerializer(many=True, read_only=True)
    sunday = FoodItemSerializer(many=True, read_only=True)
    class Meta:
        model = Menu
        fields = ['name', 'week', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']