from urllib.parse import parse_qs, urlparse
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify


SAFE_DOCUMENT_EXTENSIONS = [
    'pdf',
    'doc',
    'docx',
    'ppt',
    'pptx',
    'xls',
    'xlsx',
    'txt',
    'zip',
]

SAFE_VIDEO_EXTENSIONS = [
    'mp4',
    'mov',
    'webm',
    'm4v',
]

SAFE_ASSIGNMENT_EXTENSIONS = [
    'pdf',
    'doc',
    'docx',
    'txt',
    'zip',
    'py',
    'ipynb',
    'csv',
    'xlsx',
    'ppt',
    'pptx',
    'jpg',
    'jpeg',
    'png',
]

DANGEROUS_ASSIGNMENT_EXTENSIONS = [
    'exe',
    'bat',
    'cmd',
    'com',
    'msi',
    'sh',
    'ps1',
    'dll',
    'apk',
    'jar',
]

PAYMENT_PROOF_EXTENSIONS = [
    'pdf',
    'jpg',
    'jpeg',
    'png',
    'webp',
]

DANGEROUS_PAYMENT_EXTENSIONS = DANGEROUS_ASSIGNMENT_EXTENSIONS + [
    'html',
    'htm',
    'js',
    'php',
]


def assignment_submission_upload_to(instance, filename):

    safe_name = Path(filename).name
    assignment_id = instance.assignment_id or 'new-assignment'
    student_id = instance.student_id or 'new-student'
    course_id = (
        instance.assignment.lesson.module.course_id
        if instance.assignment_id
        else 'new-course'
    )

    return (
        f'learning/assignments/{course_id}/'
        f'{assignment_id}/{student_id}/{safe_name}'
    )


def payment_proof_upload_to(instance, filename):

    safe_name = Path(filename).name
    course_id = instance.course_id or 'new-course'
    student_id = instance.student_id or 'new-student'

    return f'learning/payment_proofs/{course_id}/{student_id}/{safe_name}'


class CourseCategory(models.Model):

    name = models.CharField(
        max_length=150,
        unique=True
    )

    slug = models.SlugField(
        max_length=170,
        unique=True,
        blank=True
    )

    description = models.TextField(
        blank=True
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:

        ordering = (
            'name',
        )

        verbose_name_plural = 'Course categories'

    def __str__(self):

        return self.name

    def save(self, *args, **kwargs):

        if not self.slug:

            self.slug = self.generate_unique_slug()

        super().save(*args, **kwargs)

    def generate_unique_slug(self):

        base_slug = slugify(self.name) or 'category'
        slug = base_slug
        counter = 2

        while CourseCategory.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            slug = f'{base_slug}-{counter}'
            counter += 1

        return slug

    def get_absolute_url(self):

        return reverse(
            'learning:category',
            args=[
                self.slug,
            ]
        )


class InstructorProfile(models.Model):

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='instructor_profile'
    )

    title = models.CharField(
        max_length=150,
        blank=True
    )

    bio = models.TextField(
        blank=True
    )

    expertise = models.CharField(
        max_length=255,
        blank=True,
        help_text='Separate multiple values using commas.'
    )

    photo = models.ImageField(
        upload_to='learning/instructors/',
        blank=True,
        null=True
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:

        ordering = (
            'user__first_name',
            'user__last_name',
            'user__username',
        )

    def __str__(self):

        return self.display_name

    @property
    def display_name(self):

        full_name = self.user.get_full_name()

        return full_name or self.user.username

    @property
    def expertise_list(self):

        return [
            item.strip()
            for item in self.expertise.split(',')
            if item.strip()
        ]


class Course(models.Model):

    class Level(models.TextChoices):

        BEGINNER = 'Beginner', 'Beginner'
        INTERMEDIATE = 'Intermediate', 'Intermediate'
        ADVANCED = 'Advanced', 'Advanced'
        ALL_LEVELS = 'All Levels', 'All Levels'

    class DeliveryMode(models.TextChoices):

        SELF_PACED = 'Self-Paced', 'Self-Paced'
        LIVE_ONLINE = 'Live Online', 'Live Online'
        BLENDED = 'Blended', 'Blended'
        FACE_TO_FACE = 'Face-to-Face', 'Face-to-Face'

    class Status(models.TextChoices):

        DRAFT = 'Draft', 'Draft'
        PENDING_REVIEW = 'Pending Review', 'Pending Review'
        PUBLISHED = 'Published', 'Published'
        ARCHIVED = 'Archived', 'Archived'

    instructor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='learning_courses'
    )

    category = models.ForeignKey(
        CourseCategory,
        on_delete=models.PROTECT,
        related_name='courses'
    )

    title = models.CharField(
        max_length=220
    )

    slug = models.SlugField(
        max_length=240,
        unique=True,
        blank=True
    )

    short_description = models.CharField(
        max_length=300
    )

    full_description = models.TextField()

    cover_image = models.ImageField(
        upload_to='learning/course_covers/',
        blank=True,
        null=True
    )

    promotional_video_url = models.URLField(
        max_length=1000,
        blank=True
    )

    level = models.CharField(
        max_length=30,
        choices=Level.choices,
        default=Level.ALL_LEVELS
    )

    language = models.CharField(
        max_length=80,
        default='English'
    )

    delivery_mode = models.CharField(
        max_length=40,
        choices=DeliveryMode.choices,
        default=DeliveryMode.SELF_PACED
    )

    estimated_duration = models.CharField(
        max_length=100,
        blank=True,
        help_text='Example: 6 weeks, 20 hours, or 12 lessons.'
    )

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    discount_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )

    is_free = models.BooleanField(
        default=True
    )

    learning_outcomes = models.TextField(
        blank=True,
        help_text='One outcome per line.'
    )

    requirements = models.TextField(
        blank=True,
        help_text='One requirement per line.'
    )

    target_audience = models.TextField(
        blank=True,
        help_text='One audience group per line.'
    )

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.DRAFT
    )

    is_featured = models.BooleanField(
        default=False
    )

    is_published = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:

        ordering = (
            '-is_featured',
            '-created_at',
        )

        indexes = (
            models.Index(fields=('slug',), name='learning_co_slug_42b789_idx'),
            models.Index(fields=('category',), name='learning_co_categor_7f5139_idx'),
            models.Index(fields=('instructor',), name='learning_co_instruc_c28a74_idx'),
            models.Index(fields=('status',), name='learning_co_status_064f7f_idx'),
            models.Index(fields=('is_published',), name='learning_co_is_publ_0180a6_idx'),
            models.Index(fields=('is_featured',), name='learning_co_is_feat_2ae4e2_idx'),
            models.Index(fields=('created_at',), name='learning_co_created_91bc8a_idx'),
        )

    def __str__(self):

        return self.title

    def save(self, *args, **kwargs):

        if not self.slug:

            self.slug = self.generate_unique_slug()

        if self.status == self.Status.PUBLISHED:

            self.is_published = True

        else:

            self.is_published = False

        super().save(*args, **kwargs)

    def generate_unique_slug(self):

        base_slug = slugify(self.title) or 'course'
        slug = base_slug
        counter = 2

        while Course.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            slug = f'{base_slug}-{counter}'
            counter += 1

        return slug

    def get_absolute_url(self):

        return reverse(
            'learning:course_detail',
            args=[
                self.slug,
            ]
        )

    @property
    def display_price(self):

        if self.is_free:

            return 'Free'

        active_price = self.discount_price or self.price

        return f'TSh {active_price:,.0f}'

    @property
    def outcome_list(self):

        return self._split_lines(self.learning_outcomes)

    @property
    def requirement_list(self):

        return self._split_lines(self.requirements)

    @property
    def target_audience_list(self):

        return self._split_lines(self.target_audience)

    def _split_lines(self, value):

        return [
            item.strip()
            for item in value.splitlines()
            if item.strip()
        ]


