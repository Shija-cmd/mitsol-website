# Generated manually for Stage 2 quiz workflow.

import django.core.validators
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('learning', '0003_courseannouncement_notification'),
    ]

    operations = [
        migrations.CreateModel(
            name='Quiz',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=220)),
                ('slug', models.SlugField(blank=True, max_length=240)),
                ('instructions', models.TextField(blank=True)),
                ('passing_score', models.PositiveIntegerField(default=50, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)])),
                ('time_limit_minutes', models.PositiveIntegerField(blank=True, null=True)),
                ('attempts_allowed', models.PositiveIntegerField(default=1, validators=[django.core.validators.MinValueValidator(1)])),
                ('randomise_questions', models.BooleanField(default=False)),
                ('randomise_choices', models.BooleanField(default=False)),
                ('show_score_after_submission', models.BooleanField(default=True)),
                ('show_correct_answers', models.BooleanField(default=False)),
                ('is_compulsory', models.BooleanField(default=True)),
                ('is_published', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('lesson', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='quiz', to='learning.lesson')),
            ],
            options={
                'ordering': ('lesson__module__course__title', 'lesson__module__order', 'lesson__order'),
            },
        ),
        migrations.CreateModel(
            name='Question',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('question_text', models.TextField()),
                ('question_type', models.CharField(choices=[('Multiple Choice', 'Multiple Choice'), ('Multiple Select', 'Multiple Select'), ('True or False', 'True or False'), ('Short Answer', 'Short Answer')], default='Multiple Choice', max_length=40)),
                ('marks', models.DecimalField(decimal_places=2, default=1, max_digits=7)),
                ('order', models.PositiveIntegerField(default=1)),
                ('explanation', models.TextField(blank=True)),
                ('is_required', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('quiz', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='questions', to='learning.quiz')),
            ],
            options={
                'ordering': ('quiz', 'order'),
            },
        ),
        migrations.CreateModel(
            name='Choice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('choice_text', models.CharField(max_length=500)),
                ('is_correct', models.BooleanField(default=False)),
                ('order', models.PositiveIntegerField(default=1)),
                ('question', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='choices', to='learning.question')),
            ],
            options={
                'ordering': ('question', 'order'),
            },
        ),
        migrations.CreateModel(
            name='QuizAttempt',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('attempt_number', models.PositiveIntegerField()),
                ('started_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('submitted_at', models.DateTimeField(blank=True, null=True)),
                ('expires_at', models.DateTimeField(blank=True, null=True)),
                ('status', models.CharField(choices=[('In Progress', 'In Progress'), ('Submitted', 'Submitted'), ('Awaiting Manual Grading', 'Awaiting Manual Grading'), ('Graded', 'Graded'), ('Expired', 'Expired')], default='In Progress', max_length=40)),
                ('objective_marks_awarded', models.DecimalField(decimal_places=2, default=0, max_digits=8)),
                ('manual_marks_awarded', models.DecimalField(decimal_places=2, default=0, max_digits=8)),
                ('total_marks_awarded', models.DecimalField(decimal_places=2, default=0, max_digits=8)),
                ('total_possible_marks', models.DecimalField(decimal_places=2, default=0, max_digits=8)),
                ('percentage', models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ('passed', models.BooleanField(default=False)),
                ('requires_manual_grading', models.BooleanField(default=False)),
                ('instructor_feedback', models.TextField(blank=True)),
                ('graded_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('enrolment', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='quiz_attempts', to='learning.enrolment')),
                ('graded_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='graded_quiz_attempts', to=settings.AUTH_USER_MODEL)),
                ('quiz', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attempts', to='learning.quiz')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='quiz_attempts', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('-started_at',),
            },
        ),
        migrations.CreateModel(
            name='StudentAnswer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text_answer', models.TextField(blank=True)),
                ('objective_marks_awarded', models.DecimalField(decimal_places=2, default=0, max_digits=7)),
                ('manual_marks_awarded', models.DecimalField(decimal_places=2, default=0, max_digits=7)),
                ('is_correct', models.BooleanField(default=False)),
                ('instructor_feedback', models.TextField(blank=True)),
                ('graded_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('attempt', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='answers', to='learning.quizattempt')),
                ('graded_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='graded_quiz_answers', to=settings.AUTH_USER_MODEL)),
                ('question', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='student_answers', to='learning.question')),
                ('selected_choices', models.ManyToManyField(blank=True, related_name='student_answers', to='learning.choice')),
            ],
            options={
                'ordering': ('question__order',),
            },
        ),
        migrations.AddIndex(
            model_name='quiz',
            index=models.Index(fields=['slug'], name='learning_qu_slug_d912e9_idx'),
        ),
        migrations.AddIndex(
            model_name='quiz',
            index=models.Index(fields=['is_published'], name='learning_qu_is_publ_7dbd38_idx'),
        ),
        migrations.AddIndex(
            model_name='quiz',
            index=models.Index(fields=['created_at'], name='learning_qu_created_0e42de_idx'),
        ),
        migrations.AddConstraint(
            model_name='quiz',
            constraint=models.UniqueConstraint(fields=('lesson', 'slug'), name='unique_quiz_slug_per_lesson'),
        ),
        migrations.AddIndex(
            model_name='question',
            index=models.Index(fields=['quiz', 'order'], name='learning_qu_quiz_id_218b17_idx'),
        ),
        migrations.AddIndex(
            model_name='question',
            index=models.Index(fields=['question_type'], name='learning_qu_questio_c8f546_idx'),
        ),
        migrations.AddConstraint(
            model_name='question',
            constraint=models.UniqueConstraint(fields=('quiz', 'order'), name='unique_question_order_per_quiz'),
        ),
        migrations.AddConstraint(
            model_name='choice',
            constraint=models.UniqueConstraint(fields=('question', 'order'), name='unique_choice_order_per_question'),
        ),
        migrations.AddConstraint(
            model_name='choice',
            constraint=models.UniqueConstraint(fields=('question', 'choice_text'), name='unique_choice_text_per_question'),
        ),
        migrations.AddIndex(
            model_name='quizattempt',
            index=models.Index(fields=['student'], name='learning_qu_student_b59012_idx'),
        ),
        migrations.AddIndex(
            model_name='quizattempt',
            index=models.Index(fields=['quiz'], name='learning_qu_quiz_id_fe08bf_idx'),
        ),
        migrations.AddIndex(
            model_name='quizattempt',
            index=models.Index(fields=['status'], name='learning_qu_status_2cdb71_idx'),
        ),
        migrations.AddIndex(
            model_name='quizattempt',
            index=models.Index(fields=['attempt_number'], name='learning_qu_attempt_2388b3_idx'),
        ),
        migrations.AddIndex(
            model_name='quizattempt',
            index=models.Index(fields=['enrolment'], name='learning_qu_enrolme_b0dc59_idx'),
        ),
        migrations.AddConstraint(
            model_name='quizattempt',
            constraint=models.UniqueConstraint(fields=('student', 'quiz', 'attempt_number'), name='unique_quiz_attempt_number_per_student'),
        ),
        migrations.AddConstraint(
            model_name='quizattempt',
            constraint=models.UniqueConstraint(condition=models.Q(('status', 'In Progress')), fields=('student', 'quiz'), name='unique_active_quiz_attempt_per_student'),
        ),
        migrations.AddConstraint(
            model_name='studentanswer',
            constraint=models.UniqueConstraint(fields=('attempt', 'question'), name='unique_answer_per_attempt_question'),
        ),
    ]
