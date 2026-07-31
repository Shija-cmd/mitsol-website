from django.contrib import admin
from django.utils import timezone

from .models import (
    Assignment,
    AssignmentSubmission,
    Certificate,
    Course,
    CourseAnnouncement,
    CourseCategory,
    CourseReview,
    Enrolment,
    InstructorProfile,
    Lesson,
    LessonProgress,
    LearningPaymentSettings,
    Module,
    Notification,
    Payment,
    Choice,
    Question,
    Quiz,
    QuizAttempt,
    StudentAnswer,
)
from .services import approve_course_review, confirm_payment, mark_submission_under_review, publish_announcement, restore_certificate


class LessonInline(admin.TabularInline):

    model = Lesson

    extra = 1

    fields = (
        'title',
        'lesson_type',
        'order',
        'duration_minutes',
        'is_preview',
        'is_compulsory',
        'is_published',
    )


class ChoiceInline(admin.TabularInline):

    model = Choice

    extra = 2

    fields = (
        'choice_text',
        'is_correct',
        'order',
    )


class QuestionInline(admin.TabularInline):

    model = Question

    extra = 1

    fields = (
        'question_text',
        'question_type',
        'marks',
        'order',
        'is_required',
    )


class ModuleInline(admin.TabularInline):

    model = Module

    extra = 1

    fields = (
        'title',
        'order',
        'is_published',
    )


@admin.register(CourseCategory)
class CourseCategoryAdmin(admin.ModelAdmin):

    list_display = (
        'name',
        'is_active',
        'created_at',
    )

    list_filter = (
        'is_active',
    )

    search_fields = (
        'name',
        'description',
    )

    prepopulated_fields = {
        'slug': (
            'name',
        )
    }


@admin.register(InstructorProfile)
class InstructorProfileAdmin(admin.ModelAdmin):

    list_display = (
        'display_name',
        'title',
        'is_active',
        'updated_at',
    )

    list_filter = (
        'is_active',
    )

    search_fields = (
        'user__username',
        'user__first_name',
        'user__last_name',
        'title',
        'expertise',
    )


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):

    list_display = (
        'title',
        'category',
        'instructor',
        'level',
        'delivery_mode',
        'display_price',
        'status',
        'is_featured',
        'is_published',
        'updated_at',
    )

    list_filter = (
        'category',
        'level',
        'delivery_mode',
        'status',
        'is_free',
        'is_featured',
        'is_published',
        'created_at',
    )

    search_fields = (
        'title',
        'short_description',
        'full_description',
        'instructor__username',
        'instructor__first_name',
        'instructor__last_name',
    )

    prepopulated_fields = {
        'slug': (
            'title',
        )
    }

    readonly_fields = (
        'created_at',
        'updated_at',
    )

    inlines = (
        ModuleInline,
    )

    actions = (
        'publish_courses',
        'archive_courses',
    )

    def publish_courses(self, request, queryset):

        queryset.update(
            status=Course.Status.PUBLISHED,
            is_published=True
        )

    publish_courses.short_description = 'Publish selected courses'

    def archive_courses(self, request, queryset):

        queryset.update(
            status=Course.Status.ARCHIVED,
            is_published=False
        )

    archive_courses.short_description = 'Archive selected courses'


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):

    list_display = (
        'title',
        'course',
        'order',
        'is_published',
        'updated_at',
    )

    list_filter = (
        'is_published',
        'course',
    )

    search_fields = (
        'title',
        'description',
        'course__title',
    )

    inlines = (
        LessonInline,
    )


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):

    list_display = (
        'title',
        'module',
        'lesson_type',
        'order',
        'duration_minutes',
        'is_preview',
        'is_compulsory',
        'is_published',
        'updated_at',
    )

    list_filter = (
        'lesson_type',
        'is_preview',
        'is_compulsory',
        'is_published',
        'module__course',
    )

    search_fields = (
        'title',
        'written_content',
        'module__title',
        'module__course__title',
    )

    readonly_fields = (
        'created_at',
        'updated_at',
    )