class Module(models.Model):

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='modules'
    )

    title = models.CharField(
        max_length=220
    )

    description = models.TextField(
        blank=True
    )

    order = models.PositiveIntegerField(
        default=1
    )

    is_published = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:

        ordering = (
            'order',
            'title',
        )

        constraints = (
            models.UniqueConstraint(
                fields=(
                    'course',
                    'order',
                ),
                name='unique_module_order_per_course'
            ),
        )

    def __str__(self):

        return f'{self.course.title} - {self.title}'


class Lesson(models.Model):

    class LessonType(models.TextChoices):

        VIDEO = 'Video', 'Video'
        TEXT = 'Text', 'Text'
        DOCUMENT = 'Document', 'Document'
        EXTERNAL_RESOURCE = 'External Resource', 'External Resource'
        QUIZ = 'Quiz', 'Quiz'
        ASSIGNMENT = 'Assignment', 'Assignment'
        LIVE_SESSION = 'Live Session', 'Live Session'

    module = models.ForeignKey(
        Module,
        on_delete=models.CASCADE,
        related_name='lessons'
    )

    title = models.CharField(
        max_length=220
    )

    slug = models.SlugField(
        max_length=240,
        blank=True
    )

    lesson_type = models.CharField(
        max_length=40,
        choices=LessonType.choices,
        default=LessonType.TEXT
    )

    written_content = models.TextField(
        blank=True
    )

    video_url = models.URLField(
        max_length=1000,
        blank=True
    )

    video_file = models.FileField(
        upload_to='learning/videos/',
        validators=[
            FileExtensionValidator(SAFE_VIDEO_EXTENSIONS),
        ],
        blank=True,
        null=True
    )

    downloadable_file = models.FileField(
        upload_to='learning/documents/',
        validators=[
            FileExtensionValidator(SAFE_DOCUMENT_EXTENSIONS),
        ],
        blank=True,
        null=True
    )

    source_code_file = models.FileField(
        upload_to='learning/documents/source_code/',
        validators=[
            FileExtensionValidator(['zip']),
        ],
        blank=True,
        null=True
    )

    external_resource_url = models.URLField(
        max_length=1000,
        blank=True
    )

    duration_minutes = models.PositiveIntegerField(
        default=0
    )

    order = models.PositiveIntegerField(
        default=1
    )

    is_preview = models.BooleanField(
        default=False
    )

    is_compulsory = models.BooleanField(
        default=True
    )

    is_published = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:

        ordering = (
            'module__order',
            'order',
            'title',
        )

        constraints = (
            models.UniqueConstraint(
                fields=(
                    'module',
                    'slug',
                ),
                name='unique_lesson_slug_per_module'
            ),
            models.UniqueConstraint(
                fields=(
                    'module',
                    'order',
                ),
                name='unique_lesson_order_per_module'
            ),
        )

    def __str__(self):

        return f'{self.module.course.title} - {self.title}'

    def save(self, *args, **kwargs):

        if not self.slug:

            self.slug = self.generate_unique_slug()

        super().save(*args, **kwargs)

    def generate_unique_slug(self):

        base_slug = slugify(self.title) or 'lesson'
        slug = base_slug
        counter = 2

        while Lesson.objects.filter(
            module=self.module,
            slug=slug
        ).exclude(pk=self.pk).exists():
            slug = f'{base_slug}-{counter}'
            counter += 1

        return slug

    @property
    def embedded_video_url(self):

        if not self.video_url:

            return ''

        parsed_url = urlparse(
            self.video_url
        )

        hostname = parsed_url.hostname or ''

        if 'youtu.be' in hostname:

            video_id = parsed_url.path.strip('/').split('/')[0]

        elif 'youtube.com' in hostname:

            if parsed_url.path.startswith('/embed/'):

                return self.video_url

            if parsed_url.path.startswith('/shorts/'):

                video_id = parsed_url.path.split('/shorts/', 1)[1].split('/')[0]

            elif parsed_url.path.startswith('/live/'):

                video_id = parsed_url.path.split('/live/', 1)[1].split('/')[0]

            else:

                video_id = parse_qs(
                    parsed_url.query
                ).get(
                    'v',
                    [
                        '',
                    ]
                )[0]

        else:

            return self.video_url

        if not video_id:

            return ''

        video_id = video_id.split('?')[0].split('&')[0]

        return f'https://www.youtube.com/embed/{video_id}'


