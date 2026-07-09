from django.urls import path

from . import views


urlpatterns = [

    path(
        '',
        views.product_list,
        name='software_product_list'
    ),

    path(
        'order/<slug:product_slug>/',
        views.order_product,
        name='software_order'
    ),

    path(
        'download/<uuid:license_key>/',
        views.download_software,
        name='software_download'
    ),
    
    path(
        "download/<uuid:license_key>/",
        views.download_software,
        name="download_software"
    ),

    path(
        'download/<str:license_key>/',
        views.download_software_fallback,
        name='software_download_fallback'
    ),

    path(
        '<slug:product_slug>/',
        views.product_detail,
        name='software_product_detail'
    ),

]


api_urlpatterns = [

    path(
        'licenses/activate/',
        views.activate_license,
        name='software_license_activate'
    ),

    path(
        'licenses/verify/',
        views.verify_license,
        name='software_license_verify'
    ),

    path(
        'software/<slug:product_slug>/latest/',
        views.latest_software,
        name='software_latest'
    ),

]