@admin.register(Enrolment)
class EnrolmentAdmin(admin.ModelAdmin):

    list_display = (
        'student',
        'course',
        'status',
        'payment_status',
        'progress_percentage',
        'is_active',
        'enrolled_at',
    )

    list_filter = (
        'status',
        'payment_status',
        'is_active',
        'course',
        'enrolled_at',
    )

    search_fields = (
        'student__username',
        'student__first_name',
        'student__last_name',
        'course__title',
    )

    readonly_fields = (
        'enrolled_at',
        'activated_at',
        'completed_at',
    )


@admin.register(LearningPaymentSettings)
class LearningPaymentSettingsAdmin(admin.ModelAdmin):

    list_display = (
        'currency',
        'is_active',
        'payment_support_email',
        'payment_support_phone',
        'updated_at',
    )

    list_filter = (
        'is_active',
        'currency',
    )

    fieldsets = (
        (
            'General',
            {
                'fields': (
                    'currency',
                    'general_payment_instructions',
                    'is_active',
                )
            }
        ),
        (
            'Mobile Money',
            {
                'fields': (
                    'mpesa_business_number',
                    'mpesa_account_name',
                    'airtel_business_number',
                    'airtel_account_name',
                    'mixx_business_number',
                    'mixx_account_name',
                    'require_proof_for_mobile_money',
                )
            }
        ),
        (
            'Bank and Card',
            {
                'fields': (
                    'bank_name',
                    'bank_account_name',
                    'bank_account_number',
                    'bank_branch',
                    'card_instructions',
                    'require_proof_for_bank_transfer',
                )
            }
        ),
        (
            'Support',
            {
                'fields': (
                    'payment_support_email',
                    'payment_support_phone',
                    'updated_at',
                )
            }
        ),
    )

    readonly_fields = (
        'updated_at',
    )


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):

    list_display = (
        'student',
        'course',
        'amount',
        'currency',
        'payment_method',
        'transaction_reference',
        'status',
        'submitted_at',
        'verified_at',
    )

    list_filter = (
        'status',
        'payment_method',
        'currency',
        'course',
        'submitted_at',
        'verified_at',
    )

    search_fields = (
        'student__username',
        'student__first_name',
        'student__last_name',
        'student__email',
        'course__title',
        'transaction_reference',
    )

    autocomplete_fields = (
        'student',
        'course',
        'enrolment',
        'verified_by',
        'rejected_by',
        'refunded_by',
    )

    readonly_fields = (
        'amount',
        'currency',
        'original_filename',
        'proof_file_size',
        'submitted_at',
        'verified_at',
        'verified_by',
        'rejected_at',
        'rejected_by',
        'refunded_at',
        'refunded_by',
        'created_at',
        'updated_at',
    )

    fieldsets = (
        (
            'Payment',
            {
                'fields': (
                    'student',
                    'course',
                    'enrolment',
                    'amount',
                    'currency',
                    'status',
                    'payment_method',
                    'transaction_reference',
                    'proof_of_payment',
                    'original_filename',
                    'proof_file_size',
                )
            }
        ),
        (
            'Notes',
            {
                'fields': (
                    'student_notes',
                    'administrator_notes',
                    'refund_reason',
                )
            }
        ),
        (
            'Audit',
            {
                'fields': (
                    'submitted_at',
                    'verified_by',
                    'verified_at',
                    'rejected_by',
                    'rejected_at',
                    'refunded_by',
                    'refunded_at',
                    'created_at',
                    'updated_at',
                )
            }
        ),
    )

    actions = (
        'confirm_selected_payments',
    )

    def confirm_selected_payments(self, request, queryset):

        confirmed = 0

        for payment in queryset:

            try:
                confirm_payment(payment, request.user)
                confirmed += 1
            except Exception:
                continue

        self.message_user(
            request,
            f'{confirmed} payment(s) confirmed.'
        )

    confirm_selected_payments.short_description = 'Confirm selected pending payments'


