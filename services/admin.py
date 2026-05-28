from django.contrib import admin

from .models import Service


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):

    list_display = (

        'title',

        'created_at'

    )

    search_fields = (

        'title',

        'description'

    )

    readonly_fields = (

        'created_at',

    )

    fieldsets = (

        (

            'Service Information',

            {

                'fields': (

                    'title',

                    'description',

                    'icon',

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