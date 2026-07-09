# Generated manually for research publication management.

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='ResearchPublication',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID'
                    )
                ),
                (
                    'title',
                    models.CharField(
                        max_length=255
                    )
                ),
                (
                    'category',
                    models.CharField(
                        choices=[
                            (
                                'Publication',
                                'Publication'
                            ),
                            (
                                'Research Project',
                                'Research Project'
                            ),
                            (
                                'Academic Work',
                                'Academic Work'
                            ),
                            (
                                'Case Study',
                                'Case Study'
                            ),
                        ],
                        default='Research Project',
                        max_length=50
                    )
                ),
                (
                    'abstract',
                    models.TextField()
                ),
                (
                    'authors',
                    models.CharField(
                        blank=True,
                        max_length=255
                    )
                ),
                (
                    'publication_date',
                    models.DateField(
                        blank=True,
                        null=True
                    )
                ),
                (
                    'journal_or_conference',
                    models.CharField(
                        blank=True,
                        max_length=255
                    )
                ),
                (
                    'external_link',
                    models.URLField(
                        blank=True,
                        max_length=1000
                    )
                ),
                (
                    'pdf_file',
                    models.FileField(
                        blank=True,
                        null=True,
                        upload_to='research/publications/'
                    )
                ),
                (
                    'is_featured',
                    models.BooleanField(
                        default=False
                    )
                ),
                (
                    'is_published',
                    models.BooleanField(
                        default=True
                    )
                ),
                (
                    'created_at',
                    models.DateTimeField(
                        auto_now_add=True
                    )
                ),
                (
                    'updated_at',
                    models.DateTimeField(
                        auto_now=True
                    )
                ),
            ],
            options={
                'ordering': (
                    '-is_featured',
                    '-publication_date',
                    '-created_at',
                ),
            },
        ),
    ]
