from django.contrib import admin
from .models import Order, FoodGroup, FoodItem, Menu
# Register your models here.
admin.site.register(Menu)
admin.site.register(Order)
admin.site.register(FoodItem)

# run the save() inside selected food group
@admin.action(description="make menu")
def make_menu(modeladmin, request, queryset):
    for food_group in queryset:
        food_group.save()
        
class FoodGroupAdmin(admin.ModelAdmin):
    actions = [make_menu]
    list_display = ('food', 'day', 'week')
    list_filter = ('day', 'week')
    search_fields = ('food__name', 'day', 'week')
    ordering = ('week', 'day')
    


admin.site.register(FoodGroup, FoodGroupAdmin)