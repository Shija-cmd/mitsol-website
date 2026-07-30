from decimal import Decimal
from datetime import timedelta

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Max
from django.urls import reverse
from django.utils import timezone

from .models import (
    Assignment,
    AssignmentSubmission,
    CourseAnnouncement,
    Enrolment,
    LessonProgress,
    Notification,
    Question,
    QuizAttempt,
    StudentAnswer,
    DANGEROUS_ASSIGNMENT_EXTENSIONS,
)
from .permissions import ensure_course_owner


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

    if created:

        create_notification(
            recipient=student,
            title='Course enrolment received',
            message=(
                f'You have been enrolled in {course.title}.'
                if course.is_free
                else f'Your enrolment request for {course.title} is pending payment confirmation.'
            ),
            notification_type=Notification.NotificationType.ENROLMENT,
            related_url=course.get_absolute_url(),
            dedupe_key=f'enrolment:{enrolment.pk}:created'
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


def evaluate_course_completion(enrolment):

    recalculate_enrolment_progress(
        enrolment
    )

    return enrolment


def create_notification(
    recipient,
    title,
    message,
    notification_type=Notification.NotificationType.SYSTEM,
    related_url='',
    dedupe_key='',
):

    if dedupe_key:

        notification, created = Notification.objects.get_or_create(
            recipient=recipient,
            dedupe_key=dedupe_key,
            defaults={
                'title': title,
                'message': message,
                'notification_type': notification_type,
                'related_url': related_url,
            }
        )

        return notification

    return Notification.objects.create(
        recipient=recipient,
        title=title,
        message=message,
        notification_type=notification_type,
        related_url=related_url,
    )


def get_active_enrolment(student, course):

    return Enrolment.objects.filter(
        student=student,
        course=course,
        status__in=[
            Enrolment.Status.ACTIVE,
            Enrolment.Status.COMPLETED,
        ],
        is_active=True
    ).first()


def quiz_is_accessible(student, quiz):

    lesson = quiz.lesson

    if lesson.is_preview:

        return None

    enrolment = get_active_enrolment(
        student,
        quiz.course
    )

    if not enrolment:

        raise PermissionDenied(
            'You must be actively enrolled to access this quiz.'
        )

    return enrolment


@transaction.atomic
def start_quiz_attempt(student, quiz):

    quiz = quiz.__class__.objects.select_for_update().select_related(
        'lesson',
        'lesson__module',
        'lesson__module__course'
    ).get(
        pk=quiz.pk
    )

    if not quiz.is_published:

        raise PermissionDenied(
            'This quiz is not available.'
        )

    enrolment = quiz_is_accessible(
        student,
        quiz
    )

    active_attempt = QuizAttempt.objects.select_for_update().filter(
        student=student,
        quiz=quiz,
        status=QuizAttempt.Status.IN_PROGRESS
    ).first()

    if active_attempt:

        expire_quiz_attempt_if_needed(
            active_attempt
        )

        if active_attempt.status == QuizAttempt.Status.IN_PROGRESS:

            return active_attempt

    used_attempts = QuizAttempt.objects.select_for_update().filter(
        student=student,
        quiz=quiz
    ).count()

    if used_attempts >= quiz.attempts_allowed:

        raise ValidationError(
            'You have used all allowed attempts for this quiz.'
        )

    next_attempt = (
        QuizAttempt.objects.filter(
            student=student,
            quiz=quiz
        ).aggregate(
            highest=Max('attempt_number')
        )['highest'] or 0
    ) + 1

    expires_at = None

    if quiz.time_limit_minutes:

        expires_at = timezone.now() + timedelta(
            minutes=quiz.time_limit_minutes
        )

    attempt = QuizAttempt.objects.create(
        student=student,
        quiz=quiz,
        enrolment=enrolment,
        attempt_number=next_attempt,
        expires_at=expires_at,
        total_possible_marks=quiz.total_marks
    )

    for question in quiz.questions.all():

        StudentAnswer.objects.get_or_create(
            attempt=attempt,
            question=question
        )

    return attempt


@transaction.atomic
def expire_quiz_attempt_if_needed(attempt):

    attempt = QuizAttempt.objects.select_for_update().select_related(
        'quiz'
    ).get(
        pk=attempt.pk
    )

    if (
        attempt.status == QuizAttempt.Status.IN_PROGRESS
        and attempt.expires_at
        and timezone.now() >= attempt.expires_at
    ):

        _grade_attempt(
            attempt,
            submitted_at=attempt.expires_at,
            expired=True
        )

    return attempt


@transaction.atomic
def submit_quiz_attempt(attempt, submitted_answers):

    attempt = QuizAttempt.objects.select_for_update().select_related(
        'quiz',
        'quiz__lesson',
        'quiz__lesson__module',
        'quiz__lesson__module__course',
        'student'
    ).get(
        pk=attempt.pk
    )

    if attempt.status != QuizAttempt.Status.IN_PROGRESS:

        raise ValidationError(
            'This attempt has already been submitted.'
        )

    if attempt.expires_at and timezone.now() >= attempt.expires_at:

        return expire_quiz_attempt_if_needed(
            attempt
        )

    questions = attempt.quiz.questions.prefetch_related(
        'choices'
    )

    for question in questions:

        answer, created = StudentAnswer.objects.get_or_create(
            attempt=attempt,
            question=question
        )

        payload = submitted_answers.get(
            str(question.pk),
            submitted_answers.get(question.pk, {})
        )

        if question.question_type == Question.QuestionType.SHORT_ANSWER:

            answer.text_answer = (
                payload.get('text_answer', '')
                if isinstance(payload, dict)
                else str(payload or '')
            )
            answer.selected_choices.clear()
            answer.save(
                update_fields=[
                    'text_answer',
                    'updated_at',
                ]
            )

        else:

            choice_ids = payload.get(
                'choice_ids',
                []
            ) if isinstance(payload, dict) else payload

            if not isinstance(choice_ids, (list, tuple, set)):

                choice_ids = [
                    choice_ids,
                ] if choice_ids else []

            try:

                normalized_choice_ids = {
                    int(choice_id)
                    for choice_id in choice_ids
                    if str(choice_id).strip()
                }

            except (TypeError, ValueError):

                raise ValidationError(
                    'One or more submitted choices are invalid.'
                )

            valid_choices = list(
                question.choices.filter(
                    pk__in=normalized_choice_ids
                )
            )
            valid_choice_ids = {
                choice.pk
                for choice in valid_choices
            }

            if valid_choice_ids != normalized_choice_ids:

                raise ValidationError(
                    'One or more submitted choices are invalid.'
                )

            answer.text_answer = ''
            answer.save(
                update_fields=[
                    'text_answer',
                    'updated_at',
                ]
            )
            answer.selected_choices.set(
                valid_choices
            )

    return _grade_attempt(
        attempt,
        submitted_at=timezone.now()
    )


def _grade_attempt(attempt, submitted_at=None, expired=False):

    objective_marks = Decimal('0')
    total_possible = Decimal('0')
    requires_manual = False

    questions = attempt.quiz.questions.prefetch_related(
        'choices'
    )

    for question in questions:

        total_possible += question.marks
        answer, created = StudentAnswer.objects.get_or_create(
            attempt=attempt,
            question=question
        )

        answer.objective_marks_awarded = Decimal('0')
        answer.is_correct = False

        if question.question_type == Question.QuestionType.SHORT_ANSWER:

            requires_manual = True

        else:

            selected_ids = set(
                answer.selected_choices.values_list(
                    'pk',
                    flat=True
                )
            )
            correct_ids = set(
                question.choices.filter(
                    is_correct=True
                ).values_list(
                    'pk',
                    flat=True
                )
            )

            if selected_ids and selected_ids == correct_ids:

                answer.objective_marks_awarded = question.marks
                answer.is_correct = True
                objective_marks += question.marks

        answer.save(
            update_fields=[
                'objective_marks_awarded',
                'is_correct',
                'updated_at',
            ]
        )

    attempt.objective_marks_awarded = objective_marks
    attempt.manual_marks_awarded = Decimal('0')
    attempt.total_possible_marks = total_possible
    attempt.total_marks_awarded = objective_marks
    attempt.requires_manual_grading = requires_manual
    attempt.submitted_at = submitted_at or timezone.now()

    if requires_manual:

        attempt.status = QuizAttempt.Status.AWAITING_MANUAL_GRADING
        attempt.passed = False

    else:

        attempt.status = QuizAttempt.Status.GRADED
        attempt.graded_at = timezone.now()
        _finalize_attempt_score(
            attempt
        )

    if expired and not requires_manual:

        attempt.status = QuizAttempt.Status.EXPIRED

    attempt.save()
    _send_submission_notifications(
        attempt
    )

    if attempt.status == QuizAttempt.Status.GRADED and attempt.passed:

        mark_quiz_lesson_complete(
            attempt
        )

    return attempt


def _finalize_attempt_score(attempt):

    if attempt.total_possible_marks:

        attempt.percentage = (
            attempt.total_marks_awarded * Decimal('100')
            / attempt.total_possible_marks
        ).quantize(
            Decimal('0.01')
        )

    else:

        attempt.percentage = Decimal('0')

    attempt.passed = attempt.percentage >= Decimal(
        str(attempt.quiz.passing_score)
    )


def _send_submission_notifications(attempt):

    result_url = reverse(
        'learning:quiz_result',
        args=[
            attempt.pk,
        ]
    )

    create_notification(
        recipient=attempt.student,
        title='Quiz submitted',
        message=f'Your attempt for {attempt.quiz.title} has been submitted.',
        notification_type=Notification.NotificationType.QUIZ,
        related_url=result_url,
        dedupe_key=f'quiz-attempt:{attempt.pk}:submitted'
    )

    if attempt.status == QuizAttempt.Status.AWAITING_MANUAL_GRADING:

        create_notification(
            recipient=attempt.student,
            title='Quiz awaiting manual grading',
            message=f'{attempt.quiz.title} includes short-answer questions and is awaiting grading.',
            notification_type=Notification.NotificationType.QUIZ,
            related_url=result_url,
            dedupe_key=f'quiz-attempt:{attempt.pk}:awaiting'
        )

        create_notification(
            recipient=attempt.quiz.course.instructor,
            title='Quiz attempt needs grading',
            message=f'{attempt.student} submitted {attempt.quiz.title}.',
            notification_type=Notification.NotificationType.QUIZ,
            related_url=reverse(
                'learning:instructor_quiz_attempt_grade',
                args=[
                    attempt.pk,
                ]
            ),
            dedupe_key=f'quiz-attempt:{attempt.pk}:instructor-grading'
        )

    elif attempt.status == QuizAttempt.Status.GRADED:

        create_notification(
            recipient=attempt.student,
            title='Quiz automatically graded',
            message=f'Your score for {attempt.quiz.title} is {attempt.percentage}%.',
            notification_type=Notification.NotificationType.QUIZ,
            related_url=result_url,
            dedupe_key=f'quiz-attempt:{attempt.pk}:auto-graded'
        )

        create_notification(
            recipient=attempt.student,
            title='Quiz passed' if attempt.passed else 'Quiz failed',
            message=f'You {"passed" if attempt.passed else "did not pass"} {attempt.quiz.title}.',
            notification_type=Notification.NotificationType.QUIZ,
            related_url=result_url,
            dedupe_key=f'quiz-attempt:{attempt.pk}:pass-state'
        )


@transaction.atomic
def grade_short_answers(attempt, grader, grading_data):

    attempt = QuizAttempt.objects.select_for_update().select_related(
        'quiz',
        'quiz__lesson',
        'quiz__lesson__module',
        'quiz__lesson__module__course',
        'student'
    ).get(
        pk=attempt.pk
    )

    ensure_course_owner(
        grader,
        attempt.quiz.course
    )

    if attempt.status not in [
        QuizAttempt.Status.AWAITING_MANUAL_GRADING,
        QuizAttempt.Status.GRADED,
    ]:

        raise ValidationError(
            'This attempt is not ready for manual grading.'
        )

    manual_total = Decimal('0')

    for answer in attempt.answers.select_related('question').filter(
        question__question_type=Question.QuestionType.SHORT_ANSWER
    ):

        data = grading_data.get(
            str(answer.pk),
            grading_data.get(answer.pk, {})
        )
        marks = Decimal(
            str(data.get('marks', 0) or 0)
        )

        if marks < 0 or marks > answer.question.marks:

            raise ValidationError(
                'Manual marks must be between zero and the question marks.'
            )

        answer.manual_marks_awarded = marks
        answer.instructor_feedback = data.get(
            'feedback',
            ''
        )
        answer.graded_by = grader
        answer.graded_at = timezone.now()
        answer.save()
        manual_total += marks

    attempt.manual_marks_awarded = manual_total
    attempt.total_marks_awarded = attempt.objective_marks_awarded + manual_total
    attempt.instructor_feedback = grading_data.get(
        'instructor_feedback',
        attempt.instructor_feedback
    )
    attempt.status = QuizAttempt.Status.GRADED
    attempt.requires_manual_grading = False
    attempt.graded_by = grader
    attempt.graded_at = timezone.now()
    _finalize_attempt_score(
        attempt
    )
    attempt.save()

    create_notification(
        recipient=attempt.student,
        title='Quiz manually graded',
        message=f'Your result for {attempt.quiz.title} is now available.',
        notification_type=Notification.NotificationType.QUIZ,
        related_url=reverse(
            'learning:quiz_result',
            args=[
                attempt.pk,
            ]
        ),
        dedupe_key=f'quiz-attempt:{attempt.pk}:manual-graded'
    )

    create_notification(
        recipient=attempt.student,
        title='Quiz passed' if attempt.passed else 'Quiz failed',
        message=f'You {"passed" if attempt.passed else "did not pass"} {attempt.quiz.title}.',
        notification_type=Notification.NotificationType.QUIZ,
        related_url=reverse(
            'learning:quiz_result',
            args=[
                attempt.pk,
            ]
        ),
        dedupe_key=f'quiz-attempt:{attempt.pk}:manual-pass-state'
    )

    if attempt.passed:

        mark_quiz_lesson_complete(
            attempt
        )

    return attempt


def mark_quiz_lesson_complete(attempt):

    if not attempt.enrolment:

        return None

    quiz = attempt.quiz

    if quiz.is_compulsory or quiz.lesson.is_compulsory:

        return mark_lesson_complete(
            attempt.student,
            attempt.enrolment,
            quiz.lesson
        )

    return evaluate_course_completion(
        attempt.enrolment
    )


def assignment_file_extension(filename):

    return filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''


def validate_assignment_file(assignment, uploaded_file):

    if not uploaded_file:

        return

    filename = uploaded_file.name or ''

    if len(filename) > 255:

        raise ValidationError(
            'The filename is too long.'
        )

    extension = assignment_file_extension(
        filename
    )

    if not extension or extension in DANGEROUS_ASSIGNMENT_EXTENSIONS:

        raise ValidationError(
            'The selected file type is not allowed.'
        )

    if extension not in assignment.allowed_extension_list:

        raise ValidationError(
            'The selected file type is not allowed.'
        )

    if uploaded_file.size <= 0:

        raise ValidationError(
            'The selected file is empty.'
        )

    max_bytes = assignment.maximum_file_size_mb * 1024 * 1024

    if uploaded_file.size > max_bytes:

        raise ValidationError(
            f'The file exceeds the maximum size of {assignment.maximum_file_size_mb} MB.'
        )


def can_access_assignment(user, assignment):

    if not assignment.is_published and not (
        user.is_authenticated
        and (
            user.is_staff
            or assignment.course.instructor_id == user.id
        )
    ):

        raise PermissionDenied(
            'This assignment is not available.'
        )

    if assignment.lesson.is_preview:

        return None

    if user.is_authenticated and (
        user.is_staff
        or assignment.course.instructor_id == user.id
    ):

        return None

    if not user.is_authenticated:

        raise PermissionDenied(
            'Please sign in and enrol to access this assignment.'
        )

    enrolment = get_active_enrolment(
        user,
        assignment.course
    )

    if not enrolment:

        raise PermissionDenied(
            'You must be actively enrolled to access this assignment.'
        )

    return enrolment


def assignment_accepts_submission(assignment):

    if (
        assignment.due_date
        and timezone.now() > assignment.due_date
        and not assignment.allow_late_submission
    ):

        raise ValidationError(
            'The assignment deadline has passed.'
        )


@transaction.atomic
def get_or_create_assignment_draft(student, assignment):

    assignment = Assignment.objects.select_for_update().select_related(
        'lesson',
        'lesson__module',
        'lesson__module__course'
    ).get(
        pk=assignment.pk
    )

    if not assignment.is_published:

        raise PermissionDenied(
            'This assignment is not available.'
        )

    assignment_accepts_submission(
        assignment
    )

    enrolment = get_active_enrolment(
        student,
        assignment.course
    )

    if not enrolment:

        raise PermissionDenied(
            'You must be actively enrolled to submit this assignment.'
        )

    draft = AssignmentSubmission.objects.select_for_update().filter(
        assignment=assignment,
        student=student,
        status=AssignmentSubmission.Status.DRAFT
    ).first()

    if draft:

        return draft, enrolment

    used_attempts = AssignmentSubmission.objects.select_for_update().filter(
        assignment=assignment,
        student=student
    ).count()

    if used_attempts >= assignment.maximum_attempts:

        raise ValidationError(
            'You have used all permitted submission attempts.'
        )

    latest_returned = AssignmentSubmission.objects.filter(
        assignment=assignment,
        student=student,
        status=AssignmentSubmission.Status.RETURNED
    ).order_by(
        '-attempt_number'
    ).first()

    if used_attempts and not (
        assignment.allow_resubmission
        and latest_returned
    ):

        raise ValidationError(
            'Resubmission is not available for this assignment.'
        )

    next_attempt = (
        AssignmentSubmission.objects.filter(
            assignment=assignment,
            student=student
        ).aggregate(
            highest=Max('attempt_number')
        )['highest'] or 0
    ) + 1

    draft = AssignmentSubmission.objects.create(
        assignment=assignment,
        student=student,
        enrolment=enrolment,
        attempt_number=next_attempt
    )

    return draft, enrolment


@transaction.atomic
def save_assignment_draft(submission, student, cleaned_data):

    submission = AssignmentSubmission.objects.select_for_update().select_related(
        'assignment',
        'assignment__lesson',
        'assignment__lesson__module',
        'assignment__lesson__module__course',
        'student'
    ).get(
        pk=submission.pk
    )

    if submission.student_id != student.id:

        raise PermissionDenied(
            'You cannot edit this submission.'
        )

    if submission.status != AssignmentSubmission.Status.DRAFT:

        raise ValidationError(
            'Submitted work cannot be edited.'
        )

    assignment_accepts_submission(
        submission.assignment
    )

    uploaded_file = cleaned_data.get(
        'submission_file'
    )

    if uploaded_file:

        validate_assignment_file(
            submission.assignment,
            uploaded_file
        )
        submission.submission_file = uploaded_file
        submission.original_filename = uploaded_file.name
        submission.file_size = uploaded_file.size

    submission.submission_text = cleaned_data.get(
        'submission_text',
        ''
    )
    submission.save()

    return submission


def validate_assignment_submission_content(submission):

    assignment = submission.assignment

    if assignment.require_text_submission and not submission.submission_text.strip():

        raise ValidationError(
            'A written response is required.'
        )

    if assignment.require_file_submission and not submission.submission_file:

        raise ValidationError(
            'A file submission is required.'
        )


@transaction.atomic
def submit_assignment(submission, student):

    submission = AssignmentSubmission.objects.select_for_update().select_related(
        'assignment',
        'assignment__lesson',
        'assignment__lesson__module',
        'assignment__lesson__module__course',
        'student'
    ).get(
        pk=submission.pk
    )

    if submission.student_id != student.id:

        raise PermissionDenied(
            'You cannot submit this assignment.'
        )

    if submission.status == AssignmentSubmission.Status.SUBMITTED:

        return submission

    if submission.status != AssignmentSubmission.Status.DRAFT:

        raise ValidationError(
            'This submission cannot be finalized.'
        )

    assignment_accepts_submission(
        submission.assignment
    )
    validate_assignment_submission_content(
        submission
    )

    if submission.submission_file:

        validate_assignment_file(
            submission.assignment,
            submission.submission_file
        )

    now = timezone.now()
    submission.is_late = bool(
        submission.assignment.due_date
        and now > submission.assignment.due_date
    )
    submission.status = AssignmentSubmission.Status.SUBMITTED
    submission.submitted_at = now
    submission.save()

    detail_url = reverse(
        'learning:submission_detail',
        args=[
            submission.pk,
        ]
    )

    create_notification(
        recipient=submission.student,
        title='Assignment submitted',
        message=f'Your submission for {submission.assignment.title} has been received.',
        notification_type=Notification.NotificationType.ASSIGNMENT,
        related_url=detail_url,
        dedupe_key=f'assignment-submission:{submission.pk}:submitted-student'
    )
    create_notification(
        recipient=submission.assignment.course.instructor,
        title='Assignment submitted',
        message=f'{submission.student} submitted {submission.assignment.title}.',
        notification_type=Notification.NotificationType.ASSIGNMENT,
        related_url=reverse(
            'learning:instructor_submission_detail',
            args=[
                submission.pk,
            ]
        ),
        dedupe_key=f'assignment-submission:{submission.pk}:submitted-instructor'
    )

    return submission


@transaction.atomic
def mark_submission_under_review(submission, instructor):

    submission = AssignmentSubmission.objects.select_for_update().select_related(
        'assignment',
        'assignment__lesson',
        'assignment__lesson__module',
        'assignment__lesson__module__course'
    ).get(
        pk=submission.pk
    )

    ensure_course_owner(
        instructor,
        submission.assignment.course
    )

    if submission.status == AssignmentSubmission.Status.SUBMITTED:

        submission.status = AssignmentSubmission.Status.UNDER_REVIEW
        submission.save(
            update_fields=[
                'status',
                'updated_at',
            ]
        )

    return submission


@transaction.atomic
def grade_assignment_submission(submission, grader, score, feedback):

    submission = AssignmentSubmission.objects.select_for_update().select_related(
        'assignment',
        'assignment__lesson',
        'assignment__lesson__module',
        'assignment__lesson__module__course',
        'student',
        'enrolment'
    ).get(
        pk=submission.pk
    )

    ensure_course_owner(
        grader,
        submission.assignment.course
    )

    if submission.status not in [
        AssignmentSubmission.Status.SUBMITTED,
        AssignmentSubmission.Status.UNDER_REVIEW,
        AssignmentSubmission.Status.GRADED,
    ]:

        raise ValidationError(
            'This submission is not ready for grading.'
        )

    score = Decimal(
        str(score)
    )

    if score < 0 or score > submission.assignment.maximum_score:

        raise ValidationError(
            'Score must be between zero and the maximum score.'
        )

    submission.score = score
    submission.passed = score >= submission.assignment.passing_score
    submission.instructor_feedback = feedback
    submission.graded_by = grader
    submission.graded_at = timezone.now()
    submission.status = AssignmentSubmission.Status.GRADED
    submission.save()

    create_notification(
        recipient=submission.student,
        title='Assignment graded',
        message=f'Your submission for {submission.assignment.title} has been graded.',
        notification_type=Notification.NotificationType.ASSIGNMENT,
        related_url=reverse(
            'learning:submission_detail',
            args=[
                submission.pk,
            ]
        ),
        dedupe_key=f'assignment-submission:{submission.pk}:graded'
    )
    create_notification(
        recipient=submission.student,
        title='Assignment passed' if submission.passed else 'Assignment failed',
        message=f'You {"passed" if submission.passed else "did not pass"} {submission.assignment.title}.',
        notification_type=Notification.NotificationType.ASSIGNMENT,
        related_url=reverse(
            'learning:submission_detail',
            args=[
                submission.pk,
            ]
        ),
        dedupe_key=f'assignment-submission:{submission.pk}:pass-state'
    )

    if submission.passed:

        mark_assignment_lesson_complete(
            submission
        )

    return submission


@transaction.atomic
def return_assignment_for_revision(submission, grader, revision_message):

    if not revision_message.strip():

        raise ValidationError(
            'Revision message is required.'
        )

    submission = AssignmentSubmission.objects.select_for_update().select_related(
        'assignment',
        'assignment__lesson',
        'assignment__lesson__module',
        'assignment__lesson__module__course',
        'student'
    ).get(
        pk=submission.pk
    )

    ensure_course_owner(
        grader,
        submission.assignment.course
    )

    if not submission.assignment.allow_resubmission:

        raise ValidationError(
            'This assignment does not allow resubmission.'
        )

    used_attempts = AssignmentSubmission.objects.filter(
        assignment=submission.assignment,
        student=submission.student
    ).count()

    if used_attempts >= submission.assignment.maximum_attempts:

        raise ValidationError(
            'No submission attempts remain.'
        )

    if submission.status == AssignmentSubmission.Status.RETURNED:

        return submission

    submission.status = AssignmentSubmission.Status.RETURNED
    submission.returned_by = grader
    submission.returned_at = timezone.now()
    submission.revision_message = revision_message
    submission.save()

    create_notification(
        recipient=submission.student,
        title='Assignment returned for revision',
        message=f'{submission.assignment.title} was returned for revision.',
        notification_type=Notification.NotificationType.ASSIGNMENT,
        related_url=reverse(
            'learning:submission_detail',
            args=[
                submission.pk,
            ]
        ),
        dedupe_key=f'assignment-submission:{submission.pk}:returned'
    )

    return submission


def mark_assignment_lesson_complete(submission):

    if not submission.enrolment:

        return None

    if submission.assignment.is_compulsory or submission.assignment.lesson.is_compulsory:

        return mark_lesson_complete(
            submission.student,
            submission.enrolment,
            submission.assignment.lesson
        )

    return evaluate_course_completion(
        submission.enrolment
    )


@transaction.atomic
def publish_announcement(announcement):

    announcement = CourseAnnouncement.objects.select_for_update().select_related(
        'course'
    ).get(
        pk=announcement.pk
    )

    if not announcement.is_published:

        announcement.is_published = True
        announcement.published_at = timezone.now()
        announcement.save(
            update_fields=[
                'is_published',
                'published_at',
                'updated_at',
            ]
        )

    send_announcement_notifications(
        announcement
    )

    return announcement


@transaction.atomic
def send_announcement_notifications(announcement):

    announcement = CourseAnnouncement.objects.select_for_update().select_related(
        'course'
    ).get(
        pk=announcement.pk
    )

    if announcement.notifications_sent:

        return 0

    enrolments = Enrolment.objects.select_related(
        'student'
    ).filter(
        course=announcement.course,
        status__in=[
            Enrolment.Status.ACTIVE,
            Enrolment.Status.COMPLETED,
        ],
        is_active=True
    )

    sent_count = 0

    for enrolment in enrolments:

        create_notification(
            recipient=enrolment.student,
            title=announcement.title,
            message=announcement.message,
            notification_type=Notification.NotificationType.ANNOUNCEMENT,
            related_url=reverse('learning:announcements'),
            dedupe_key=f'announcement:{announcement.pk}:student:{enrolment.student_id}'
        )
        sent_count += 1

    announcement.notifications_sent = True
    announcement.save(
        update_fields=[
            'notifications_sent',
            'updated_at',
        ]
    )

    return sent_count
