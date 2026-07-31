from django.contrib import admin

from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.sitemaps.views import sitemap
from django.http import Http404
from django.views.static import serve
from core.sitemaps import (
    LearningCategorySitemap,
    LearningCourseSitemap,
    ResearchPublicationSitemap,
    SoftwareProductSitemap,
    StaticViewSitemap,
)
from core.views import health_check, robots_txt
from software_store.urls import api_urlpatterns

sitemaps = {

    'static': StaticViewSitemap,
    'software': SoftwareProductSitemap,
    'research': ResearchPublicationSitemap,
    'learning_courses': LearningCourseSitemap,
    'learning_categories': LearningCategorySitemap,

}


def disabled_default_admin(request, *args, **kwargs):

    raise Http404


urlpatterns = [

    path(
        f'{settings.DJANGO_ADMIN_URL}/',
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

    path(
        'software/',
        include('software_store.urls')
    ),

    path(
        'learn/',
        include('learning.urls')
    ),

    path(
        'accounts/',
        include('django.contrib.auth.urls')
    ),

    path(
        'api/',
        include(api_urlpatterns)
    ),
    
    path(

        'sitemap.xml',

        sitemap,

        {'sitemaps': sitemaps},

        name='django.contrib.sitemaps.views.sitemap'

    ),
    
    path(

        'robots.txt',

        robots_txt,

        name='robots'

    ),
    
    path(

        'health/',

        health_check,

        name='health'

    ),

]

if settings.DJANGO_ADMIN_URL != 'admin':

    urlpatterns += [
        path(
            'admin/',
            disabled_default_admin,
            name='disabled_default_admin'
        ),
    ]

if settings.DEBUG and not getattr(settings, 'CLOUDINARY_ENABLED', False):

    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )

elif not getattr(settings, 'CLOUDINARY_ENABLED', False):

    urlpatterns += [
        re_path(
            r'^media/(?P<path>.*)$',
            serve,
            {
                'document_root': settings.MEDIA_ROOT
            }
        ),
    ]
