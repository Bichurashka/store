from django.db import models

# Create your models here.


class Category(models.Model):
    name = models.CharField(max_length=20, unique=True)
    parent = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self) -> str:
        return str(self.name)


class Orders(models.Model):
    class OrderStatus(models.TextChoices):
        PENDING = "Pending", "pending"
        PAID = "Paid", "paid"
        SHIPPED = "Shipped", "shipped"
        CANCELED = "Canceled", "canceled"

    status = models.CharField(max_length=20, choices=OrderStatus.choices)
    price = models.DecimalField(decimal_places=2, max_digits=10)
    user = models.ForeignKey("users.CustomUser", on_delete=models.CASCADE)


class Items(models.Model):
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=20)
    price = models.DecimalField(decimal_places=2, max_digits=10)
    base_price = models.DecimalField(decimal_places=2, max_digits=10)
    description = models.CharField(max_length=100, null=True, blank=True)
    sku = models.CharField(max_length=20, unique=True)

    def __str__(self) -> str:
        return str(self.name)


class OrderItems(models.Model):
    order = models.ForeignKey(Orders, on_delete=models.CASCADE, related_name="items")
    item = models.ForeignKey(Items, on_delete=models.CASCADE)
    amount = models.IntegerField()


class Discounts(models.Model):
    class DiscountType(models.TextChoices):
        PERCENTAGE = "Percentage", "percentage"
        FIXED = "Fixed", "fixed"

    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    type = models.CharField(max_length=20, choices=DiscountType.choices)
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    amount = models.DecimalField(decimal_places=2, max_digits=10)
