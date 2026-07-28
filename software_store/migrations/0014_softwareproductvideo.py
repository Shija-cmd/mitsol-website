# Generated manually to support multiple demo videos per software product.

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        (
            'software_store',
            '0013_update_pharmacy_cloud_saas_url'
        ),
    ]

    operations = [
        migrations.CreateModel(
            name='SoftwareProductVideo',
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
                        help_text='Example: Stock management demo, Sales demo, Reports overview.',
                        max_length=200
                    )
                ),
                (
                    'youtube_url',
                    models.URLField(
                        help_text='Paste one YouTube video URL here.',
                        max_length=1000
                    )
                ),
                (
                    'sort_order',
                    models.PositiveIntegerField(
                        default=0
                    )
                ),
                (
                    'product',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='demo_videos',
                        to='software_store.softwareproduct'
                    )
                ),
            ],
            options={
                'ordering': (
                    'sort_order',
                    'title',
                ),
            },
        ),
    ]
