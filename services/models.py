from django.db import models


class Service(models.Model):

    title = models.CharField(
        max_length=200
    )

    description = models.TextField()

    icon = models.CharField(
        max_length=100,
        help_text='Example: fas fa-code'
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):

        return self.title