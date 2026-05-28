from django.shortcuts import render

from portfolio.models import Project
from django.http import HttpResponse


def home(request):

    projects = Project.objects.all()

    return render(

        request,

        'core/home.html',

        {

            'projects': projects

        }

    )
    
def robots_txt(request):

    lines = [

        "User-Agent: *",

        "Allow: /",

        "Sitemap: https://mitsol.com.se/sitemap.xml",

    ]

    return HttpResponse(

        "\n".join(lines),

        content_type="text/plain"

    )