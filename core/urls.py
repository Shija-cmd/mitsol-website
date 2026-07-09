from django.urls import path

from .views import home, research, research_detail

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
        'robots.txt', 
        robots_txt
    ),

]