class Enrolment(models.Model):

    class Status(models.TextChoices):

        PENDING = 'Pending', 'Pending'
        ACTIVE = 'Active', 'Active'
        COMPLETED = 'Completed', 'Completed'
        SUSPENDED = 'Suspended', 'Suspended'
        CANCELLED = 'Cancelled', 'Cancelled'

    class PaymentStatus(models.TextChoices):

        NOT_REQUIRED = 'Not Required', 'Not Required'
        PENDING = 'Pending', 'Pending'
        PAID = 'Paid', 'Paid'
        REJECTED = 'Rejected', 'Rejected'
        REFUNDED = 'Refunded', 'Refunded'

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='learning_enrolments'
    )

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='enrolments'
    )

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.PENDING
    )

    payment_status = models.CharField(
        max_length=30,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING
    )

    enrolled_at = models.DateTimeField(
        auto_now_add=True
    )

    activated_at = models.DateTimeField(
        blank=True,
        null=True
    )

    completed_at = models.DateTimeField(
        blank=True,
        null=True
    )

    progress_percentage = models.PositiveIntegerField(
        default=0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100),
        ]
    )

    is_active = models.BooleanField(
        default=False
    )

    class Meta:

        ordering = (
            '-enrolled_at',
        )

        constraints = (
            models.UniqueConstraint(
                fields=(
                    'student',
                    'course',
                ),
                name='unique_student_course_enrolment'
            ),
        )

    def __str__(self):

        return f'{self.student} - {self.course}'

    def save(self, *args, **kwargs):

        if self.course.is_free and self.status == self.Status.PENDING:

            self.status = self.Status.ACTIVE
            self.payment_status = self.PaymentStatus.NOT_REQUIRED
            self.is_active = True

            if not self.activated_at:

                self.activated_at = timezone.now()

        super().save(*args, **kwargs)


class LessonProgress(models.Model):

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='lesson_progress'
    )

    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name='progress_records'
    )

    enrolment = models.ForeignKey(
        Enrolment,
        on_delete=models.CASCADE,
        related_name='lesson_progress'
    )

    is_completed = models.BooleanField(
        default=False
    )

    started_at = models.DateTimeField(
        auto_now_add=True
    )

    completed_at = models.DateTimeField(
        blank=True,
        null=True
    )

    last_accessed_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:

        ordering = (
            '-last_accessed_at',
        )

        constraints = (
            models.UniqueConstraint(
                fields=(
                    'student',
                    'lesson',
                ),
                name='unique_student_lesson_progress'
            ),
        )

    def __str__(self):

        return f'{self.student} - {self.lesson}'


class Notification(models.Model):

    class NotificationType(models.TextChoices):

        ENROLMENT = 'Enrolment', 'Enrolment'
        PAYMENT = 'Payment', 'Payment'
        QUIZ = 'Quiz', 'Quiz'
        ASSIGNMENT = 'Assignment', 'Assignment'
        REVIEW = 'Review', 'Review'
        ANNOUNCEMENT = 'Announcement', 'Announcement'
        COURSE_COMPLETION = 'Course Completion', 'Course Completion'
        CERTIFICATE = 'Certificate', 'Certificate'
        SYSTEM = 'System', 'System'

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='learning_notifications'
    )

    title = models.CharField(
        max_length=180
    )

    message = models.TextField()

    notification_type = models.CharField(
        max_length=40,
        choices=NotificationType.choices,
        default=NotificationType.SYSTEM
    )

    related_url = models.CharField(
        max_length=1000,
        blank=True
    )

    dedupe_key = models.CharField(
        max_length=255,
        blank=True,
        help_text='Optional key used by services to avoid duplicate notifications.'
    )

    is_read = models.BooleanField(
        default=False
    )

    read_at = models.DateTimeField(
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:

        ordering = (
            '-created_at',
        )

        indexes = (
            models.Index(fields=('recipient', 'is_read'), name='learning_no_recipie_e8673c_idx'),
            models.Index(fields=('notification_type',), name='learning_no_notific_7d05e5_idx'),
            models.Index(fields=('created_at',), name='learning_no_created_3c962e_idx'),
        )

        constraints = (
            models.UniqueConstraint(
                fields=(
                    'recipient',
                    'dedupe_key',
                ),
                condition=~models.Q(dedupe_key=''),
                name='unique_learning_notification_dedupe'
            ),
        )

    def __str__(self):

        return f'{self.recipient} - {self.title}'

    def mark_read(self):

        if not self.is_read:

            self.is_read = True
            self.read_at = timezone.now()
            self.save(
                update_fields=[
                    'is_read',
                    'read_at',
                ]
            )


class CourseAnnouncement(models.Model):

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='announcements'
    )

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='learning_announcements'
    )

    title = models.CharField(
        max_length=220
    )

    message = models.TextField()

    is_published = models.BooleanField(
        default=False
    )

    published_at = models.DateTimeField(
        blank=True,
        null=True
    )

    notifications_sent = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:

        ordering = (
            '-published_at',
            '-created_at',
        )

    def __str__(self):

        return f'{self.course.title} - {self.title}'

    def save(self, *args, **kwargs):

        if self.is_published and not self.published_at:

            self.published_at = timezone.now()

        super().save(*args, **kwargs)


