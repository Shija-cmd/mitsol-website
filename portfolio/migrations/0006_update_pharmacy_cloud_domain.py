# Generated manually to point Pharmacy Cloud portfolio traffic at the public SaaS domain.

from django.db import migrations


PHARMACY_CLOUD_URL = 'https://www.mitsol-pharmacy.cloud/'


def update_pharmacy_cloud_domain(apps, schema_editor):

    Project = apps.get_model(
        'portfolio',
        'Project'
    )

    Project.objects.filter(
        title='MITSOL Pharmacy Cloud'
    ).update(
        project_url=PHARMACY_CLOUD_URL
    )


class Migration(migrations.Migration):

    dependencies = [
        (
            'portfolio',
            '0005_set_pharmacy_cloud_url'
        ),
    ]

    operations = [
        migrations.RunPython(
            update_pharmacy_cloud_domain,
            migrations.RunPython.noop
        ),
    ]
