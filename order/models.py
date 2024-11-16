from django.db import models
from django.contrib.postgres.fields import ArrayField
import string
import random
import datetime
from user.models import User
import base64
from io import BytesIO
from django.core.files.base import ContentFile
from PIL import Image
import pytz
from django.utils import timezone
DAY_CHOICES = [
    ('MON', 'Monday'),
    ('TUE', 'Tuesday'),
    ('WED', 'Wednesday'),
    ('THU', 'Thursday'),
    ('FRI', 'Friday'),
    ('SAT', 'Saturday'),
    ('SUN', 'Sunday'),
]
WEEK_CHOICES = [
    ('WEEK1', 'Week 1'),
    ('WEEK2', 'Week 2'),
]
ORDER_STATUS_CHOICES = [
    ('pending', 'pending'),
    ('delivered', 'delivered'),
    ('refunded', 'refunded'),
]
PAYMENT_METHOD_CHOICES = [
    ('card', 'card'),
    ('mix', 'mix'),
    ('credit', 'credit'),
]

def generate_order_code():
    length = 6
    chars = string.ascii_uppercase + string.digits
    max_attempts = 100 
    for _ in range(max_attempts):
        new_code = ''.join(random.choices(chars, k=length))
        if not Order.objects.filter(order_code=new_code).exists():
            return new_code
    raise ValueError("Unable to generate a unique order code after 100 attempts.")


class Order(models.Model):
    order_code = models.CharField(max_length=9, unique=True, default=generate_order_code)
    address = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=100)
    email = models.EmailField(max_length=100)
    date = models.DateTimeField(default = datetime.datetime.now(pytz.timezone("America/Edmonton")))
    price = models.DecimalField(max_digits=6, decimal_places=2)
    quantity = models.IntegerField()
    comment = models.TextField(blank=True)
    delivery_fee = models.IntegerField(default=0)
    session_id = models.CharField(max_length=100, default='')
    status = models.CharField(max_length=10, choices=ORDER_STATUS_CHOICES, default='pending')
    upload_image = models.ImageField(upload_to='temp_images/', blank=True, null=True)
    image = models.TextField(blank=True)
    user = models.CharField(max_length=10000, default='')
    payment_intent = models.CharField(max_length=10000, default='')
    room_number = models.CharField(max_length=100, blank=True, null=True, default='N/A')
    lon = models.DecimalField(max_digits=9, decimal_places=6, default=0)
    lat = models.DecimalField(max_digits=9, decimal_places=6, default=0)
    addOns = models.TextField(blank=True, null=True)
    addOnFee = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    is_early = models.BooleanField(default=False)
    payment_method = models.CharField(max_length=100, choices=PAYMENT_METHOD_CHOICES, default='card')
    cancel_time = models.DateTimeField(blank=True, null=True) # should not be cancelled after this time, if order is ordered after 11am, it should not be cancelled after tommorow 9L30am, if ordered before 11am, it should not be cancelled after today 9:30am
    is_utensils = models.BooleanField(default=True)
    def save(self, *args, **kwargs):
        order_time = timezone.localtime(self.date)
        if order_time.hour >= 10:
            self.cancel_time = order_time.replace(hour=9, minute=30, second=0, microsecond=0) + datetime.timedelta(days=1)
        else:
            self.cancel_time = order_time.replace(hour=9, minute=30, second=0, microsecond=0)
        if timezone.is_naive(self.cancel_time):
            self.cancel_time = timezone.make_aware(self.cancel_time, timezone.get_current_timezone())
        if self.upload_image:
            image = Image.open(self.upload_image)
            buffer = BytesIO()
            image.save(buffer, format=image.format)
            base64_image = base64.b64encode(buffer.getvalue()).decode()
            self.image = base64_image
            self.upload_image = None
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Order {self.order_code} at {self.address} of quantity {self.quantity}"


class FoodGroup(models.Model):
    food = models.ForeignKey('FoodItem', on_delete=models.CASCADE)
    day = models.CharField(max_length=3, choices=DAY_CHOICES)
    week = models.CharField(max_length=5, choices=WEEK_CHOICES)
    def save(self, *args, **kwargs):
        menu = Menu.objects.filter(week=self.week).first()
        if self.day == 'MON':
            menu.monday.add(self.food)
        elif self.day == 'TUE':
            menu.tuesday.add(self.food)
        elif self.day == 'WED':
            menu.wednesday.add(self.food)
        elif self.day == 'THU':
            menu.thursday.add(self.food)
        elif self.day == 'FRI':
            menu.friday.add(self.food)
        elif self.day == 'SAT':
            menu.saturday.add(self.food)
        elif self.day == 'SUN':
            menu.sunday.add(self.food)
    
    
    
    def __str__(self):
        return self.day.__str__() + ' ' + self.food.name + ' of ' + self.week.__str__().lower()
    

class FoodItem(models.Model): # single food item
    name = models.CharField(max_length=100)
    picture = models.TextField(blank=True)
    upload_image = models.ImageField(upload_to='food_pictures/', blank=True, null=True)
    def save(self, *args, **kwargs):
        if self.upload_image:
            image = Image.open(self.upload_image)
            buffer = BytesIO()
            image.save(buffer, format=image.format)
            base64_image = base64.b64encode(buffer.getvalue()).decode()
            self.picture = base64_image
            self.upload_image = None
        super().save(*args, **kwargs)
    description = models.TextField()
    def __str__(self):
        return self.name

class Menu(models.Model):
    name = models.CharField(max_length=100, default='Menu')
    week = models.CharField(max_length=5, choices=WEEK_CHOICES, default='WEEK1')
    monday = models.ManyToManyField(FoodItem, related_name='monday', blank=True)
    tuesday = models.ManyToManyField(FoodItem, related_name='tuesday', blank=True)
    wednesday = models.ManyToManyField(FoodItem, related_name='wednesday', blank=True)
    thursday = models.ManyToManyField(FoodItem, related_name='thursday', blank=True)
    friday = models.ManyToManyField(FoodItem, related_name='friday', blank=True)
    saturday = models.ManyToManyField(FoodItem, related_name='saturday', blank=True)
    sunday = models.ManyToManyField(FoodItem, related_name='sunday', blank=True)
    
    def __str__(self):
        return self.name + ' ' + self.week.__str__().lower()