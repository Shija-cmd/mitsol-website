from django.urls import path

from .views import home, research, research_detail, research_pdf_download

from core.views import robots_txt


urlpatterns = [

    path(
        '',
        home,
        name='home'
    ),

    path(
        'research/',
        research,
        name='research'
    ),

    path(
        'research/<slug:slug>/',
        research_detail,
        name='research_detail'
    ),

    path(
        'research/<slug:slug>/download/',
        research_pdf_download,
        name='research_pdf_download'
    ),
    
    path(
        'robots.txt', 
        robots_txt
    ),

]
