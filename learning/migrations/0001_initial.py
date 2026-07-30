# Generated manually for MITSOL Learn Phase 1.

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='CourseCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=150, unique=True)),
                ('slug', models.SlugField(blank=True, max_length=170, unique=True)),
                ('description', models.TextField(blank=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name_plural': 'Course categories',
                'ordering': ('name',),
            },
        ),
        migrations.CreateModel(
            name='Course',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=220)),
                ('slug', models.SlugField(blank=True, max_length=240, unique=True)),
                ('short_description', models.CharField(max_length=300)),
                ('full_description', models.TextField()),
                ('cover_image', models.ImageField(blank=True, null=True, upload_to='learning/course_covers/')),
                ('promotional_video_url', models.URLField(blank=True, max_length=1000)),
                ('level', models.CharField(choices=[('Beginner', 'Beginner'), ('Intermediate', 'Intermediate'), ('Advanced', 'Advanced'), ('All Levels', 'All Levels')], default='All Levels', max_length=30)),
                ('language', models.CharField(default='English', max_length=80)),
                ('delivery_mode', models.CharField(choices=[('Self-Paced', 'Self-Paced'), ('Live Online', 'Live Online'), ('Blended', 'Blended'), ('Face-to-Face', 'Face-to-Face')], default='Self-Paced', max_length=40)),
                ('estimated_duration', models.CharField(blank=True, help_text='Example: 6 weeks, 20 hours, or 12 lessons.', max_length=100)),
                ('price', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('discount_price', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('is_free', models.BooleanField(default=True)),
                ('learning_outcomes', models.TextField(blank=True, help_text='One outcome per line.')),
                ('requirements', models.TextField(blank=True, help_text='One requirement per line.')),
                ('target_audience', models.TextField(blank=True, help_text='One audience group per line.')),
                ('status', models.CharField(choices=[('Draft', 'Draft'), ('Pending Review', 'Pending Review'), ('Published', 'Published'), ('Archived', 'Archived')], default='Draft', max_length=30)),
                ('is_featured', models.BooleanField(default=False)),
                ('is_published', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='courses', to='learning.coursecategory')),
                ('instructor', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='learning_courses', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('-is_featured', '-created_at'),
                'indexes': [
                    models.Index(fields=['slug'], name='learning_co_slug_42b789_idx'),
                    models.Index(fields=['category'], name='learning_co_categor_7f5139_idx'),
                    models.Index(fields=['instructor'], name='learning_co_instruc_c28a74_idx'),
                    models.Index(fields=['status'], name='learning_co_status_064f7f_idx'),
                    models.Index(fields=['is_published'], name='learning_co_is_publ_0180a6_idx'),
                    models.Index(fields=['is_featured'], name='learning_co_is_feat_2ae4e2_idx'),
                    models.Index(fields=['created_at'], name='learning_co_created_91bc8a_idx'),
                ],
            },
        ),
        migrations.CreateModel(
            name='InstructorProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(blank=True, max_length=150)),
                ('bio', models.TextField(blank=True)),
                ('expertise', models.CharField(blank=True, help_text='Separate multiple values using commas.', max_length=255)),
                ('photo', models.ImageField(blank=True, null=True, upload_to='learning/instructors/')),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='instructor_profile', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('user__first_name', 'user__last_name', 'user__username'),
            },
        ),
        migrations.CreateModel(
            name='Module',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=220)),
                ('description', models.TextField(blank=True)),
                ('order', models.PositiveIntegerField(default=1)),
                ('is_published', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('course', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='modules', to='learning.course')),
            ],
            options={
                'ordering': ('order', 'title'),
                'constraints': [models.UniqueConstraint(fields=('course', 'order'), name='unique_module_order_per_course')],
            },
        ),
        migrations.CreateModel(
            name='Lesson',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=220)),
                ('slug', models.SlugField(blank=True, max_length=240)),
                ('lesson_type', models.CharField(choices=[('Video', 'Video'), ('Text', 'Text'), ('Document', 'Document'), ('External Resource', 'External Resource'), ('Quiz', 'Quiz'), ('Assignment', 'Assignment'), ('Live Session', 'Live Session')], default='Text', max_length=40)),
                ('written_content', models.TextField(blank=True)),
                ('video_url', models.URLField(blank=True, max_length=1000)),
                ('video_file', models.FileField(blank=True, null=True, upload_to='learning/videos/', validators=[django.core.validators.FileExtensionValidator(['mp4', 'mov', 'webm', 'm4v'])])),
                ('downloadable_file', models.FileField(blank=True, null=True, upload_to='learning/documents/', validators=[django.core.validators.FileExtensionValidator(['pdf', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx', 'txt', 'zip'])])),
                ('source_code_file', models.FileField(blank=True, null=True, upload_to='learning/documents/source_code/', validators=[django.core.validators.FileExtensionValidator(['zip'])])),
                ('external_resource_url', models.URLField(blank=True, max_length=1000)),
                ('duration_minutes', models.PositiveIntegerField(default=0)),
                ('order', models.PositiveIntegerField(default=1)),
                ('is_preview', models.BooleanField(default=False)),
                ('is_compulsory', models.BooleanField(default=True)),
                ('is_published', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('module', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='lessons', to='learning.module')),
            ],
            options={
                'ordering': ('module__order', 'order', 'title'),
                'constraints': [
                    models.UniqueConstraint(fields=('module', 'slug'), name='unique_lesson_slug_per_module'),
                    models.UniqueConstraint(fields=('module', 'order'), name='unique_lesson_order_per_module'),
                ],
            },
        ),
        migrations.CreateModel(
            name='Enrolment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('Pending', 'Pending'), ('Active', 'Active'), ('Completed', 'Completed'), ('Suspended', 'Suspended'), ('Cancelled', 'Cancelled')], default='Pending', max_length=30)),
                ('payment_status', models.CharField(choices=[('Not Required', 'Not Required'), ('Pending', 'Pending'), ('Paid', 'Paid'), ('Rejected', 'Rejected'), ('Refunded', 'Refunded')], default='Pending', max_length=30)),
                ('enrolled_at', models.DateTimeField(auto_now_add=True)),
                ('activated_at', models.DateTimeField(blank=True, null=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('progress_percentage', models.PositiveIntegerField(default=0, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)])),
                ('is_active', models.BooleanField(default=False)),
                ('course', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='enrolments', to='learning.course')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='learning_enrolments', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('-enrolled_at',),
                'constraints': [models.UniqueConstraint(fields=('student', 'course'), name='unique_student_course_enrolment')],
            },
        ),
        migrations.CreateModel(
            name='LessonProgress',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_completed', models.BooleanField(default=False)),
                ('started_at', models.DateTimeField(auto_now_add=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('last_accessed_at', models.DateTimeField(auto_now=True)),
                ('enrolment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='lesson_progress', to='learning.enrolment')),
                ('lesson', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='progress_records', to='learning.lesson')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='lesson_progress', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('-last_accessed_at',),
                'constraints': [models.UniqueConstraint(fields=('student', 'lesson'), name='unique_student_lesson_progress')],
            },
        ),
    ]
