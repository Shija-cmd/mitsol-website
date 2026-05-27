from django.urls import path

from .views import portfolio_page


urlpatterns = [

    path(
        '',
        portfolio_page,
        name='portfolio'
    ),

]