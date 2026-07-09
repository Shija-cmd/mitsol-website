from django.contrib import admin

from .models import ResearchPublication

admin.site.site_header = (
    "MITSOL Administration"
)

admin.site.site_title = (
    "MITSOL Admin Portal"
)

admin.site.index_title = (
    "Welcome to MITSOL Management System"
)


@admin.register(ResearchPublication)
class ResearchPublicationAdmin(admin.ModelAdmin):

    list_display = (
        'title',
        'category',
        'status',
        'publication_date',
        'featured',
    )

    list_filter = (
        'category',
        'status',
        'featured',
    )

    search_fields = (
        'title',
        'authors',
        'journal',
        'keywords',
        'research_area',
    )

    prepopulated_fields = {
        'slug': (
            'title',
        )
    }

    readonly_fields = (
        'views',
        'downloads',
        'created_at',
        'updated_at',
    )

    fieldsets = (
        (
            'Basic Information',
            {
                'fields': (
                    'title',
                    'slug',
                    'category',
                    'featured',
                    'status',
                    'is_published',
                )
            }
        ),
        (
            'Publication Details',
            {
                'fields': (
                    'authors',
                    'publication_date',
                    'journal_or_conference',
                    'journal',
                    'conference',
                    'publisher',
                    'volume',
                    'issue',
                    'pages',
                    'doi',
                    'isbn',
                    'external_link',
                )
            }
        ),
        (
            'Research Content',
            {
                'fields': (
                    'abstract',
                    'objectives',
                    'methodology',
                    'results',
                    'conclusion',
                    'future_work',
                )
            }
        ),
        (
            'Classification',
            {
                'fields': (
                    'research_area',
                    'keywords',
                    'technologies_used',
                )
            }
        ),
        (
            'Media',
            {
                'fields': (
                    'featured_image',
                    'pdf_file',
                    'presentation_slides',
                    'poster_image',
                    'dataset_link',
                    'youtube_url',
                    'github_url',
                    'demo_url',
                )
            }
        ),
        (
            'Metrics',
            {
                'fields': (
                    'views',
                    'downloads',
                    'citations',
                )
            }
        ),
        (
            'Collaboration',
            {
                'fields': (
                    'institution',
                    'supervisors',
                    'collaborators',
                    'funding_source',
                    'created_at',
                    'updated_at',
                )
            }
        ),
    )
