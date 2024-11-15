from django.db import models
import uuid
from django.contrib.auth.models import AbstractUser
import datetime
import pytz

class User(AbstractUser):
    uuid = models.UUIDField(primary_key=True, editable=False, default=uuid.uuid4)
    username = models.CharField(max_length=100, unique=True)
    password = models.CharField(max_length=100)
    address = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=100)
    email = models.EmailField(max_length=100)
    room_number = models.CharField(max_length=100, blank=True, null=True, default='N/A')
    credit = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    verification_code = models.CharField(max_length=6, blank=True, null=True)
    verification_expiry = models.DateTimeField(blank=True, null=True, default = datetime.datetime.now(pytz.timezone("America/Edmonton")))
    def __str__(self):
        return self.username + ' 邮箱: ' + self.email + ' 电话: '+ self.phone_number