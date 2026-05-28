from django.contrib import admin

from .models import Project

from django.contrib import admin

from .models import Project


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):

    list_display = (

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