@admin.register(CourseReview)
class CourseReviewAdmin(admin.ModelAdmin):

    list_display = (
        'student',
        'course',
        'rating',
        'status',
        'is_approved',
        'created_at',
        'moderated_by',
        'moderated_at',
    )

    list_filter = (
        'status',
        'is_approved',
        'rating',
        'course',
        'created_at',
        'moderated_at',
    )

    search_fields = (
        'student__username',
        'student__first_name',
        'student__last_name',
        'course__title',
        'comment',
        'moderation_notes',
    )

    autocomplete_fields = (
        'student',
        'course',
        'enrolment',
        'moderated_by',
    )

    readonly_fields = (
        'student',
        'course',
        'enrolment',
        'created_at',
        'updated_at',
        'moderated_by',
        'moderated_at',
    )

    date_hierarchy = 'created_at'

    fieldsets = (
        (
            'Review',
            {
                'fields': (
                    'student',
                    'course',
                    'enrolment',
                    'rating',
                    'comment',
                    'status',
                    'is_approved',
                )
            }
        ),
        (
            'Moderation',
            {
                'fields': (
                    'moderation_notes',
                    'moderated_by',
                    'moderated_at',
                )
            }
        ),
        (
            'Timestamps',
            {
                'fields': (
                    'created_at',
                    'updated_at',
                )
            }
        ),
    )

    actions = (
        'approve_selected_reviews',
    )

    def approve_selected_reviews(self, request, queryset):

        approved = 0

        for review in queryset:

            try:
                approve_course_review(review, request.user)
                approved += 1
            except Exception:
                continue

        self.message_user(
            request,
            f'{approved} review(s) approved.'
        )

    approve_selected_reviews.short_description = 'Approve selected pending reviews'


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):

    list_display = (
        'certificate_number',
        'student',
        'course',
        'issued_at',
        'is_valid',
        'revoked_at',
    )

    list_filter = (
        'is_valid',
        'course',
        'issued_at',
        'revoked_at',
    )

    search_fields = (
        'certificate_number',
        'verification_code',
        'student__username',
        'student__first_name',
        'student__last_name',
        'course__title',
    )

    autocomplete_fields = (
        'student',
        'course',
        'enrolment',
        'revoked_by',
        'restored_by',
    )

    readonly_fields = (
        'student',
        'course',
        'enrolment',
        'certificate_number',
        'verification_code',
        'issued_at',
        'revoked_at',
        'revoked_by',
        'restored_at',
        'restored_by',
        'created_at',
        'updated_at',
    )

    date_hierarchy = 'issued_at'

    fieldsets = (
        (
            'Certificate',
            {
                'fields': (
                    'student',
                    'course',
                    'enrolment',
                    'certificate_number',
                    'verification_code',
                    'issued_at',
                    'certificate_file',
                    'is_valid',
                )
            }
        ),
        (
            'Revocation and Restoration',
            {
                'fields': (
                    'revocation_reason',
                    'revoked_by',
                    'revoked_at',
                    'restored_by',
                    'restored_at',
                )
            }
        ),
        (
            'Timestamps',
            {
                'fields': (
                    'created_at',
                    'updated_at',
                )
            }
        ),
    )

    actions = (
        'restore_selected_certificates',
    )

    def restore_selected_certificates(self, request, queryset):

        restored = 0

        for certificate in queryset:

            try:
                restore_certificate(certificate, request.user)
                restored += 1
            except Exception:
                continue

        self.message_user(
            request,
            f'{restored} certificate(s) restored.'
        )

    restore_selected_certificates.short_description = 'Restore selected certificates'


@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):

    list_display = (
        'student',
        'lesson',
        'enrolment',
        'is_completed',
        'started_at',
        'completed_at',
        'last_accessed_at',
    )

    list_filter = (
        'is_completed',
        'lesson__module__course',
        'last_accessed_at',
    )

    search_fields = (
        'student__username',
        'lesson__title',
        'enrolment__course__title',
    )

    readonly_fields = (
        'started_at',
        'last_accessed_at',
    )


