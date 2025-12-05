from django.contrib import admin
from django.urls import path, include
from core import views
from django.conf import settings
from django.conf.urls.static import static





urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name="home"),
    # Customer-facing routes
    path('<str:restaurant_code>/<str:table_number>/menu/', views.customer_menu, name="customer_menu"),
    path('<str:restaurant_code>/<str:table_number>/checkout/', views.customer_checkout, name="customer_checkout"),
    path('payment-success/', views.payment_success, name='payment_success'),

    # Dashboard & analytics
    path('dashboard/', views.dashboard, name="dashboard"),
    path('dashboard/data/', views.dashboard_data, name="dashboard_data"),

    # Management / kitchen
    path('manage/', views.menu_management, name="menu_management"),
    path('kitchen/', views.kitchen_dashboard, name="kitchen_dashboard"),

    # API routes
    path('get/', views.get_orders_json, name="get_orders_json"),
    

]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)