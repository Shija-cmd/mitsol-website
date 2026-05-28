from django.contrib import admin
from django.utils.html import format_html

from .models import Project


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):

    list_display = (

        'thumbnail',

        'title',

        'category',

        'technologies',

        'created_at'

    )

    search_fields = (

        'title',

        'category',

        'technologies'

    )

    list_filter = (

        'category',

        'created_at'

    )

    readonly_fields = (

        'created_at',

        'thumbnail_preview'

    )

    fieldsets = (

        (

            'Project Information',

            {

                'fields': (

                    'title',

                    'category',

                    'description',

                    'technologies'

                )

            }

        ),

        (

            'Media & Links',

            {

                'fields': (

                    'image',

                    'thumbnail_preview',

                    'project_url',

                    'github_url'

                )

            }

        ),

        (

            'Metadata',

            {

                'fields': (

                    'created_at',

                )

            }

        ),

    )

    def thumbnail(self, obj):

        if obj.image:

            return format_html(

                '<img src="{}" width="60" style="border-radius:8px;" />',

                obj.image.url

            )

        return "-"

    thumbnail.short_description = 'Preview'


    def thumbnail_preview(self, obj):

        if obj.image:

            return format_html(

                '<img src="{}" width="250" style="border-radius:10px;" />',

                obj.image.url

            )

        return "No image uploaded"

    thumbnail_preview.short_description = 'Image Preview'