class Quiz(models.Model):

    lesson = models.OneToOneField(
        Lesson,
        on_delete=models.CASCADE,
        related_name='quiz'
    )

    title = models.CharField(
        max_length=220
    )

    slug = models.SlugField(
        max_length=240,
        blank=True
    )

    instructions = models.TextField(
        blank=True
    )

    passing_score = models.PositiveIntegerField(
        default=50,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100),
        ]
    )

    time_limit_minutes = models.PositiveIntegerField(
        blank=True,
        null=True
    )

    attempts_allowed = models.PositiveIntegerField(
        default=1,
        validators=[
            MinValueValidator(1),
        ]
    )

    randomise_questions = models.BooleanField(
        default=False
    )

    randomise_choices = models.BooleanField(
        default=False
    )

    show_score_after_submission = models.BooleanField(
        default=True
    )

    show_correct_answers = models.BooleanField(
        default=False
    )

    is_compulsory = models.BooleanField(
        default=True
    )

    is_published = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:

        ordering = (
            'lesson__module__course__title',
            'lesson__module__order',
            'lesson__order',
        )

        indexes = (
            models.Index(fields=('slug',), name='learning_qu_slug_d912e9_idx'),
            models.Index(fields=('is_published',), name='learning_qu_is_publ_7dbd38_idx'),
            models.Index(fields=('created_at',), name='learning_qu_created_0e42de_idx'),
        )

        constraints = (
            models.UniqueConstraint(
                fields=(
                    'lesson',
                    'slug',
                ),
                name='unique_quiz_slug_per_lesson'
            ),
        )

    def __str__(self):

        return self.title

    def clean(self):

        if self.passing_score < 0 or self.passing_score > 100:

            raise ValidationError(
                {
                    'passing_score': 'Passing score must be between 0 and 100.'
                }
            )

        if self.attempts_allowed < 1:

            raise ValidationError(
                {
                    'attempts_allowed': 'Attempts allowed must be at least 1.'
                }
            )

        if self.time_limit_minutes is not None and self.time_limit_minutes <= 0:

            raise ValidationError(
                {
                    'time_limit_minutes': 'Time limit must be greater than zero.'
                }
            )

        if self.is_published and self.lesson and not self.lesson.is_published:

            raise ValidationError(
                {
                    'is_published': 'A quiz cannot be published under an unpublished lesson.'
                }
            )

    def save(self, *args, **kwargs):

        if not self.slug:

            self.slug = slugify(self.title) or 'quiz'

        if self.lesson_id and self.lesson.lesson_type != Lesson.LessonType.QUIZ:

            self.lesson.lesson_type = Lesson.LessonType.QUIZ
            self.lesson.save(
                update_fields=[
                    'lesson_type',
                    'updated_at',
                ]
            )

        super().save(*args, **kwargs)

    @property
    def course(self):

        return self.lesson.module.course

    @property
    def total_marks(self):

        return self.questions.aggregate(
            total=models.Sum('marks')
        )['total'] or 0


class Question(models.Model):

    class QuestionType(models.TextChoices):

        MULTIPLE_CHOICE = 'Multiple Choice', 'Multiple Choice'
        MULTIPLE_SELECT = 'Multiple Select', 'Multiple Select'
        TRUE_FALSE = 'True or False', 'True or False'
        SHORT_ANSWER = 'Short Answer', 'Short Answer'

    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name='questions'
    )

    question_text = models.TextField()

    question_type = models.CharField(
        max_length=40,
        choices=QuestionType.choices,
        default=QuestionType.MULTIPLE_CHOICE
    )

    marks = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=1
    )

    order = models.PositiveIntegerField(
        default=1
    )

    explanation = models.TextField(
        blank=True
    )

    is_required = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:

        ordering = (
            'quiz',
            'order',
        )

        indexes = (
            models.Index(fields=('quiz', 'order'), name='learning_qu_quiz_id_218b17_idx'),
            models.Index(fields=('question_type',), name='learning_qu_questio_c8f546_idx'),
        )

        constraints = (
            models.UniqueConstraint(
                fields=(
                    'quiz',
                    'order',
                ),
                name='unique_question_order_per_quiz'
            ),
        )

    def __str__(self):

        return f'{self.quiz.title} - Question {self.order}'

    def clean(self):

        if self.marks <= 0:

            raise ValidationError(
                {
                    'marks': 'Question marks must be greater than zero.'
                }
            )

    @property
    def is_objective(self):

        return self.question_type != self.QuestionType.SHORT_ANSWER


class Choice(models.Model):

    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name='choices'
    )

    choice_text = models.CharField(
        max_length=500
    )

    is_correct = models.BooleanField(
        default=False
    )

    order = models.PositiveIntegerField(
        default=1
    )

    class Meta:

        ordering = (
            'question',
            'order',
        )

        constraints = (
            models.UniqueConstraint(
                fields=(
                    'question',
                    'order',
                ),
                name='unique_choice_order_per_question'
            ),
            models.UniqueConstraint(
                fields=(
                    'question',
                    'choice_text',
                ),
                name='unique_choice_text_per_question'
            ),
        )

    def __str__(self):

        return self.choice_text

    def clean(self):

        if not self.choice_text.strip():

            raise ValidationError(
                {
                    'choice_text': 'Choice text is required.'
                }
            )

        if self.question_id and not self.question.is_objective:

            raise ValidationError(
                'Short-answer questions cannot have choices.'
            )


