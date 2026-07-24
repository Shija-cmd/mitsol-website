from django.db.models import F, Q
from django.shortcuts import get_object_or_404, redirect, render

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

    selected_category = request.GET.get(
        'category',
        ''
    ).strip()

    selected_status = request.GET.get(
        'status',
        ''
    ).strip()

    selected_area = request.GET.get(
        'area',
        ''
    ).strip()

    search_query = request.GET.get(
        'q',
        ''
    ).strip()

    if selected_category:

        publications = publications.filter(
            category=selected_category
        )

    if selected_status:

        publications = publications.filter(
            status=selected_status
        )

    if selected_area:

        publications = publications.filter(
            research_area__icontains=selected_area
        )

    if search_query:

        publications = publications.filter(
            Q(title__icontains=search_query)
            | Q(abstract__icontains=search_query)
            | Q(authors__icontains=search_query)
            | Q(keywords__icontains=search_query)
            | Q(research_area__icontains=search_query)
        )

    research_areas = []

    for publication in ResearchPublication.objects.filter(
        is_published=True
    ).exclude(
        research_area=''
    ):

        for area in publication.research_area_list:

            if area not in research_areas:

                research_areas.append(
                    area
                )

    return render(

        request,

        'core/research.html',

        {

            'publications': publications,
            'categories': ResearchPublication.Category.choices,
            'statuses': ResearchPublication.Status.choices,
            'research_areas': sorted(research_areas),
            'selected_category': selected_category,
            'selected_status': selected_status,
            'selected_area': selected_area,
            'search_query': search_query,

        }

    )


def research_detail(request, slug):

    publication = get_object_or_404(
        ResearchPublication,
        slug=slug,
        is_published=True
    )

    ResearchPublication.objects.filter(
        pk=publication.pk
    ).update(
        views=F('views') + 1
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


def research_pdf_download(request, slug):

    publication = get_object_or_404(
        ResearchPublication,
        slug=slug,
        is_published=True,
        pdf_file__isnull=False
    )

    ResearchPublication.objects.filter(
        pk=publication.pk
    ).update(
        downloads=F('downloads') + 1
    )

    return redirect(
        publication.pdf_file.url
    )
