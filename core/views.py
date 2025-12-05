from django.shortcuts import render, get_object_or_404, redirect, HttpResponse
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Sum
from .models import Restaurant, Category, MenuItem, Order, OrderItem
from .forms import CategoryForm, MenuItemForm
import json
from django.shortcuts import render, get_object_or_404
from .models import Restaurant, Category
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Restaurant, Order, OrderItem
from django.utils.timezone import make_aware
from django.db.models import Sum, Count, Avg
from decimal import Decimal
from datetime import datetime, timedelta
from decimal import Decimal
from django.db.models import Sum, Count
from django.http import JsonResponse
from django.utils.timezone import make_aware
from .models import Restaurant, Order, OrderItem
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import razorpay
from django.shortcuts import render
from .models import Order







def home(request):
    return render(request, "core/home.html")





def customer_menu(request, restaurant_code, table_number):
    restaurant = get_object_or_404(Restaurant, code=restaurant_code)
    categories = Category.objects.filter(restaurant=restaurant).prefetch_related("items")

    def initials(name):
        parts = name.split()
        if len(parts) > 1:
            return parts[0][0].upper() + parts[1][0].upper()
        return name[:2].upper() if len(name) >= 2 else name.upper()

    cat_items = []
    for cat in categories:
        active_items = cat.items.filter(active=True)
        wrapped_items = []

        for item in active_items:
            # Determine thumbnail: use uploaded image if available, otherwise initials
            thumb = item.image.url if getattr(item, "image", None) else initials(item.name)

            wrapped_items.append({
                "item": item,
                "thumb": thumb,
                "veg": getattr(item, "veg", True),
                "desc": getattr(item, "desc", ""),
                "price": getattr(item, "price", 0),
            })

        cat_items.append((cat, wrapped_items))

    context = {
        "restaurant": restaurant,
        "table_number": table_number,
        "cat_items": cat_items,
    }
    return render(request, "core/menu.html", context)




import json
import razorpay
from django.conf import settings
from django.shortcuts import render, get_object_or_404
from .models import Restaurant, Category, MenuItem

def customer_checkout(request, restaurant_code, table_number):
    restaurant = get_object_or_404(Restaurant, code=restaurant_code)
    categories = Category.objects.filter(restaurant=restaurant)

    if request.method == 'POST':
        cart_json = request.POST.get('cartdata', '{}')
        try:
            cart = json.loads(cart_json)
        except json.JSONDecodeError:
            cart = {}

        if not cart:
            return render(request, "core/order_failed.html", {
                'error': "Cart is empty or invalid."
            })

        # Calculate total using DB prices (never trust client)

        # Initialize Razorpay
        total = 0
        
        order = Order.objects.create(
            restaurant=restaurant,
            status='pending',
            table_number=table_number,
            paid=False
        )

        for item_id, item_data in cart.items():
            try:
                menu_item = MenuItem.objects.get(id=item_id, category__restaurant=restaurant)
            except MenuItem.DoesNotExist:
                continue
            qty = int(item_data.get('qty', 0))
            if qty > 0:
                order_item = OrderItem.objects.create(
                    order = order,
                    menu_item = menu_item,
                    name = menu_item,
                    quantity = qty,
                    price = qty * menu_item.price,
                    )
                total += float(menu_item.price) * qty

        total = round(total, 2)
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        razorpay_order = client.order.create({
            "amount": int(total * 100),
            "currency": "INR",
            "receipt": f"table_{table_number}",
            "payment_capture": 1
        })
        order.razorpay_order_id=razorpay_order['id']
        order.amount=total
        order.save()


        

        context = {
            'restaurant': restaurant,
            'table_number': table_number,
            'razorpay_key_id': settings.RAZORPAY_KEY_ID,
            'razorpay_order_id': razorpay_order['id'],
            'cart_json': json.dumps(cart),
            'amount': total,
        }
        return render(request, "core/order_payment.html", context)

    # GET → show menu
    cat_items = [(cat, cat.items.filter(active=True)) for cat in categories]
    return render(request, "core/menu.html", {
        'restaurant': restaurant,
        'table_number': table_number,
        'cat_items': cat_items,
    })



# --- Restaurant admin views ---




def dashboard(request):
    restaurant = get_object_or_404(Restaurant, owner=request.user)
    return render(request, "core/dashboard.html", {"restaurant": restaurant})