class QuizAttempt(models.Model):

    class Status(models.TextChoices):

        IN_PROGRESS = 'In Progress', 'In Progress'
        SUBMITTED = 'Submitted', 'Submitted'
        AWAITING_MANUAL_GRADING = 'Awaiting Manual Grading', 'Awaiting Manual Grading'
        GRADED = 'Graded', 'Graded'
        EXPIRED = 'Expired', 'Expired'

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='quiz_attempts'
    )

    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name='attempts'
    )

    enrolment = models.ForeignKey(
        Enrolment,
        on_delete=models.PROTECT,
        related_name='quiz_attempts',
        blank=True,
        null=True
    )

    attempt_number = models.PositiveIntegerField()

    started_at = models.DateTimeField(
        default=timezone.now
    )

    submitted_at = models.DateTimeField(
        blank=True,
        null=True
    )

    expires_at = models.DateTimeField(
        blank=True,
        null=True
    )

    status = models.CharField(
        max_length=40,
        choices=Status.choices,
        default=Status.IN_PROGRESS
    )

    objective_marks_awarded = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0
    )

    manual_marks_awarded = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0
    )

    total_marks_awarded = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0
    )

    total_possible_marks = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0
    )

    percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )

    passed = models.BooleanField(
        default=False
    )

    requires_manual_grading = models.BooleanField(
        default=False
    )

    graded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='graded_quiz_attempts',
        blank=True,
        null=True
    )

    graded_at = models.DateTimeField(
        blank=True,
        null=True
    )

    instructor_feedback = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:

        ordering = (
            '-started_at',
        )

        indexes = (
            models.Index(fields=('student',), name='learning_qu_student_b59012_idx'),
            models.Index(fields=('quiz',), name='learning_qu_quiz_id_fe08bf_idx'),
            models.Index(fields=('status',), name='learning_qu_status_2cdb71_idx'),
            models.Index(fields=('attempt_number',), name='learning_qu_attempt_2388b3_idx'),
            models.Index(fields=('enrolment',), name='learning_qu_enrolme_b0dc59_idx'),
        )

        constraints = (
            models.UniqueConstraint(
                fields=(
                    'student',
                    'quiz',
                    'attempt_number',
                ),
                name='unique_quiz_attempt_number_per_student'
            ),
            models.UniqueConstraint(
                fields=(
                    'student',
                    'quiz',
                ),
                condition=models.Q(status='In Progress'),
                name='unique_active_quiz_attempt_per_student'
            ),
        )

    def __str__(self):

        return f'{self.student} - {self.quiz} - Attempt {self.attempt_number}'

    @property
    def is_editable(self):

        return self.status == self.Status.IN_PROGRESS


class StudentAnswer(models.Model):

    attempt = models.ForeignKey(
        QuizAttempt,
        on_delete=models.CASCADE,
        related_name='answers'
    )

    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name='student_answers'
    )

    selected_choices = models.ManyToManyField(
        Choice,
        blank=True,
        related_name='student_answers'
    )

    text_answer = models.TextField(
        blank=True
    )

    objective_marks_awarded = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=0
    )

    manual_marks_awarded = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=0
    )

    is_correct = models.BooleanField(
        default=False
    )

    instructor_feedback = models.TextField(
        blank=True
    )

    graded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='graded_quiz_answers',
        blank=True,
        null=True
    )

    graded_at = models.DateTimeField(
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:

        ordering = (
            'question__order',
        )

        constraints = (
            models.UniqueConstraint(
                fields=(
                    'attempt',
                    'question',
                ),
                name='unique_answer_per_attempt_question'
            ),
        )

    def __str__(self):

        return f'{self.attempt} - {self.question}'

    def clean(self):

        if self.manual_marks_awarded < 0 or self.objective_marks_awarded < 0:

            raise ValidationError(
                'Marks cannot be negative.'
            )

        if self.manual_marks_awarded > self.question.marks:

            raise ValidationError(
                {
                    'manual_marks_awarded': 'Manual marks cannot exceed question marks.'
                }
            )


class Assignment(models.Model):

    lesson = models.OneToOneField(
        Lesson,
        on_delete=models.CASCADE,
        related_name='assignment'
    )

    title = models.CharField(
        max_length=220
    )

    slug = models.SlugField(
        max_length=240,
        blank=True
    )

    instructions = models.TextField()

    maximum_score = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=100
    )

    passing_score = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=50
    )

    due_date = models.DateTimeField(
        blank=True,
        null=True
    )

    allow_late_submission = models.BooleanField(
        default=False
    )

    allow_resubmission = models.BooleanField(
        default=True
    )

    maximum_attempts = models.PositiveIntegerField(
        default=1,
        validators=[
            MinValueValidator(1),
        ]
    )

    allowed_file_extensions = models.CharField(
        max_length=255,
        default=','.join(SAFE_ASSIGNMENT_EXTENSIONS),
        help_text='Separate extensions using commas.'
    )

    maximum_file_size_mb = models.PositiveIntegerField(
        default=10
    )

    require_text_submission = models.BooleanField(
        default=True
    )

    require_file_submission = models.BooleanField(
        default=False
    )

    is_compulsory = models.BooleanField(
        default=True
    )

    is_published = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:

        ordering = (
            'lesson__module__course__title',
            'lesson__module__order',
            'lesson__order',
        )

        indexes = (
            models.Index(fields=('slug',), name='learning_as_slug_8df6b9_idx'),
            models.Index(fields=('is_published',), name='learning_as_is_publ_7751a1_idx'),
            models.Index(fields=('due_date',), name='learning_as_due_dat_9305cc_idx'),
        )

        constraints = (
            models.UniqueConstraint(
                fields=(
                    'lesson',
                    'slug',
                ),
                name='unique_assignment_slug_per_lesson'
            ),
        )

    def __str__(self):

        return self.title

    def clean(self):

        errors = {}

        if self.maximum_score <= 0:

            errors['maximum_score'] = 'Maximum score must be greater than zero.'

        if self.passing_score < 0:

            errors['passing_score'] = 'Passing score cannot be negative.'

        if self.maximum_score and self.passing_score > self.maximum_score:

            errors['passing_score'] = 'Passing score cannot exceed maximum score.'

        if self.maximum_attempts < 1:

            errors['maximum_attempts'] = 'Maximum attempts must be at least 1.'

        if not self.require_text_submission and not self.require_file_submission:

            errors['require_text_submission'] = 'At least one submission method is required.'

        allowed_extensions = self.allowed_extension_list

        if self.require_file_submission and not allowed_extensions:

            errors['allowed_file_extensions'] = 'Allowed file extensions are required for file submissions.'

        dangerous = set(allowed_extensions) & set(DANGEROUS_ASSIGNMENT_EXTENSIONS)

        if dangerous:

            errors['allowed_file_extensions'] = 'Executable file types are not allowed.'

        if self.require_file_submission and self.maximum_file_size_mb <= 0:

            errors['maximum_file_size_mb'] = 'Maximum file size must be greater than zero.'

        if self.is_published and self.lesson and not self.lesson.is_published:

            errors['is_published'] = 'A published assignment cannot belong to an unpublished lesson.'

        if errors:

            raise ValidationError(
                errors
            )

    def save(self, *args, **kwargs):

        if not self.slug:

            self.slug = slugify(self.title) or 'assignment'

        if self.lesson_id and self.lesson.lesson_type != Lesson.LessonType.ASSIGNMENT:

            self.lesson.lesson_type = Lesson.LessonType.ASSIGNMENT
            self.lesson.save(
                update_fields=[
                    'lesson_type',
                    'updated_at',
                ]
            )

        super().save(*args, **kwargs)

    @property
    def course(self):

        return self.lesson.module.course

    @property
    def allowed_extension_list(self):

        return [
            item.strip().lower().lstrip('.')
            for item in self.allowed_file_extensions.split(',')
            if item.strip()
        ]

    def get_absolute_url(self):

        return reverse(
            'learning:assignment_detail',
            args=[
                self.pk,
            ]
        )


