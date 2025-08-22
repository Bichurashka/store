from django.db import models

# Create your models here.


class Category(models.Model):
    name: models.CharField = models.CharField(max_length=20, unique=True)
    parent_id: models.ForeignKey = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True
    )


class Orders(models.Model):
    class OrderStatus(models.TextChoices):
        PENDING = "Pending", "pending"
        PAID = "Paid", "paid"
        SHIPPED = "Shipped", "shipped"
        CANCELED = "Canceled", "canceled"

    status: models.CharField = models.CharField(max_length=20, choices=OrderStatus.choices)
    price: models.DecimalField = models.DecimalField(decimal_places=2, max_digits=10)
    user_id: models.ForeignKey = models.ForeignKey("users.CustomUser", on_delete=models.CASCADE)


class Items(models.Model):
    category_id: models.ForeignKey = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True
    )
    name: models.CharField = models.CharField(max_length=20)
    price: models.DecimalField = models.DecimalField(decimal_places=2, max_digits=10)
    description: models.CharField = models.CharField(max_length=100, null=True, blank=True)
    sku: models.CharField = models.CharField(max_length=20, unique=True)


class OrderItems(models.Model):
    order_id: models.ForeignKey = models.ForeignKey(Orders, on_delete=models.CASCADE)
    item_id: models.ForeignKey = models.ForeignKey(Items, on_delete=models.CASCADE)
    amount: models.IntegerField = models.IntegerField()


class Discounts(models.Model):
    class DiscountType(models.TextChoices):
        PERCENTAGE = "Percentage", "percentage"
        FIXED = "Fixed", "fixed"

    category_id: models.ForeignKey = models.ForeignKey(Category, on_delete=models.CASCADE)
    type: models.CharField = models.CharField(max_length=20, choices=DiscountType.choices)
    start_datetime: models.DateTimeField = models.DateTimeField()
    end_datetime: models.DateTimeField = models.DateTimeField()
    amount: models.DecimalField = models.DecimalField(decimal_places=2, max_digits=10)
