from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User

class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'uuid', 'is_staff', 'is_active')
    readonly_fields = ('uuid',)
    fieldsets = (
        (None, {'fields': ('uuid', 'username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'address', 'phone_number', 'room_number')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
        ('credits', {'fields': ('credit',)}),
    )

admin.site.register(User, UserAdmin)