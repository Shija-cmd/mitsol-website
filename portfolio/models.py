from django.db import models


class Project(models.Model):

    title = models.CharField(
        max_length=200
    )

    category = models.CharField(
        max_length=100,
        default='Software Development'
    )

    description = models.TextField()

    technologies = models.CharField(
        max_length=300
    )

    image = models.ImageField(
        upload_to='portfolio/',
        blank=True,
        null=True
    )

    project_url = models.URLField(
        blank=True,
        null=True
    )

    github_url = models.URLField(
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):

        return self.title