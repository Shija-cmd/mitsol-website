# Generated manually to link the Pharmacy Cloud portfolio item to the SaaS app.

from django.db import migrations


PHARMACY_SAAS_URL = 'https://mitsol-pharmacy-saas.onrender.com/'


def set_pharmacy_cloud_project_url(apps, schema_editor):

    Project = apps.get_model(
        'portfolio',
        'Project'
    )

    Project.objects.filter(
        title='MITSOL Pharmacy Cloud'
    ).update(
        project_url=PHARMACY_SAAS_URL
    )


class Migration(migrations.Migration):

    dependencies = [
        (
            'portfolio',
            '0004_add_pharmacy_cloud_project'
        ),
    ]

    operations = [
        migrations.RunPython(
            set_pharmacy_cloud_project_url,
            migrations.RunPython.noop
        ),
    ]