class AssignmentSubmission(models.Model):

    class Status(models.TextChoices):

        DRAFT = 'Draft', 'Draft'
        SUBMITTED = 'Submitted', 'Submitted'
        UNDER_REVIEW = 'Under Review', 'Under Review'
        GRADED = 'Graded', 'Graded'
        RETURNED = 'Returned for Revision', 'Returned for Revision'
        WITHDRAWN = 'Withdrawn', 'Withdrawn'

    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.CASCADE,
        related_name='submissions'
    )

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='assignment_submissions'
    )

    enrolment = models.ForeignKey(
        Enrolment,
        on_delete=models.PROTECT,
        related_name='assignment_submissions'
    )

    attempt_number = models.PositiveIntegerField()

    submission_text = models.TextField(
        blank=True
    )

    submission_file = models.FileField(
        upload_to=assignment_submission_upload_to,
        blank=True,
        null=True
    )

    original_filename = models.CharField(
        max_length=255,
        blank=True
    )

    file_size = models.PositiveIntegerField(
        default=0
    )

    status = models.CharField(
        max_length=40,
        choices=Status.choices,
        default=Status.DRAFT
    )

    submitted_at = models.DateTimeField(
        blank=True,
        null=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    is_late = models.BooleanField(
        default=False
    )

    score = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        blank=True,
        null=True
    )

    passed = models.BooleanField(
        default=False
    )

    instructor_feedback = models.TextField(
        blank=True
    )

    graded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='graded_assignment_submissions',
        blank=True,
        null=True
    )

    graded_at = models.DateTimeField(
        blank=True,
        null=True
    )

    returned_at = models.DateTimeField(
        blank=True,
        null=True
    )

    returned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='returned_assignment_submissions',
        blank=True,
        null=True
    )

    revision_message = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:

        ordering = (
            '-created_at',
        )

        indexes = (
            models.Index(fields=('assignment', 'student', 'status'), name='learning_su_assign_1a2e5f_idx'),
            models.Index(fields=('enrolment', 'submitted_at'), name='learning_su_enrolme_14a507_idx'),
            models.Index(fields=('status', 'graded_at'), name='learning_su_status_47f75a_idx'),
        )

        constraints = (
            models.UniqueConstraint(
                fields=(
                    'assignment',
                    'student',
                    'attempt_number',
                ),
                name='unique_assignment_attempt_per_student'
            ),
            models.UniqueConstraint(
                fields=(
                    'assignment',
                    'student',
                ),
                condition=models.Q(status='Draft'),
                name='unique_draft_assignment_submission'
            ),
        )

    def __str__(self):

        return f'{self.student} - {self.assignment} - Attempt {self.attempt_number}'

    def clean(self):

        if self.score is not None:

            if self.score < 0:

                raise ValidationError(
                    {
                        'score': 'Score cannot be negative.'
                    }
                )

            if self.assignment_id and self.score > self.assignment.maximum_score:

                raise ValidationError(
                    {
                        'score': 'Score cannot exceed assignment maximum score.'
                    }
                )

    @property
    def is_student_editable(self):

        return self.status in [
            self.Status.DRAFT,
        ]


class LearningPaymentSettings(models.Model):

    currency = models.CharField(
        max_length=10,
        default='TZS'
    )

    mpesa_business_number = models.CharField(max_length=100, blank=True)
    mpesa_account_name = models.CharField(max_length=200, blank=True)
    airtel_business_number = models.CharField(max_length=100, blank=True)
    airtel_account_name = models.CharField(max_length=200, blank=True)
    mixx_business_number = models.CharField(max_length=100, blank=True)
    mixx_account_name = models.CharField(max_length=200, blank=True)
    bank_name = models.CharField(max_length=200, blank=True)
    bank_account_name = models.CharField(max_length=200, blank=True)
    bank_account_number = models.CharField(max_length=100, blank=True)
    bank_branch = models.CharField(max_length=200, blank=True)
    card_instructions = models.TextField(blank=True)
    general_payment_instructions = models.TextField(blank=True)
    require_proof_for_mobile_money = models.BooleanField(default=True)
    require_proof_for_bank_transfer = models.BooleanField(default=True)
    payment_support_email = models.EmailField(blank=True)
    payment_support_phone = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:

        verbose_name_plural = 'Learning payment settings'

        constraints = (
            models.UniqueConstraint(
                fields=('is_active',),
                condition=models.Q(is_active=True),
                name='unique_active_learning_payment_settings'
            ),
        )

    def __str__(self):

        return f'Learning payment settings ({self.currency})'


