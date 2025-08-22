from django.contrib import admin

from goods.models import Category, Discounts, Items, OrderItems, Orders

# Register your models here.

admin.site.register(Category)
admin.site.register(Orders)
admin.site.register(Items)
admin.site.register(OrderItems)
admin.site.register(Discounts)
