from django.shortcuts import render

from portfolio.models import Project
from django.http import HttpResponse
from django.http import JsonResponse


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

        "Sitemap: https://www.mitsol.com.se/sitemap.xml",

    ]

    return HttpResponse(

        "\n".join(lines),

        content_type="text/plain"

    )
    
def health_check(request):

    return JsonResponse(

        {

            'status': 'healthy',

            'service': 'MITSOL',

        }

    )