class Payment(models.Model):

    class PaymentMethod(models.TextChoices):

        MPESA = 'M-Pesa', 'M-Pesa'
        AIRTEL = 'Airtel Money', 'Airtel Money'
        MIXX = 'Mixx by Yas', 'Mixx by Yas'
        BANK = 'Bank Transfer', 'Bank Transfer'
        CARD = 'Card', 'Card'
        OTHER = 'Other', 'Other'

    class Status(models.TextChoices):

        PENDING = 'Pending', 'Pending'
        PAID = 'Paid', 'Paid'
        FAILED = 'Failed', 'Failed'
        REJECTED = 'Rejected', 'Rejected'
        REFUNDED = 'Refunded', 'Refunded'
        CANCELLED = 'Cancelled', 'Cancelled'

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='learning_payments'
    )

    course = models.ForeignKey(
        Course,
        on_delete=models.PROTECT,
        related_name='learning_payments'
    )

    enrolment = models.ForeignKey(
        Enrolment,
        on_delete=models.PROTECT,
        related_name='payments'
    )

    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default='TZS')
    payment_method = models.CharField(max_length=40, choices=PaymentMethod.choices)
    transaction_reference = models.CharField(max_length=120)
    proof_of_payment = models.FileField(upload_to=payment_proof_upload_to, blank=True, null=True)
    original_filename = models.CharField(max_length=255, blank=True)
    proof_file_size = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.PENDING)
    student_notes = models.TextField(blank=True)
    administrator_notes = models.TextField(blank=True)
    submitted_at = models.DateTimeField(default=timezone.now)
    verified_at = models.DateTimeField(blank=True, null=True)
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name='verified_learning_payments', blank=True, null=True)
    rejected_at = models.DateTimeField(blank=True, null=True)
    rejected_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name='rejected_learning_payments', blank=True, null=True)
    refunded_at = models.DateTimeField(blank=True, null=True)
    refunded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name='refunded_learning_payments', blank=True, null=True)
    refund_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:

        ordering = ('-submitted_at',)

        indexes = (
            models.Index(fields=('student', 'status'), name='learning_pa_student_7ab4f0_idx'),
            models.Index(fields=('course', 'status'), name='learning_pa_course_612e8c_idx'),
            models.Index(fields=('enrolment', 'status'), name='learning_pa_enrolm_2f7614_idx'),
            models.Index(fields=('transaction_reference',), name='learning_pa_transa_4bd0b5_idx'),
            models.Index(fields=('submitted_at',), name='learning_pa_submitt_2403e6_idx'),
            models.Index(fields=('verified_at',), name='learning_pa_verifie_b25777_idx'),
            models.Index(fields=('payment_method', 'status'), name='learning_pa_payment_ad4f6d_idx'),
        )

        constraints = (
            models.UniqueConstraint(
                fields=('enrolment',),
                condition=models.Q(status='Pending'),
                name='unique_pending_learning_payment_per_enrolment'
            ),
            models.UniqueConstraint(
                fields=('enrolment',),
                condition=models.Q(status='Paid'),
                name='unique_paid_learning_payment_per_enrolment'
            ),
            models.UniqueConstraint(
                fields=('transaction_reference',),
                condition=~models.Q(transaction_reference=''),
                name='unique_learning_payment_reference'
            ),
        )

        permissions = (
            ('verify_learning_payment', 'Can verify learning payment'),
            ('reject_learning_payment', 'Can reject learning payment'),
            ('refund_learning_payment', 'Can refund learning payment'),
            ('view_all_learning_payments', 'Can view all learning payments'),
        )

    def __str__(self):

        return f'{self.student} - {self.course} - {self.status}'

    def clean(self):

        errors = {}

        if self.amount <= 0:
            errors['amount'] = 'Payment amount must be greater than zero.'

        if self.enrolment_id:
            if self.student_id and self.enrolment.student_id != self.student_id:
                errors['student'] = 'Payment student must match enrolment student.'
            if self.course_id and self.enrolment.course_id != self.course_id:
                errors['course'] = 'Payment course must match enrolment course.'

        if self.course_id and self.course.is_free:
            errors['course'] = 'Free courses cannot have learning payments.'

        if self.status == self.Status.PAID and not (self.verified_by_id and self.verified_at):
            errors['verified_by'] = 'Paid payments require verifier and verification time.'

        if self.status == self.Status.REJECTED and not (self.rejected_by_id and self.rejected_at and self.administrator_notes.strip()):
            errors['administrator_notes'] = 'Rejected payments require rejection notes and audit fields.'

        if self.status == self.Status.REFUNDED and not (self.refunded_by_id and self.refunded_at and self.refund_reason.strip()):
            errors['refund_reason'] = 'Refunded payments require a refund reason and audit fields.'

        if errors:
            raise ValidationError(errors)


