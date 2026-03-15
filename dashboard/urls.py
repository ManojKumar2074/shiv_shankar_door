from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('login/',  views.dashboard_login,  name='dashboard_login'),
    path('logout/', views.dashboard_logout, name='dashboard_logout'),

    # Home
    path('', views.dashboard_home, name='dashboard_home'),

    # Products
    path('products/',                    views.product_list,   name='dashboard_products'),
    path('products/add/',                views.product_add,    name='dashboard_product_add'),
    path('products/<int:pk>/edit/',      views.product_edit,   name='dashboard_product_edit'),
    path('products/<int:pk>/delete/',    views.product_delete, name='dashboard_product_delete'),
    path('products/<int:pk>/image/<slug:slot>/remove/', views.remove_image, name='dashboard_remove_image'),

    # Inquiries
    path('inquiries/',                        views.inquiry_list,          name='dashboard_inquiries'),
    path('inquiries/<int:pk>/status/',        views.inquiry_update_status, name='dashboard_inquiry_status'),
]