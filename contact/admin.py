from django.contrib import admin

from .models import ContactMessage


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):

    list_display = (

        'name',

        'email',

        'created_at'

    )

    search_fields = (

        'name',

        'email',

        'message'

    )

    list_filter = (

        'created_at',

    )

    readonly_fields = (

        'created_at',

    )

    fieldsets = (

        (

            'Sender Details',

            {

                'fields': (

                    'name',

                    'email',

                )

            }

        ),

        (

            'Message',

            {

                'fields': (

                    'message',

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
    
    actions = ['mark_as_reviewed']
    
    def mark_as_reviewed(
        self,
        request,
        queryset
    ):

        queryset.update(reviewed=True)

    mark_as_reviewed.short_description = (
        "Mark selected messages as reviewed"
    )