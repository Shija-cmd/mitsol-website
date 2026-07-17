# Generated manually to add MITSOL Pharmacy Cloud to the portfolio.

from django.db import migrations


def add_pharmacy_cloud_project(apps, schema_editor):

    Project = apps.get_model(
        'portfolio',
        'Project'
    )

    Project.objects.get_or_create(
        title='MITSOL Pharmacy Cloud',
        defaults={
            'category': 'Cloud Web Application',
            'description': (
                'A SaaS pharmacy management platform where tenants can create '
                'an account, register their pharmacy, choose a subscription, '
                'and manage inventory, sales, purchases, payments, debts, '
                'receipts, reports, and staff access online.'
            ),
            'technologies': 'Django, SaaS, Cloud, Pharmacy Management',
        }
    )


def keep_pharmacy_cloud_project(apps, schema_editor):

    pass


class Migration(migrations.Migration):

    dependencies = [
        (
            'portfolio',
            '0003_project_category_project_image'
        ),
    ]

    operations = [
        migrations.RunPython(
            add_pharmacy_cloud_project,
            keep_pharmacy_cloud_project
        ),
    ]
