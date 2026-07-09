# Generated manually for adding product delivery types.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            'software_store',
            '0006_softwareproduct_youtube_activation_url_and_more'
        ),
    ]

    operations = [
        migrations.AddField(
            model_name='softwareproduct',
            name='delivery_type',
            field=models.CharField(
                choices=[
                    (
                        'Desktop Software',
                        'Desktop Software'
                    ),
                    (
                        'Web Application',
                        'Web Application'
                    ),
                ],
                default='Desktop Software',
                max_length=50
            ),
        ),
    ]
