from django.db import migrations
from django.utils.text import slugify


INITIAL_CATEGORIES = [
    'Software Development',
    'Python Programming',
    'Django Web Development',
    'Artificial Intelligence',
    'Machine Learning',
    'Cybersecurity',
    'Networking',
    'Cloud Computing',
    'Database Management',
    'Data Analysis',
    'Research Computing',
    'Graphic Design',
    'Digital Business Skills',
    'ICT Training for Institutions',
]


def create_initial_learning_data(apps, schema_editor):

    CourseCategory = apps.get_model(
        'learning',
        'CourseCategory'
    )
    Group = apps.get_model(
        'auth',
        'Group'
    )

    for name in INITIAL_CATEGORIES:

        CourseCategory.objects.get_or_create(
            name=name,
            defaults={
                'slug': slugify(name),
                'description': f'{name} courses and training programmes.',
            }
        )

    for group_name in (
        'Student',
        'Instructor',
    ):

        Group.objects.get_or_create(
            name=group_name
        )


class Migration(migrations.Migration):

    dependencies = [
        (
            'auth',
            '0012_alter_user_first_name_max_length'
        ),
        (
            'learning',
            '0001_initial'
        ),
    ]

    operations = [
        migrations.RunPython(
            create_initial_learning_data,
            migrations.RunPython.noop
        ),
    ]
