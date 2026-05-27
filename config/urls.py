from django.contrib import admin

from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [

    path(
        'admin/',
        admin.site.urls
    ),

    path(
        '',
        include(
            'core.urls'
        )
    ),
    
    path(
        'services/',
        include('services.urls')
    ),
    
    path(
        'portfolio/',
        include('portfolio.urls')
    ),
    
    path(
        'contact/',
        include('contact.urls')
    ),
    
    path(
        'about/',
        include('about.urls')
    ),

]

urlpatterns += static(
    settings.MEDIA_URL,
    document_root=settings.MEDIA_ROOT
)