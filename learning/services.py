from django.db import transaction
from django.utils import timezone

from .models import Enrolment, LessonProgress


def recalculate_enrolment_progress(enrolment):

    compulsory_lessons = enrolment.course.modules.filter(
        is_published=True,
        lessons__is_published=True,
        lessons__is_compulsory=True
    ).values_list(
        'lessons__id',
        flat=True
    )

    total_lessons = compulsory_lessons.count()

    if total_lessons == 0:

        progress = 0

    else:

        completed_lessons = LessonProgress.objects.filter(
            enrolment=enrolment,
            lesson_id__in=compulsory_lessons,
            is_completed=True
        ).count()

        progress = round(
            completed_lessons * 100 / total_lessons
        )

    enrolment.progress_percentage = progress

    if progress >= 100 and enrolment.status == Enrolment.Status.ACTIVE:

        enrolment.status = Enrolment.Status.COMPLETED
        enrolment.completed_at = timezone.now()

    enrolment.save(
        update_fields=[
            'progress_percentage',
            'status',
            'completed_at',
        ]
    )

    return enrolment


@transaction.atomic
def enrol_student_in_course(student, course):

    enrolment, created = Enrolment.objects.get_or_create(
        student=student,
        course=course,
        defaults={
            'status': (
                Enrolment.Status.ACTIVE
                if course.is_free
                else Enrolment.Status.PENDING
            ),
            'payment_status': (
                Enrolment.PaymentStatus.NOT_REQUIRED
                if course.is_free
                else Enrolment.PaymentStatus.PENDING
            ),
            'is_active': course.is_free,
            'activated_at': timezone.now() if course.is_free else None,
        }
    )

    return enrolment, created


@transaction.atomic
def mark_lesson_complete(student, enrolment, lesson):

    progress, created = LessonProgress.objects.get_or_create(
        student=student,
        enrolment=enrolment,
        lesson=lesson
    )

    if not progress.is_completed:

        progress.is_completed = True
        progress.completed_at = timezone.now()
        progress.save(
            update_fields=[
                'is_completed',
                'completed_at',
                'last_accessed_at',
            ]
        )

    recalculate_enrolment_progress(
        enrolment
    )

    return progress