def dashboard_data(request):
    try:
        restaurant = Restaurant.objects.first()
        if not restaurant:
            return JsonResponse({"error": "No restaurant found"}, status=404)

        # --- Date Range ---
        date_str = request.GET.get("date")
        start_str = request.GET.get("start_date")
        end_str = request.GET.get("end_date")

        if date_str:
            start_dt = make_aware(datetime.strptime(date_str, "%Y-%m-%d"))
            end_dt = start_dt + timedelta(days=1)
        elif start_str and end_str:
            start_dt = make_aware(datetime.strptime(start_str, "%Y-%m-%d"))
            end_dt = make_aware(datetime.strptime(end_str, "%Y-%m-%d")) + timedelta(days=1)
        else:
            today = datetime.now()
            start_dt = make_aware(datetime(today.year, today.month, today.day))
            end_dt = start_dt + timedelta(days=1)

        # --- Orders ---
        orders = Order.objects.filter(
            restaurant=restaurant,
            created_at__gte=start_dt,
            created_at__lt=end_dt
        )

        total_orders = orders.count()
        total_revenue = orders.aggregate(total=Sum("amount"))["total"] or Decimal(0)
        paid_orders = orders.filter(paid=True).count()

        # --- Billing / Stats ---
        tax_sum = total_revenue * Decimal("0.05")
        discounts_sum = total_revenue * Decimal("0.02")
        cancelled_orders = orders.filter(status="cancelled") if hasattr(Order, "STATUS_CHOICES") else []
        cancelled_count = cancelled_orders.count() if cancelled_orders else 0
        cancelled_value = Decimal(0)
        refunds_sum = Decimal(0)

        avg_order_value = total_revenue / total_orders if total_orders else Decimal(0)
        previous_period_total = total_revenue * Decimal("0.9")
        growth_pct = (
            ((total_revenue - previous_period_total) / previous_period_total) * 100
            if previous_period_total else 0
        )

        # --- Top Items ---
        items = (
            OrderItem.objects.filter(order__in=orders)
            .values("name")
            .annotate(total_qty=Sum("quantity"), total_revenue=Sum("price"))
            .order_by("-total_revenue")[:10]
        )

        # --- Top Tables ---
        table_summary = (
            orders.values("table_number")
            .annotate(order_count=Count("id"), total_sales=Sum("amount"))
            .order_by("-total_sales")[:10]
        )

        # --- Final JSON ---
        response = {
            "range": {
                "start": start_dt.isoformat(),
                "end": end_dt.isoformat(),
            },
            "totals": {
                "total_orders": total_orders,
                "paid_orders": paid_orders,
                "total_revenue": float(total_revenue),
                "avg_order_value": float(avg_order_value),
                "tax_sum": float(tax_sum),
                "discounts_sum": float(discounts_sum),
                "cancelled_count": cancelled_count,
                "cancelled_value": float(cancelled_value),
                "previous_period_total": float(previous_period_total),
                "growth_pct_vs_prev": round(growth_pct, 2),
            },
            "top_items": list(items),
            "table_summary": list(table_summary),
            "refunds_sum": float(refunds_sum),
        }

        return JsonResponse(response)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({"error": str(e)}, status=500)





# ith vere///////////////////////////////////////////////////////////
@login_required
def menu_management(request):
    restaurant = get_object_or_404(Restaurant, owner=request.user)
    categories = Category.objects.filter(restaurant=restaurant)
    category_form = CategoryForm()
    menuitem_form = MenuItemForm()

    if request.method == 'POST':
        if 'add_category' in request.POST:
            category_form = CategoryForm(request.POST)
            if category_form.is_valid():
                new_cat = category_form.save(commit=False)
                new_cat.restaurant = restaurant
                new_cat.save()
                return redirect('menu_management')
        elif 'add_menuitem' in request.POST:
            menuitem_form = MenuItemForm(request.POST, request.FILES)
            if menuitem_form.is_valid():
                menuitem_form.save()
                return redirect('menu_management')
        elif 'toggle_active' in request.POST:
            mi = MenuItem.objects.get(id=request.POST.get('item_id'))
            mi.active = not mi.active
            mi.save()
            return redirect('menu_management')
        elif 'delete_item' in request.POST:
            MenuItem.objects.get(id=request.POST.get('item_id')).delete()
            return redirect('menu_management')

    # Get a list of items per category
    per_cat_items = []
    for cat in categories:
        per_cat_items.append((cat, cat.items.all()))
    context = {
        "categories": categories,
        "per_cat_items": per_cat_items,
        "category_form": category_form,
        "menuitem_form": menuitem_form,
    }
    return render(request, "core/menu_management.html", context)

@login_required
def kitchen_dashboard(request):
    restaurant = get_object_or_404(Restaurant, owner=request.user)
    orders = Order.objects.filter(
        restaurant=restaurant,
        status__in=["pending", "preparing"]
    ).order_by("-created_at")
    if request.method == 'POST':
        order = Order.objects.get(id=request.POST.get('order_id'))
        next_status = request.POST.get('next_status')
        if next_status in dict(Order.STATUS_CHOICES):
            order.status = next_status
            order.save()
        return redirect('kitchen_dashboard')
    return render(request, "core/kitchen.html", {"orders": orders})





@csrf_exempt
def payment_success(request):
    if request.method == 'POST':
        data = request.POST  # Razorpay sends normal form data, not JSON.
        print(data)

        razorpay_order_id = data.get('razorpay_order_id')
        razorpay_payment_id = data.get('razorpay_payment_id')
        razorpay_signature = data.get('razorpay_signature')

        if not all([razorpay_order_id, razorpay_payment_id, razorpay_signature]):
            return render(request, HttpResponse("Invalid payment data. Not all Data", status=400))

        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

        try:
            # Verify the payment signature
            client.utility.verify_payment_signature({
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature
            })

            # Mark the order as paid
            order = Order.objects.get(razorpay_order_id=razorpay_order_id)
            order.paid = True
            order.razorpay_payment_id = razorpay_payment_id
            order.razorpay_signature = razorpay_signature
            order.status = 'completed'
            order.save()

            return render(request, "core/order_success.html", {'order': order})

        except razorpay.errors.SignatureVerificationError:
            return render(request, "core/order_failed.html", {
                "error": "Payment signature verification failed."
            })
        except Order.DoesNotExist:
            return render(request, "core/order_failed.html", {
                "error": "Order not found."
            })

    return render(request, "core/order_failed.html", {
        "error": "Invalid request method."
    })


# views.py
from django.http import JsonResponse
from .models import Order

def get_orders_json(request):
    orders = Order.objects.all().order_by('-created_at')
    data = {
        "orders": [
            {
                "id": o.id,
                "table_number": o.table_number,
                "status": o.status,
                "created_at": o.created_at.strftime("%Y-%m-%d %H:%M"),
                "items": [{"name": i.name, "quantity": i.quantity} for i in o.order_items.all()],
                
            }
            for o in orders
        ]
    }
    return JsonResponse(data)
