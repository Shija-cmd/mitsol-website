# Generated manually to update the Pharmacy Cloud SaaS destination.

from django.db import migrations


PHARMACY_CLOUD_URL = 'https://www.mitsol-pharmacy.cloud/'


def update_pharmacy_cloud_saas_url(apps, schema_editor):

    SoftwareProduct = apps.get_model(
        'software_store',
        'SoftwareProduct'
    )

    SoftwareProduct.objects.filter(
        name__icontains='Pharmacy Cloud'
    ).update(
        delivery_type='Web Application',
        sales_flow='SaaS Subscription',
        saas_signup_url=PHARMACY_CLOUD_URL
    )


class Migration(migrations.Migration):

    dependencies = [
        (
            'software_store',
            '0012_set_pharmacy_cloud_saas_url'
        ),
    ]

    operations = [
        migrations.RunPython(
            update_pharmacy_cloud_saas_url,
            migrations.RunPython.noop
        ),
    ]
