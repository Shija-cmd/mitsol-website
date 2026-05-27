from django.shortcuts import render

from .models import Project


def portfolio_page(request):

    projects = Project.objects.all()

    return render(
        request,
        'portfolio/portfolio.html',
        {
            'projects': projects
        }
    )