@admin.register(CourseAnnouncement)
class CourseAnnouncementAdmin(admin.ModelAdmin):

    list_display = (
        'title',
        'course',
        'author',
        'is_published',
        'notifications_sent',
        'published_at',
        'updated_at',
    )

    list_filter = (
        'is_published',
        'notifications_sent',
        'course',
        'created_at',
    )

    search_fields = (
        'title',
        'message',
        'course__title',
        'author__username',
        'author__first_name',
        'author__last_name',
    )

    readonly_fields = (
        'published_at',
        'notifications_sent',
        'created_at',
        'updated_at',
    )

    date_hierarchy = 'created_at'

    actions = (
        'publish_and_notify',
    )

    def save_model(self, request, obj, form, change):

        was_published = False

        if change:

            was_published = CourseAnnouncement.objects.filter(
                pk=obj.pk,
                is_published=True
            ).exists()

        super().save_model(
            request,
            obj,
            form,
            change
        )

        if obj.is_published and not was_published:

            publish_announcement(
                obj
            )

    def publish_and_notify(self, request, queryset):

        for announcement in queryset:

            publish_announcement(
                announcement
            )

    publish_and_notify.short_description = 'Publish and notify enrolled students'


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):

    list_display = (
        'recipient',
        'title',
        'notification_type',
        'is_read',
        'created_at',
    )

    list_filter = (
        'notification_type',
        'is_read',
        'created_at',
    )

    search_fields = (
        'recipient__username',
        'recipient__first_name',
        'recipient__last_name',
        'title',
        'message',
    )

    readonly_fields = (
        'created_at',
        'read_at',
    )

    date_hierarchy = 'created_at'

    actions = (
        'mark_notifications_read',
    )

    def mark_notifications_read(self, request, queryset):

        queryset.update(
            is_read=True,
            read_at=timezone.now()
        )

    mark_notifications_read.short_description = 'Mark selected notifications as read'


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):

    list_display = (
        'title',
        'lesson',
        'passing_score',
        'attempts_allowed',
        'time_limit_minutes',
        'is_published',
        'updated_at',
    )

    list_filter = (
        'is_published',
        'is_compulsory',
        'lesson__module__course',
        'created_at',
    )

    search_fields = (
        'title',
        'instructions',
        'lesson__title',
        'lesson__module__course__title',
    )

    prepopulated_fields = {
        'slug': (
            'title',
        )
    }

    autocomplete_fields = (
        'lesson',
    )

    readonly_fields = (
        'created_at',
        'updated_at',
    )

    inlines = (
        QuestionInline,
    )

    actions = (
        'publish_quizzes',
        'unpublish_quizzes',
    )

    def publish_quizzes(self, request, queryset):

        queryset.update(
            is_published=True
        )

    publish_quizzes.short_description = 'Publish selected quizzes'

    def unpublish_quizzes(self, request, queryset):

        queryset.update(
            is_published=False
        )

    unpublish_quizzes.short_description = 'Unpublish selected quizzes'


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):

    list_display = (
        'quiz',
        'order',
        'question_type',
        'marks',
        'is_required',
    )

    list_filter = (
        'question_type',
        'is_required',
        'quiz__lesson__module__course',
    )

    search_fields = (
        'question_text',
        'quiz__title',
        'quiz__lesson__module__course__title',
    )

    autocomplete_fields = (
        'quiz',
    )

    inlines = (
        ChoiceInline,
    )


@admin.register(Choice)
class ChoiceAdmin(admin.ModelAdmin):

    list_display = (
        'question',
        'choice_text',
        'is_correct',
        'order',
    )

    list_filter = (
        'is_correct',
        'question__question_type',
    )

    search_fields = (
        'choice_text',
        'question__question_text',
    )

    autocomplete_fields = (
        'question',
    )


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):

    list_display = (
        'student',
        'quiz',
        'attempt_number',
        'status',
        'percentage',
        'passed',
        'submitted_at',
    )

    list_filter = (
        'status',
        'passed',
        'requires_manual_grading',
        'quiz__lesson__module__course',
        'submitted_at',
    )

    search_fields = (
        'student__username',
        'student__first_name',
        'student__last_name',
        'quiz__title',
    )

    autocomplete_fields = (
        'student',
        'quiz',
        'enrolment',
        'graded_by',
    )

    readonly_fields = (
        'objective_marks_awarded',
        'manual_marks_awarded',
        'total_marks_awarded',
        'total_possible_marks',
        'percentage',
        'passed',
        'submitted_at',
        'graded_at',
        'created_at',
        'updated_at',
    )

    date_hierarchy = 'created_at'

    actions = (
        'mark_for_review',
    )

    def mark_for_review(self, request, queryset):

        queryset.update(
            status=QuizAttempt.Status.AWAITING_MANUAL_GRADING,
            requires_manual_grading=True
        )

    mark_for_review.short_description = 'Mark selected attempts for review'