class CourseReview(models.Model):

    class Status(models.TextChoices):

        PENDING = 'Pending', 'Pending'
        APPROVED = 'Approved', 'Approved'
        REJECTED = 'Rejected', 'Rejected'
        HIDDEN = 'Hidden', 'Hidden'

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='course_reviews'
    )

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='reviews'
    )

    enrolment = models.ForeignKey(
        Enrolment,
        on_delete=models.PROTECT,
        related_name='course_reviews'
    )

    rating = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5),
        ]
    )

    comment = models.TextField()

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.PENDING
    )

    is_approved = models.BooleanField(
        default=False
    )

    moderation_notes = models.TextField(
        blank=True
    )

    moderated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='moderated_course_reviews',
        blank=True,
        null=True
    )

    moderated_at = models.DateTimeField(
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:

        ordering = (
            '-created_at',
        )

        indexes = (
            models.Index(fields=('course', 'status'), name='learning_re_course_21dc8c_idx'),
            models.Index(fields=('student', 'created_at'), name='learning_re_student_7bf2e7_idx'),
            models.Index(fields=('status', 'created_at'), name='learning_re_status_6682c6_idx'),
            models.Index(fields=('rating',), name='learning_re_rating_c80d28_idx'),
            models.Index(fields=('moderated_at',), name='learning_re_moderat_2363f0_idx'),
        )

        constraints = (
            models.UniqueConstraint(
                fields=(
                    'student',
                    'course',
                ),
                name='unique_course_review_per_student'
            ),
            models.UniqueConstraint(
                fields=(
                    'enrolment',
                ),
                name='unique_course_review_per_enrolment'
            ),
            models.CheckConstraint(
                condition=models.Q(rating__gte=1) & models.Q(rating__lte=5),
                name='course_review_rating_between_1_and_5'
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(status='Approved', is_approved=True)
                    | models.Q(status__in=['Pending', 'Rejected', 'Hidden'], is_approved=False)
                ),
                name='course_review_approval_consistent'
            ),
        )

        permissions = (
            ('moderate_course_reviews', 'Can moderate course reviews'),
            ('approve_course_review', 'Can approve course review'),
            ('reject_course_review', 'Can reject course review'),
            ('hide_course_review', 'Can hide course review'),
            ('view_all_course_reviews', 'Can view all course reviews'),
        )

    def __str__(self):

        return f'{self.course} - {self.student} - {self.rating}'

    def clean(self):

        errors = {}

        if self.rating < 1 or self.rating > 5:
            errors['rating'] = 'Rating must be between 1 and 5.'

        if self.enrolment_id:
            if self.student_id and self.enrolment.student_id != self.student_id:
                errors['student'] = 'Review student must match enrolment student.'
            if self.course_id and self.enrolment.course_id != self.course_id:
                errors['course'] = 'Review course must match enrolment course.'

        if self.status == self.Status.APPROVED and not self.is_approved:
            errors['is_approved'] = 'Approved reviews must be marked approved.'

        if self.status != self.Status.APPROVED and self.is_approved:
            errors['is_approved'] = 'Only approved reviews may be publicly approved.'

        if self.status in [self.Status.REJECTED, self.Status.HIDDEN] and not self.moderation_notes.strip():
            errors['moderation_notes'] = 'Rejected or hidden reviews require a moderation reason.'

        if self.status in [self.Status.APPROVED, self.Status.REJECTED, self.Status.HIDDEN] and not (
            self.moderated_by_id and self.moderated_at
        ):
            errors['moderated_by'] = 'Moderated reviews require moderator and moderation time.'

        if errors:
            raise ValidationError(errors)

    @property
    def safe_reviewer_name(self):

        full_name = self.student.get_full_name().strip()

        if full_name:
            return full_name

        first_name = (self.student.first_name or '').strip()
        last_name = (self.student.last_name or '').strip()

        if first_name and last_name:
            return f'{first_name} {last_name[:1]}.'

        if first_name:
            return first_name

        return 'Verified Learner'

    @property
    def is_verified_learner(self):

        if not self.enrolment_id:
            return False

        if self.enrolment.student_id != self.student_id or self.enrolment.course_id != self.course_id:
            return False

        if self.course.is_free:
            return (
                self.enrolment.is_active
                and self.enrolment.status in [
                    Enrolment.Status.ACTIVE,
                    Enrolment.Status.COMPLETED,
                ]
                and self.enrolment.payment_status == Enrolment.PaymentStatus.NOT_REQUIRED
            )

        return (
            self.enrolment.is_active
            and self.enrolment.status in [
                Enrolment.Status.ACTIVE,
                Enrolment.Status.COMPLETED,
            ]
            and self.enrolment.payment_status == Enrolment.PaymentStatus.PAID
        )


class Certificate(models.Model):

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='learning_certificates'
    )

    course = models.ForeignKey(
        Course,
        on_delete=models.PROTECT,
        related_name='certificates'
    )

    enrolment = models.OneToOneField(
        Enrolment,
        on_delete=models.PROTECT,
        related_name='certificate'
    )

    certificate_number = models.CharField(
        max_length=80,
        unique=True
    )

    verification_code = models.CharField(
        max_length=120,
        unique=True
    )

    issued_at = models.DateTimeField(
        default=timezone.now
    )

    certificate_file = models.FileField(
        upload_to='learning/certificates/',
        blank=True,
        null=True
    )

    is_valid = models.BooleanField(
        default=True
    )

    revoked_at = models.DateTimeField(
        blank=True,
        null=True
    )

    revoked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='revoked_learning_certificates',
        blank=True,
        null=True
    )

    revocation_reason = models.TextField(
        blank=True
    )

    restored_at = models.DateTimeField(
        blank=True,
        null=True
    )

    restored_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='restored_learning_certificates',
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:

        ordering = (
            '-issued_at',
        )

        indexes = (
            models.Index(fields=('student', 'issued_at'), name='learning_ce_student_4b4964_idx'),
            models.Index(fields=('course', 'issued_at'), name='learning_ce_course_91f7d8_idx'),
            models.Index(fields=('is_valid', 'issued_at'), name='learning_ce_is_vali_ea0667_idx'),
            models.Index(fields=('verification_code',), name='learning_ce_verific_b1899d_idx'),
        )

        permissions = (
            ('view_all_certificates', 'Can view all learning certificates'),
            ('revoke_certificate', 'Can revoke learning certificate'),
            ('restore_certificate', 'Can restore learning certificate'),
            ('regenerate_certificate', 'Can regenerate learning certificate PDF'),
            ('view_course_certificates', 'Can view course certificates'),
        )

    def __str__(self):

        return self.certificate_number

    def clean(self):

        errors = {}

        if self.enrolment_id:
            if self.student_id and self.enrolment.student_id != self.student_id:
                errors['student'] = 'Certificate student must match enrolment student.'
            if self.course_id and self.enrolment.course_id != self.course_id:
                errors['course'] = 'Certificate course must match enrolment course.'
            if self.enrolment.status != Enrolment.Status.COMPLETED:
                errors['enrolment'] = 'Certificate enrolment must be completed.'
            if (
                self.course_id
                and not self.course.is_free
                and self.enrolment.payment_status != Enrolment.PaymentStatus.PAID
            ):
                errors['enrolment'] = 'Paid-course certificate requires confirmed payment.'

        if not self.is_valid and not (self.revoked_at and self.revoked_by_id and self.revocation_reason.strip()):
            errors['revocation_reason'] = 'Revoked certificates require revocation audit details.'

        if self.is_valid and self.revoked_at and not self.restored_at:
            errors['is_valid'] = 'A restored valid certificate requires restoration audit details.'

        if errors:
            raise ValidationError(errors)

    @property
    def public_student_name(self):

        full_name = self.student.get_full_name().strip()
        return full_name or 'Verified Learner'

    @property
    def verification_url_path(self):

        return reverse(
            'learning:certificate_verify_code',
            args=[
                self.verification_code,
            ]
        )
