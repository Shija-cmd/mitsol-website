from django.db.models import Q
from django.shortcuts import get_object_or_404, render

from .models import ResearchPublication
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


def research(request):

    publications = ResearchPublication.objects.filter(
        is_published=True
    )

    return render(

        request,

        'core/research.html',

        {

            'publications': publications,

        }

    )


def research_detail(request, slug):

    publication = get_object_or_404(
        ResearchPublication,
        slug=slug,
        is_published=True
    )

    first_research_area = ''

    if publication.research_area_list:

        first_research_area = publication.research_area_list[0]

    related_query = Q(
        category=publication.category
    )

    if first_research_area:

        related_query |= Q(
            research_area__icontains=first_research_area
        )

    related_research = ResearchPublication.objects.filter(
        is_published=True
    ).exclude(
        pk=publication.pk
    ).filter(
        related_query
    )[:3]

    return render(

        request,

        'core/research_detail.html',

        {

            'publication': publication,

            'related_research': related_research,

        }

    )