@admin.register(StudentAnswer)
class StudentAnswerAdmin(admin.ModelAdmin):

    list_display = (
        'attempt',
        'question',
        'objective_marks_awarded',
        'manual_marks_awarded',
        'is_correct',
        'graded_at',
    )

    list_filter = (
        'is_correct',
        'question__question_type',
        'graded_at',
    )

    search_fields = (
        'attempt__student__username',
        'question__question_text',
        'text_answer',
    )

    autocomplete_fields = (
        'attempt',
        'question',
        'selected_choices',
        'graded_by',
    )

    readonly_fields = (
        'objective_marks_awarded',
        'created_at',
        'updated_at',
    )


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):

    list_display = (
        'title',
        'lesson',
        'maximum_score',
        'passing_score',
        'due_date',
        'is_compulsory',
        'is_published',
    )

    list_filter = (
        'is_published',
        'is_compulsory',
        'allow_late_submission',
        'allow_resubmission',
        'lesson__module__course',
    )

    search_fields = (
        'title',
        'instructions',
        'lesson__title',
        'lesson__module__course__title',
    )

    prepopulated_fields = {
        'slug': (
            'title',
        )
    }

    autocomplete_fields = (
        'lesson',
    )

    readonly_fields = (
        'created_at',
        'updated_at',
    )

    date_hierarchy = 'created_at'

    fieldsets = (
        (
            'Basic Information',
            {
                'fields': (
                    'lesson',
                    'title',
                    'slug',
                    'instructions',
                    'is_published',
                    'is_compulsory',
                )
            }
        ),
        (
            'Scoring and Attempts',
            {
                'fields': (
                    'maximum_score',
                    'passing_score',
                    'maximum_attempts',
                    'allow_resubmission',
                )
            }
        ),
        (
            'Deadline and Uploads',
            {
                'fields': (
                    'due_date',
                    'allow_late_submission',
                    'require_text_submission',
                    'require_file_submission',
                    'allowed_file_extensions',
                    'maximum_file_size_mb',
                )
            }
        ),
        (
            'Timestamps',
            {
                'fields': (
                    'created_at',
                    'updated_at',
                )
            }
        ),
    )

    actions = (
        'publish_assignments',
        'unpublish_assignments',
    )

    def publish_assignments(self, request, queryset):

        queryset.update(
            is_published=True
        )

    publish_assignments.short_description = 'Publish selected assignments'

    def unpublish_assignments(self, request, queryset):

        queryset.update(
            is_published=False
        )

    unpublish_assignments.short_description = 'Unpublish selected assignments'


@admin.register(AssignmentSubmission)
class AssignmentSubmissionAdmin(admin.ModelAdmin):

    list_display = (
        'student',
        'assignment',
        'attempt_number',
        'status',
        'is_late',
        'score',
        'passed',
        'submitted_at',
        'graded_at',
    )

    list_filter = (
        'status',
        'is_late',
        'passed',
        'assignment__lesson__module__course',
        'submitted_at',
        'graded_at',
    )

    search_fields = (
        'student__username',
        'student__first_name',
        'student__last_name',
        'assignment__title',
        'submission_text',
    )

    autocomplete_fields = (
        'assignment',
        'student',
        'enrolment',
        'graded_by',
        'returned_by',
    )

    readonly_fields = (
        'attempt_number',
        'original_filename',
        'file_size',
        'submitted_at',
        'is_late',
        'score',
        'passed',
        'graded_by',
        'graded_at',
        'returned_at',
        'returned_by',
        'created_at',
        'updated_at',
    )

    date_hierarchy = 'created_at'

    actions = (
        'mark_selected_under_review',
    )

    def mark_selected_under_review(self, request, queryset):

        for submission in queryset:

            mark_submission_under_review(
                submission,
                request.user
            )

    mark_selected_under_review.short_description = 'Mark selected submissions Under Review'
