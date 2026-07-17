# Generated manually to mark Pharmacy Cloud products as SaaS subscriptions.

from django.db import migrations


def mark_pharmacy_cloud_as_saas(apps, schema_editor):

    SoftwareProduct = apps.get_model(
        'software_store',
        'SoftwareProduct'
    )

    SoftwareProduct.objects.filter(
        name__icontains='Pharmacy Cloud'
    ).update(
        delivery_type='Web Application',
        sales_flow='SaaS Subscription'
    )


class Migration(migrations.Migration):

    dependencies = [
        (
            'software_store',
            '0010_softwareproduct_sales_flow'
        ),
    ]

    operations = [
        migrations.RunPython(
            mark_pharmacy_cloud_as_saas,
            migrations.RunPython.noop
        ),
    ]
