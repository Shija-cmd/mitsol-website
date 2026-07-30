from django.contrib import admin

from .models import (
    Course,
    CourseCategory,
    Enrolment,
    InstructorProfile,
    Lesson,
    LessonProgress,
    Module,
)


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
