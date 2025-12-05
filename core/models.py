import string
import random
from django.db import models
from django.contrib.auth.models import User
import uuid

def generate_unique_code():
    length = 6
    chars = string.ascii_uppercase + string.digits
    while True:
        code = ''.join(random.choices(chars, k=length))
        if not Restaurant.objects.filter(code=code).exists():
            return code

class Restaurant(models.Model):
    code = models.CharField(max_length=6, unique=True, editable=False, blank=True)
    name = models.CharField(max_length=60)
    address = models.TextField()
    owner = models.OneToOneField(User, on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = generate_unique_code()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.code})"


class Category(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="categories")
    name = models.CharField(max_length=40)

    def __str__(self):
        return f"{self.name} ({self.restaurant.name})"

class MenuItem(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="items")
    name = models.CharField(max_length=60)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    image = models.ImageField(upload_to="menu_items/", blank=True, null=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.category.name})"

class Order(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("preparing", "Preparing"),
        ("ready", "Ready"),
        ("delivered", "Delivered"),
    )
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE)
    table_number = models.CharField(max_length=20)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="pending")
    amount = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    paid = models.BooleanField(default=False)
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=255, blank=True, null=True)
    #for session creation
    session_id = models.UUIDField(default=uuid.uuid4, unique=True, blank=True, null=True)

    def __str__(self):
        return f"Order {self.id} - Table {self.table_number}"

    def update_amount(self):
        total = sum(i.price * i.quantity for i in self.order_items.all())
        self.amount = total
        self.save(update_fields=["amount"])

    @property
    def items_display(self):
        return ", ".join([f"{i.name}×{i.quantity}" for i in self.order_items.all()])


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="order_items")
    menu_item = models.ForeignKey(MenuItem, on_delete=models.PROTECT)
    name = models.CharField(max_length=60)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self):
        return f"{self.name} × {self.quantity}"
    




class Bill(models.Model):
    """
    Optional: persistent invoice for accounting/audit.
    Create a Bill when an order is paid/completed.
    """
    order = models.OneToOneField('Order', on_delete=models.CASCADE, related_name='bill')
    invoice_number = models.CharField(max_length=32, unique=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    service_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_method = models.CharField(max_length=30, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Invoice {self.invoice_number} - Order {self.order.id}"

    @staticmethod
    def generate_invoice_number():
        # simple invoice generator; replace with something robust if needed
        ts = timezone.now().strftime("%Y%m%d%H%M%S")
        return f"INV{ts}"
    
    def save(self, *args, **kwargs):
        if not self.invoice_number:
            self.invoice_number = self.generate_invoice_number()
        super().save(*args, **kwargs)