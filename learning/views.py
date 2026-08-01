import re
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group, User
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import FileResponse, Http404, HttpResponse
from django.core.paginator import Paginator
from django.db.models import Avg, Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import (
    AssignmentForm,
    AssignmentGradingForm,
    AssignmentRevisionForm,
    AssignmentSubmissionForm,
    CertificateRevocationForm,
    CertificateVerificationForm,
    ChoiceForm,
    CourseAnnouncementForm,
    CourseReviewForm,
    CourseForm,
    InstructorProfileForm,
    LessonForm,
    ManualQuizGradingForm,
    ModuleForm,
    PaymentReasonForm,
    PaymentSubmissionForm,
    QuestionForm,
    QuizAttemptForm,
    QuizForm,
    ReviewModerationReasonForm,
    StudentRegistrationForm,
)
from .models import (
    Assignment,
    AssignmentSubmission,
    Choice,
    Certificate,
    Course,
    CourseAnnouncement,
    CourseCategory,
    CourseReview,
    Enrolment,
    InstructorProfile,
    Lesson,
    LessonProgress,
    Notification,
    Payment,
    LearningPaymentSettings,
    Question,
    Quiz,
    QuizAttempt,
    StudentAnswer,
)
from .permissions import STUDENT_GROUP, ensure_course_owner, instructor_required, is_instructor
from .services import (
    can_access_assignment,
    approve_course_review,
    attach_rating_summaries,
    can_student_review_course,
    certificate_verification_url,
    confirm_payment,
    create_course_review,
    enrol_student_in_course,
    expire_quiz_attempt_if_needed,
    get_or_create_assignment_draft,
    get_or_create_paid_course_enrolment,
    get_course_payable_amount,
    get_learning_payment_settings,
    get_course_rating_summary,
    find_certificate,
    generate_certificate_pdf,
    evaluate_course_completion,
    grade_assignment_submission,
    grade_short_answers,
    mark_lesson_complete,
    mark_submission_under_review,
    mark_payment_refunded,
    publish_announcement,
    quiz_is_accessible,
    recalculate_enrolment_progress,
    return_assignment_for_revision,
    reject_payment,
    reject_course_review,
    save_assignment_draft,
    hide_course_review,
    restore_certificate,
    revoke_certificate,
    start_quiz_attempt,
    submit_assignment,
    submit_course_payment,
    submit_quiz_attempt,
    update_course_review,
    user_can_manage_certificates,
)


def learning_home(request):

    featured_courses = attach_rating_summaries(published_courses().filter(
        is_featured=True
    )[:3])

    recent_courses = attach_rating_summaries(published_courses()[:6])

    categories = CourseCategory.objects.filter(
        is_active=True
    ).annotate(
        course_count=Count(
            'courses',
            filter=Q(courses__is_published=True)
        )
    )[:8]

    instructors = InstructorProfile.objects.select_related(
        'user'
    ).filter(
        is_active=True,
        user__learning_courses__is_published=True,
        user__learning_courses__status=Course.Status.PUBLISHED,
    ).annotate(
        course_count=Count('user__learning_courses', distinct=True)
    ).order_by(
        'user__first_name',
        'user__last_name',
        'user__username',
    )[:4]

    stats = {
        'courses': published_courses().count(),
        'categories': CourseCategory.objects.filter(is_active=True).count(),
        'students': Enrolment.objects.values('student').distinct().count(),
        'lessons': Lesson.objects.filter(is_published=True).count(),
    }

    return render(
        request,
        'learning/home.html',
        {
            'featured_courses': featured_courses,
            'recent_courses': recent_courses,
            'categories': categories,
            'instructors': instructors,
            'stats': stats,
        }
    )


def course_catalogue(request):

    courses = filter_courses(
        request,
        published_courses()
    )

    paginator = Paginator(
        courses,
        9
    )

    page_obj = paginator.get_page(
        request.GET.get('page')
    )
    page_obj.object_list = attach_rating_summaries(page_obj.object_list)

    return render(
        request,
        'learning/course_list.html',
        catalogue_context(
            request,
            page_obj
        )
    )


def category_courses(request, slug):

    category = get_object_or_404(
        CourseCategory,
        slug=slug,
        is_active=True
    )

    courses = filter_courses(
        request,
        published_courses().filter(
            category=category
        )
    )

    paginator = Paginator(
        courses,
        9
    )

    page_obj = paginator.get_page(
        request.GET.get('page')
    )
    page_obj.object_list = attach_rating_summaries(page_obj.object_list)

    context = catalogue_context(
        request,
        page_obj
    )

    context['current_category'] = category

    return render(
        request,
        'learning/course_list.html',
        context
    )


def instructor_list(request):

    instructors = InstructorProfile.objects.select_related(
        'user'
    ).filter(
        is_active=True,
        user__learning_courses__is_published=True,
        user__learning_courses__status=Course.Status.PUBLISHED,
    ).annotate(
        course_count=Count('user__learning_courses', distinct=True)
    ).order_by(
        'user__first_name',
        'user__last_name',
        'user__username',
    )

    return render(
        request,
        'learning/instructors/list.html',
        {
            'instructors': instructors,
        }
    )


def instructor_profile_detail(request, username):

    profile = get_object_or_404(
        InstructorProfile.objects.select_related('user'),
        user__username=username,
        is_active=True,
    )
    courses = attach_rating_summaries(
        published_courses().filter(
            instructor=profile.user
        )
    )

    return render(
        request,
        'learning/instructors/detail.html',
        {
            'profile': profile,
            'courses': courses,
        }
    )


def course_detail(request, slug):

    course = get_object_or_404(
        published_courses().prefetch_related(
            'modules__lessons'
        ),
        slug=slug
    )

    enrolment = None

    if request.user.is_authenticated:

        enrolment = Enrolment.objects.filter(
            student=request.user,
            course=course
        ).first()

    pending_payment = None
    latest_payment = None
    existing_review = None
    instructor_profile = InstructorProfile.objects.filter(
        user=course.instructor,
        is_active=True,
    ).first()
    can_review = False
    review_reason = ''

    if enrolment:

        pending_payment = enrolment.payments.filter(
            status=Payment.Status.PENDING
        ).first()
        latest_payment = enrolment.payments.first()
        if enrolment.status in [
            Enrolment.Status.ACTIVE,
            Enrolment.Status.COMPLETED,
        ]:
            try:
                completion_result = evaluate_course_completion(enrolment)
                enrolment = completion_result.enrolment
            except ValidationError:
                completion_result = None
        else:
            completion_result = None
    else:
        completion_result = None

    if request.user.is_authenticated:

        existing_review = CourseReview.objects.filter(
            student=request.user,
            course=course
        ).first()
        can_review, review_enrolment, review_reason = can_student_review_course(
            request.user,
            course,
            include_existing_check=False
        )

        if existing_review:

            can_review = False

    approved_reviews = CourseReview.objects.select_related(
        'student',
        'enrolment'
    ).filter(
        course=course,
        status=CourseReview.Status.APPROVED,
        is_approved=True
    )

    review_sort = request.GET.get(
        'review_sort',
        'recent'
    )
    review_ordering = {
        'recent': '-created_at',
        'oldest': 'created_at',
        'highest': '-rating',
        'lowest': 'rating',
    }
    review_sort = review_sort if review_sort in review_ordering else 'recent'
    approved_reviews = approved_reviews.order_by(
        review_ordering[review_sort]
    )
    review_paginator = Paginator(
        approved_reviews,
        10
    )
    review_page = review_paginator.get_page(
        request.GET.get('review_page')
    )

    return render(
        request,
        'learning/course_detail.html',
        {
            'course': course,
            'enrolment': enrolment,
            'pending_payment': pending_payment,
            'latest_payment': latest_payment,
            'existing_review': existing_review,
            'can_review': can_review,
            'review_reason': review_reason,
            'rating_summary': get_course_rating_summary(course),
            'review_page': review_page,
            'review_sort': review_sort,
            'completion_result': completion_result,
            'instructor_profile': instructor_profile,
        }
    )


@login_required
def enrol_course(request, slug):

    course = get_object_or_404(
        published_courses(),
        slug=slug
    )

    if not course.is_free:

        enrolment, created = get_or_create_paid_course_enrolment(
            request.user,
            course
        )

        messages.info(
            request,
            'Your enrolment request is ready. Please submit payment for verification.'
        )

        return redirect(
            'learning:payment_course',
            slug=course.slug
        )

    enrolment, created = enrol_student_in_course(request.user, course)

    if created and course.is_free:

        messages.success(
            request,
            'You are enrolled. You can start learning now.'
        )

    elif created:

        messages.info(
            request,
            'Your enrolment request has been submitted. MITSOL will confirm payment before access is activated.'
        )

    else:

        messages.info(
            request,
            'You are already enrolled in this course.'
        )

    return redirect(
        'learning:course_detail',
        slug=course.slug
    )


@login_required
def my_courses(request):

    enrolments = Enrolment.objects.select_related(
        'course',
        'course__category'
    ).filter(
        student=request.user
    )

    return render(
        request,
        'learning/my_courses.html',
        {
            'active_enrolments': enrolments.filter(status=Enrolment.Status.ACTIVE),
            'pending_enrolments': enrolments.filter(status=Enrolment.Status.PENDING),
            'completed_enrolments': enrolments.filter(status=Enrolment.Status.COMPLETED),
            'suspended_enrolments': enrolments.filter(status=Enrolment.Status.SUSPENDED),
        }
    )


@login_required
def student_dashboard(request):

    enrolments = Enrolment.objects.select_related(
        'course'
    ).filter(
        student=request.user
    )

    recent_progress = LessonProgress.objects.select_related(
        'lesson',
        'lesson__module',
        'lesson__module__course'
    ).filter(
        student=request.user
    )[:5]

    recent_announcements = CourseAnnouncement.objects.select_related(
        'course',
        'author'
    ).filter(
        is_published=True,
        course__enrolments__student=request.user,
        course__enrolments__is_active=True,
        course__enrolments__status__in=[
            Enrolment.Status.ACTIVE,
            Enrolment.Status.COMPLETED,
        ],
    ).distinct()[:5]

    quiz_attempts = QuizAttempt.objects.select_related(
        'quiz',
        'quiz__lesson',
        'quiz__lesson__module',
        'quiz__lesson__module__course'
    ).filter(
        student=request.user
    )

    in_progress_attempts = quiz_attempts.filter(
        status=QuizAttempt.Status.IN_PROGRESS
    )

    assignment_submissions = AssignmentSubmission.objects.select_related(
        'assignment',
        'assignment__lesson',
        'assignment__lesson__module',
        'assignment__lesson__module__course'
    ).filter(
        student=request.user
    )

    upcoming_assignments = Assignment.objects.select_related(
        'lesson',
        'lesson__module',
        'lesson__module__course'
    ).filter(
        is_published=True,
        lesson__module__course__enrolments__student=request.user,
        lesson__module__course__enrolments__is_active=True,
        due_date__isnull=False,
        due_date__gte=timezone.now()
    ).distinct().order_by(
        'due_date'
    )[:5]

    payments = Payment.objects.select_related(
        'course'
    ).filter(
        student=request.user
    )

    certificates = Certificate.objects.select_related(
        'course'
    ).filter(
        student=request.user
    )

    reviews = CourseReview.objects.select_related(
        'course'
    ).filter(
        student=request.user
    )

    reviewed_course_ids = reviews.values_list(
        'course_id',
        flat=True
    )
    eligible_courses = []

    for enrolment in enrolments.select_related('course'):
        eligible, review_enrolment, reason = can_student_review_course(
            request.user,
            enrolment.course,
            include_existing_check=False
        )
        if eligible and enrolment.course_id not in reviewed_course_ids:
            eligible_courses.append(enrolment.course)

    return render(
        request,
        'learning/dashboard.html',
        {
            'enrolments': enrolments[:6],
            'recent_progress': recent_progress,
            'active_count': enrolments.filter(status=Enrolment.Status.ACTIVE).count(),
            'completed_count': enrolments.filter(status=Enrolment.Status.COMPLETED).count(),
            'pending_count': enrolments.filter(status=Enrolment.Status.PENDING).count(),
            'recent_announcements': recent_announcements,
            'recent_quiz_attempts': quiz_attempts[:5],
            'in_progress_quiz_attempts': in_progress_attempts,
            'pending_quiz_attempts': quiz_attempts.filter(status=QuizAttempt.Status.AWAITING_MANUAL_GRADING),
            'passed_quiz_count': QuizAttempt.objects.filter(student=request.user, passed=True).count(),
            'failed_quiz_count': QuizAttempt.objects.filter(student=request.user, status=QuizAttempt.Status.GRADED, passed=False).count(),
            'draft_assignments': assignment_submissions.filter(status=AssignmentSubmission.Status.DRAFT)[:5],
            'returned_assignments': assignment_submissions.filter(status=AssignmentSubmission.Status.RETURNED)[:5],
            'recent_assignment_submissions': assignment_submissions.exclude(status=AssignmentSubmission.Status.DRAFT)[:5],
            'upcoming_assignments': upcoming_assignments,
            'passed_assignment_count': assignment_submissions.filter(status=AssignmentSubmission.Status.GRADED, passed=True).count(),
            'failed_assignment_count': assignment_submissions.filter(status=AssignmentSubmission.Status.GRADED, passed=False).count(),
            'recent_payments': payments[:5],
            'pending_payment_count': payments.filter(status=Payment.Status.PENDING).count(),
            'rejected_payment_count': payments.filter(status=Payment.Status.REJECTED).count(),
            'recent_reviews': reviews[:5],
            'pending_review_count': reviews.filter(status=CourseReview.Status.PENDING).count(),
            'approved_review_count': reviews.filter(status=CourseReview.Status.APPROVED).count(),
            'rejected_review_count': reviews.filter(status=CourseReview.Status.REJECTED).count(),
            'eligible_review_courses': eligible_courses[:5],
            'certificate_count': certificates.filter(is_valid=True).count(),
            'revoked_certificate_count': certificates.filter(is_valid=False).count(),
            'recent_certificates': certificates[:3],
        }
    )


def lesson_detail(request, course_slug, lesson_slug):

    lesson = get_object_or_404(
        Lesson.objects.select_related(
            'module',
            'module__course'
        ),
        module__course__slug=course_slug,
        slug=lesson_slug,
        is_published=True,
        module__is_published=True,
        module__course__is_published=True
    )

    course = lesson.module.course
    enrolment = None

    if request.user.is_authenticated:

        enrolment = Enrolment.objects.filter(
            student=request.user,
            course=course,
            status__in=[
                Enrolment.Status.ACTIVE,
                Enrolment.Status.COMPLETED,
            ],
            is_active=True,
            payment_status__in=[
                Enrolment.PaymentStatus.NOT_REQUIRED,
                Enrolment.PaymentStatus.PAID,
            ],
        ).first()

    if not lesson.is_preview and not enrolment:

        messages.warning(
            request,
            'Please enrol in this course to access this lesson.'
        )

        return redirect(
            'learning:course_detail',
            slug=course.slug
        )

    progress = None

    if enrolment:

        progress, created = LessonProgress.objects.get_or_create(
            student=request.user,
            enrolment=enrolment,
            lesson=lesson
        )

    if request.method == 'POST' and enrolment:

        if lesson.lesson_type in [
            Lesson.LessonType.QUIZ,
            Lesson.LessonType.ASSIGNMENT,
        ]:

            messages.info(
                request,
                'This lesson is completed through its assessment workflow.'
            )

            return redirect(
                'learning:lesson_detail',
                course_slug=course.slug,
                lesson_slug=lesson.slug
            )

        mark_lesson_complete(
            request.user,
            enrolment,
            lesson
        )

        messages.success(
            request,
            'Lesson marked as complete.'
        )

        return redirect(
            'learning:lesson_detail',
            course_slug=course.slug,
            lesson_slug=lesson.slug
        )

    quiz = getattr(
        lesson,
        'quiz',
        None
    )
    assignment = getattr(
        lesson,
        'assignment',
        None
    )
    quiz_attempts = QuizAttempt.objects.none()
    latest_quiz_attempt = None
    assignment_submissions = AssignmentSubmission.objects.none()
    latest_assignment_submission = None

    if quiz and request.user.is_authenticated:

        quiz_attempts = QuizAttempt.objects.filter(
            student=request.user,
            quiz=quiz
        )
        latest_quiz_attempt = quiz_attempts.first()

    if assignment and request.user.is_authenticated:

        assignment_submissions = AssignmentSubmission.objects.filter(
            student=request.user,
            assignment=assignment
        )
        latest_assignment_submission = assignment_submissions.first()

    return render(
        request,
        'learning/lesson_detail.html',
        {
            'course': course,
            'lesson': lesson,
            'enrolment': enrolment,
            'progress': progress,
            'quiz': quiz,
            'quiz_attempts': quiz_attempts,
            'latest_quiz_attempt': latest_quiz_attempt,
            'assignment': assignment,
            'assignment_submissions': assignment_submissions,
            'latest_assignment_submission': latest_assignment_submission,
        }
    )


@instructor_required
def instructor_dashboard(request):

    courses = instructor_courses(
        request.user
    )

    enrolments = Enrolment.objects.filter(
        course__in=courses
    )

    attempts = QuizAttempt.objects.filter(
        quiz__lesson__module__course__in=courses
    )

    assignment_submissions = AssignmentSubmission.objects.filter(
        assignment__lesson__module__course__in=courses
    )

    payments = Payment.objects.filter(
        course__in=courses
    )

    reviews = CourseReview.objects.filter(
        course__in=courses
    )
    approved_reviews = reviews.filter(
        status=CourseReview.Status.APPROVED,
        is_approved=True
    )
    certificates = Certificate.objects.filter(
        course__in=courses
    )

    return render(
        request,
        'learning/instructor/dashboard.html',
        {
            'courses': courses[:5],
            'total_courses': courses.count(),
            'published_courses': courses.filter(is_published=True).count(),
            'draft_courses': courses.filter(status=Course.Status.DRAFT).count(),
            'total_students': enrolments.values('student').distinct().count(),
            'recent_enrolments': enrolments.select_related('student', 'course')[:5],
            'total_quiz_attempts': attempts.count(),
            'pending_grading_count': attempts.filter(status=QuizAttempt.Status.AWAITING_MANUAL_GRADING).count(),
            'recent_quiz_attempts': attempts.select_related('student', 'quiz')[:5],
            'average_quiz_score': attempts.filter(status=QuizAttempt.Status.GRADED).aggregate(avg=Avg('percentage'))['avg'],
            'total_assignment_submissions': assignment_submissions.count(),
            'pending_assignment_grading_count': assignment_submissions.filter(
                status__in=[
                    AssignmentSubmission.Status.SUBMITTED,
                    AssignmentSubmission.Status.UNDER_REVIEW,
                ]
            ).count(),
            'late_assignment_count': assignment_submissions.filter(is_late=True).count(),
            'returned_assignment_count': assignment_submissions.filter(status=AssignmentSubmission.Status.RETURNED).count(),
            'recent_assignment_submissions': assignment_submissions.select_related('student', 'assignment')[:5],
            'average_assignment_score': assignment_submissions.filter(status=AssignmentSubmission.Status.GRADED).aggregate(avg=Avg('score'))['avg'],
            'pending_payment_count': payments.filter(status=Payment.Status.PENDING).count(),
            'paid_payment_count': payments.filter(status=Payment.Status.PAID).count(),
            'pending_paid_enrolment_count': enrolments.filter(
                course__is_free=False,
                status=Enrolment.Status.PENDING
            ).count(),
            'active_paid_enrolment_count': enrolments.filter(
                course__is_free=False,
                status__in=[
                    Enrolment.Status.ACTIVE,
                    Enrolment.Status.COMPLETED,
                ],
                payment_status=Enrolment.PaymentStatus.PAID
            ).count(),
            'recent_payments': payments.select_related('student', 'course')[:5],
            'average_review_rating': approved_reviews.aggregate(avg=Avg('rating'))['avg'] or 0,
            'approved_review_count': approved_reviews.count(),
            'low_rating_count': approved_reviews.filter(rating__in=[1, 2]).count(),
            'recent_reviews': approved_reviews.select_related('student', 'course')[:5],
            'certificate_count': certificates.filter(is_valid=True).count(),
            'revoked_certificate_count': certificates.filter(is_valid=False).count(),
            'recent_certificates': certificates.select_related('student', 'course')[:5],
        }
    )


@instructor_required
def instructor_profile_manage(request):

    profile, created = InstructorProfile.objects.get_or_create(
        user=request.user
    )

    if request.method == 'POST':
        form = InstructorProfileForm(
            request.POST,
            request.FILES,
            instance=profile
        )
        if form.is_valid():
            form.save()
            messages.success(
                request,
                'Your instructor profile has been updated.'
            )
            return redirect(
                'learning:instructor_profile_manage'
            )
    else:
        form = InstructorProfileForm(
            instance=profile
        )

    return render(
        request,
        'learning/instructor/profile_form.html',
        {
            'form': form,
            'profile': profile,
        }
    )


@instructor_required
def instructor_course_list(request):

    return render(
        request,
        'learning/instructor/course_list.html',
        {
            'courses': instructor_courses(request.user),
        }
    )


@instructor_required
def instructor_course_create(request):

    if request.method == 'POST':

        form = CourseForm(
            request.POST,
            request.FILES
        )

        if form.is_valid():

            course = form.save(
                commit=False
            )
            course.instructor = request.user
            course.save()

            messages.success(
                request,
                'Course created successfully.'
            )

            return redirect(
                'learning:instructor_courses'
            )

    else:

        form = CourseForm()

    return render(
        request,
        'learning/instructor/course_form.html',
        {
            'form': form,
            'title': 'Create Course',
        }
    )


@instructor_required
def instructor_course_edit(request, pk):

    course = get_object_or_404(
        Course,
        pk=pk
    )

    ensure_course_owner(
        request.user,
        course
    )

    if request.method == 'POST':

        form = CourseForm(
            request.POST,
            request.FILES,
            instance=course
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                'Course updated successfully.'
            )

            return redirect(
                'learning:instructor_courses'
            )

    else:

        form = CourseForm(
            instance=course
        )

    return render(
        request,
        'learning/instructor/course_form.html',
        {
            'form': form,
            'course': course,
            'title': 'Edit Course',
        }
    )


@instructor_required
def instructor_course_modules(request, pk):

    course = get_object_or_404(
        Course.objects.prefetch_related(
            'modules__lessons'
        ),
        pk=pk
    )

    ensure_course_owner(
        request.user,
        course
    )

    module_form = ModuleForm()
    lesson_form = LessonForm(
        course=course
    )

    if request.method == 'POST':

        action = request.POST.get(
            'action'
        )

        if action == 'module':

            module_form = ModuleForm(
                request.POST
            )

            if module_form.is_valid():

                module = module_form.save(
                    commit=False
                )
                module.course = course
                module.save()

                messages.success(
                    request,
                    'Module added successfully.'
                )

                return redirect(
                    'learning:instructor_course_modules',
                    pk=course.pk
                )

        elif action == 'lesson':

            lesson_form = LessonForm(
                request.POST,
                request.FILES,
                course=course
            )

            if lesson_form.is_valid():

                lesson = lesson_form.save(
                    commit=False
                )

                if lesson.module.course_id != course.id:

                    messages.error(
                        request,
                        'Invalid module selected.'
                    )

                else:

                    lesson.save()

                    messages.success(
                        request,
                        'Lesson added successfully.'
                    )

                    return redirect(
                        'learning:instructor_course_modules',
                        pk=course.pk
                    )

    return render(
        request,
        'learning/instructor/modules.html',
        {
            'course': course,
            'module_form': module_form,
            'lesson_form': lesson_form,
        }
    )


@login_required
def announcement_list(request):

    announcements = CourseAnnouncement.objects.select_related(
        'course',
        'author'
    ).filter(
        is_published=True,
        course__enrolments__student=request.user,
        course__enrolments__is_active=True,
        course__enrolments__status__in=[
            Enrolment.Status.ACTIVE,
            Enrolment.Status.COMPLETED,
        ],
    ).distinct()

    return render(
        request,
        'learning/announcements.html',
        {
            'announcements': announcements,
        }
    )


@instructor_required
def instructor_announcement_list(request):

    announcements = CourseAnnouncement.objects.select_related(
        'course',
        'author'
    )

    if not request.user.is_staff:

        announcements = announcements.filter(
            course__instructor=request.user
        )

    return render(
        request,
        'learning/instructor/announcement_list.html',
        {
            'announcements': announcements,
        }
    )


@instructor_required
def instructor_announcement_create(request):

    if request.method == 'POST':

        form = CourseAnnouncementForm(
            request.POST,
            user=request.user
        )

        if form.is_valid():

            announcement = form.save(
                commit=False
            )
            ensure_course_owner(
                request.user,
                announcement.course
            )
            announcement.author = request.user
            announcement.save()

            if announcement.is_published:

                publish_announcement(
                    announcement
                )

            messages.success(
                request,
                'Announcement created successfully.'
            )

            return redirect(
                'learning:instructor_announcements'
            )

    else:

        form = CourseAnnouncementForm(
            user=request.user
        )

    return render(
        request,
        'learning/instructor/announcement_form.html',
        {
            'form': form,
            'title': 'Create Announcement',
        }
    )


@instructor_required
def instructor_announcement_edit(request, pk):

    announcements = CourseAnnouncement.objects.select_related(
        'course'
    )

    if not request.user.is_staff:

        announcements = announcements.filter(
            course__instructor=request.user
        )

    announcement = get_object_or_404(
        announcements,
        pk=pk
    )

    if request.method == 'POST':

        was_published = announcement.is_published
        form = CourseAnnouncementForm(
            request.POST,
            instance=announcement,
            user=request.user
        )

        if form.is_valid():

            announcement = form.save(
                commit=False
            )
            ensure_course_owner(
                request.user,
                announcement.course
            )
            announcement.save()

            if announcement.is_published and not was_published:

                publish_announcement(
                    announcement
                )

            messages.success(
                request,
                'Announcement updated successfully.'
            )

            return redirect(
                'learning:instructor_announcements'
            )

    else:

        form = CourseAnnouncementForm(
            instance=announcement,
            user=request.user
        )

    return render(
        request,
        'learning/instructor/announcement_form.html',
        {
            'form': form,
            'announcement': announcement,
            'title': 'Edit Announcement',
        }
    )


@login_required
def notification_list(request):

    notifications = Notification.objects.filter(
        recipient=request.user
    )

    return render(
        request,
        'learning/notifications.html',
        {
            'notifications': notifications,
        }
    )


@login_required
def notification_read(request, pk):

    notification = get_object_or_404(
        Notification,
        pk=pk,
        recipient=request.user
    )

    notification.mark_read()

    if notification.related_url:

        return redirect(
            notification.related_url
        )

    return redirect(
        'learning:notifications'
    )


@login_required
@require_POST
def notifications_read_all(request):

    Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).update(
        is_read=True,
        read_at=timezone.now()
    )

    messages.success(
        request,
        'All notifications marked as read.'
    )

    return redirect(
        'learning:notifications'
    )


@staff_member_required
def admin_announcement_list(request):

    return render(
        request,
        'learning/admin/announcement_list.html',
        {
            'announcements': CourseAnnouncement.objects.select_related(
                'course',
                'author'
            ),
        }
    )


@login_required
def quiz_detail(request, pk):

    quiz = get_object_or_404(
        Quiz.objects.select_related(
            'lesson',
            'lesson__module',
            'lesson__module__course'
        ).prefetch_related(
            'questions'
        ),
        pk=pk,
        is_published=True
    )

    try:

        enrolment = quiz_is_accessible(
            request.user,
            quiz
        )

    except PermissionDenied:

        messages.warning(
            request,
            'Please enrol in this course to access this quiz.'
        )

        return redirect(
            'learning:course_detail',
            slug=quiz.course.slug
        )

    attempts = QuizAttempt.objects.filter(
        student=request.user,
        quiz=quiz
    )
    in_progress = attempts.filter(
        status=QuizAttempt.Status.IN_PROGRESS
    ).first()

    if in_progress:

        expire_quiz_attempt_if_needed(
            in_progress
        )

    attempts_used = attempts.count()

    return render(
        request,
        'learning/quiz_detail.html',
        {
            'quiz': quiz,
            'enrolment': enrolment,
            'attempts': attempts,
            'attempts_used': attempts_used,
            'attempts_remaining': max(quiz.attempts_allowed - attempts_used, 0),
            'in_progress': attempts.filter(status=QuizAttempt.Status.IN_PROGRESS).first(),
            'best_attempt': attempts.filter(status=QuizAttempt.Status.GRADED).order_by('-percentage').first(),
        }
    )


@login_required
def quiz_start(request, pk):

    quiz = get_object_or_404(
        Quiz,
        pk=pk,
        is_published=True
    )

    try:

        attempt = start_quiz_attempt(
            request.user,
            quiz
        )

    except (PermissionDenied, ValidationError) as exc:

        messages.error(
            request,
            exc.messages[0] if hasattr(exc, 'messages') else str(exc)
        )

        return redirect(
            'learning:quiz_detail',
            pk=quiz.pk
        )

    return redirect(
        'learning:quiz_attempt',
        pk=attempt.pk
    )


@login_required
def quiz_attempt(request, pk):

    attempt = get_object_or_404(
        QuizAttempt.objects.select_related(
            'quiz',
            'quiz__lesson',
            'quiz__lesson__module',
            'quiz__lesson__module__course'
        ),
        pk=pk,
        student=request.user
    )

    attempt = expire_quiz_attempt_if_needed(
        attempt
    )

    if attempt.status != QuizAttempt.Status.IN_PROGRESS:

        return redirect(
            'learning:quiz_result',
            pk=attempt.pk
        )

    form = QuizAttemptForm(
        quiz=attempt.quiz
    )

    return render(
        request,
        'learning/quiz_attempt.html',
        {
            'attempt': attempt,
            'quiz': attempt.quiz,
            'form': form,
        }
    )


@login_required
@require_POST
def quiz_submit(request, pk):

    attempt = get_object_or_404(
        QuizAttempt.objects.select_related(
            'quiz'
        ),
        pk=pk,
        student=request.user
    )

    form = QuizAttemptForm(
        request.POST,
        quiz=attempt.quiz
    )

    if form.is_valid():

        try:

            submit_quiz_attempt(
                attempt,
                form.submitted_answers()
            )

            messages.success(
                request,
                'Quiz submitted successfully.'
            )

            return redirect(
                'learning:quiz_result',
                pk=attempt.pk
            )

        except ValidationError as exc:

            messages.error(
                request,
                exc.messages[0]
            )

    return render(
        request,
        'learning/quiz_attempt.html',
        {
            'attempt': attempt,
            'quiz': attempt.quiz,
            'form': form,
        }
    )


@login_required
def quiz_result(request, pk):

    attempt = get_object_or_404(
        QuizAttempt.objects.select_related(
            'quiz',
            'quiz__lesson',
            'quiz__lesson__module',
            'quiz__lesson__module__course'
        ).prefetch_related(
            'answers__question',
            'answers__question__choices',
            'answers__selected_choices'
        ),
        pk=pk,
        student=request.user
    )

    return render(
        request,
        'learning/quiz_result.html',
        {
            'attempt': attempt,
            'quiz': attempt.quiz,
        }
    )


@login_required
def quiz_attempt_history(request, pk):

    quiz = get_object_or_404(
        Quiz,
        pk=pk,
        is_published=True
    )

    return render(
        request,
        'learning/quiz_attempt_history.html',
        {
            'quiz': quiz,
            'attempts': QuizAttempt.objects.filter(
                student=request.user,
                quiz=quiz
            ),
        }
    )


@instructor_required
def instructor_quiz_list(request):

    quizzes = instructor_quizzes(
        request.user
    ).select_related(
        'lesson',
        'lesson__module',
        'lesson__module__course'
    ).annotate(
        question_count=Count('questions'),
        attempt_count=Count('attempts', distinct=True),
        pending_count=Count(
            'attempts',
            filter=Q(attempts__status=QuizAttempt.Status.AWAITING_MANUAL_GRADING),
            distinct=True
        )
    )

    return render(
        request,
        'learning/instructor/quiz_list.html',
        {
            'quizzes': quizzes,
        }
    )


@instructor_required
def instructor_quiz_create(request):

    if request.method == 'POST':

        form = QuizForm(
            request.POST,
            user=request.user
        )

        if form.is_valid():

            quiz = form.save(
                commit=False
            )
            ensure_course_owner(
                request.user,
                quiz.lesson.module.course
            )
            quiz.save()

            messages.success(
                request,
                'Quiz created successfully.'
            )

            return redirect(
                'learning:instructor_quiz_questions',
                pk=quiz.pk
            )

    else:

        form = QuizForm(
            user=request.user
        )

    return render(
        request,
        'learning/instructor/quiz_form.html',
        {
            'form': form,
            'title': 'Create Quiz',
        }
    )


@instructor_required
def instructor_quiz_edit(request, pk):

    quiz = get_instructor_quiz(
        request.user,
        pk
    )

    if request.method == 'POST':

        form = QuizForm(
            request.POST,
            instance=quiz,
            user=request.user
        )

        if form.is_valid():

            quiz = form.save(
                commit=False
            )
            ensure_course_owner(
                request.user,
                quiz.lesson.module.course
            )
            quiz.save()

            messages.success(
                request,
                'Quiz updated successfully.'
            )

            return redirect(
                'learning:instructor_quizzes'
            )

    else:

        form = QuizForm(
            instance=quiz,
            user=request.user
        )

    return render(
        request,
        'learning/instructor/quiz_form.html',
        {
            'form': form,
            'quiz': quiz,
            'title': 'Edit Quiz',
        }
    )


@instructor_required
def instructor_quiz_questions(request, pk):

    quiz = get_instructor_quiz(
        request.user,
        pk
    )

    question_form = QuestionForm(
        quiz=quiz
    )

    if request.method == 'POST':

        question_form = QuestionForm(
            request.POST,
            quiz=quiz
        )

        if question_form.is_valid():

            question = question_form.save(
                commit=False
            )
            question.quiz = quiz
            question.save()

            messages.success(
                request,
                'Question added successfully.'
            )

            return redirect(
                'learning:instructor_question_choices',
                pk=question.pk
            )

    return render(
        request,
        'learning/instructor/quiz_questions.html',
        {
            'quiz': quiz,
            'questions': quiz.questions.prefetch_related('choices'),
            'question_form': question_form,
        }
    )


@instructor_required
def instructor_question_edit(request, pk):

    question = get_instructor_question(
        request.user,
        pk
    )

    if request.method == 'POST':

        form = QuestionForm(
            request.POST,
            instance=question,
            quiz=question.quiz
        )

        if form.is_valid():

            form.save()
            messages.success(
                request,
                'Question updated successfully.'
            )

            return redirect(
                'learning:instructor_quiz_questions',
                pk=question.quiz.pk
            )

    else:

        form = QuestionForm(
            instance=question,
            quiz=question.quiz
        )

    return render(
        request,
        'learning/instructor/question_form.html',
        {
            'form': form,
            'question': question,
            'title': 'Edit Question',
        }
    )


@instructor_required
@require_POST
def instructor_question_delete(request, pk):

    question = get_instructor_question(
        request.user,
        pk
    )
    quiz_pk = question.quiz_id
    question.delete()
    messages.success(
        request,
        'Question deleted successfully.'
    )

    return redirect(
        'learning:instructor_quiz_questions',
        pk=quiz_pk
    )


@instructor_required
def instructor_question_choices(request, pk):

    question = get_instructor_question(
        request.user,
        pk
    )

    if not question.is_objective:

        messages.info(
            request,
            'Short-answer questions do not use choices.'
        )

        return redirect(
            'learning:instructor_quiz_questions',
            pk=question.quiz.pk
        )

    form = ChoiceForm(
        question=question
    )

    if request.method == 'POST':

        form = ChoiceForm(
            request.POST,
            question=question
        )

        if form.is_valid():

            choice = form.save(
                commit=False
            )
            choice.question = question
            choice.save()

            messages.success(
                request,
                'Choice added successfully.'
            )

            return redirect(
                'learning:instructor_question_choices',
                pk=question.pk
            )

    return render(
        request,
        'learning/instructor/question_choices.html',
        {
            'question': question,
            'choices': question.choices.all(),
            'form': form,
            'choice_warning': choice_rule_warning(question),
        }
    )


@instructor_required
def instructor_quiz_attempt_list(request):

    attempts = instructor_attempts(
        request.user
    ).select_related(
        'student',
        'quiz',
        'quiz__lesson',
        'quiz__lesson__module',
        'quiz__lesson__module__course'
    )

    status = request.GET.get(
        'status',
        ''
    )

    if status:

        attempts = attempts.filter(
            status=status
        )

    return render(
        request,
        'learning/instructor/quiz_attempt_list.html',
        {
            'attempts': attempts,
            'statuses': QuizAttempt.Status.choices,
            'selected_status': status,
        }
    )


@instructor_required
def instructor_quiz_attempt_detail(request, pk):

    attempt = get_instructor_attempt(
        request.user,
        pk
    )

    return render(
        request,
        'learning/instructor/quiz_attempt_detail.html',
        {
            'attempt': attempt,
        }
    )


@instructor_required
def instructor_quiz_attempt_grade(request, pk):

    attempt = get_instructor_attempt(
        request.user,
        pk
    )

    short_answers = attempt.answers.select_related(
        'question'
    ).filter(
        question__question_type=Question.QuestionType.SHORT_ANSWER
    )

    if request.method == 'POST':

        grading_data = {
            'instructor_feedback': request.POST.get(
                'instructor_feedback',
                ''
            )
        }

        for answer in short_answers:

            grading_data[str(answer.pk)] = {
                'marks': request.POST.get(
                    f'marks_{answer.pk}',
                    '0'
                ),
                'feedback': request.POST.get(
                    f'feedback_{answer.pk}',
                    ''
                ),
            }

        try:

            grade_short_answers(
                attempt,
                request.user,
                grading_data
            )

            messages.success(
                request,
                'Quiz attempt graded successfully.'
            )

            return redirect(
                'learning:instructor_quiz_attempt_detail',
                pk=attempt.pk
            )

        except ValidationError as exc:

            messages.error(
                request,
                exc.messages[0]
            )

    return render(
        request,
        'learning/instructor/quiz_grade.html',
        {
            'attempt': attempt,
            'short_answers': short_answers,
            'form': ManualQuizGradingForm(
                initial={
                    'instructor_feedback': attempt.instructor_feedback,
                }
            ),
        }
    )


@login_required
def assignment_detail(request, pk):

    assignment = get_object_or_404(
        Assignment.objects.select_related(
            'lesson',
            'lesson__module',
            'lesson__module__course'
        ),
        pk=pk
    )

    try:

        enrolment = can_access_assignment(
            request.user,
            assignment
        )

    except PermissionDenied as exc:

        messages.warning(
            request,
            str(exc)
        )

        return redirect(
            'learning:course_detail',
            slug=assignment.course.slug
        )

    submissions = AssignmentSubmission.objects.filter(
        assignment=assignment,
        student=request.user
    )
    draft = submissions.filter(
        status=AssignmentSubmission.Status.DRAFT
    ).first()

    return render(
        request,
        'learning/assignment_detail.html',
        {
            'assignment': assignment,
            'enrolment': enrolment,
            'submissions': submissions,
            'draft': draft,
            'latest_submission': submissions.first(),
            'attempts_used': submissions.count(),
            'attempts_remaining': max(assignment.maximum_attempts - submissions.count(), 0),
        }
    )


@login_required
def assignment_draft(request, pk):

    assignment = get_object_or_404(
        Assignment,
        pk=pk,
        is_published=True
    )

    try:

        submission, enrolment = get_or_create_assignment_draft(
            request.user,
            assignment
        )

    except (PermissionDenied, ValidationError) as exc:

        messages.error(
            request,
            exc.messages[0] if hasattr(exc, 'messages') else str(exc)
        )

        return redirect(
            'learning:assignment_detail',
            pk=assignment.pk
        )

    if request.method == 'POST':

        form = AssignmentSubmissionForm(
            request.POST,
            request.FILES,
            instance=submission,
            assignment=assignment
        )

        if form.is_valid():

            try:

                save_assignment_draft(
                    submission,
                    request.user,
                    form.cleaned_data
                )

                messages.success(
                    request,
                    'Draft saved.'
                )

                return redirect(
                    'learning:assignment_detail',
                    pk=assignment.pk
                )

            except ValidationError as exc:

                form.add_error(
                    None,
                    exc.messages[0]
                )

    else:

        form = AssignmentSubmissionForm(
            instance=submission,
            assignment=assignment
        )

    return render(
        request,
        'learning/assignment_draft.html',
        {
            'assignment': assignment,
            'submission': submission,
            'form': form,
        }
    )


@login_required
@require_POST
def assignment_submit(request, pk):

    submission = get_object_or_404(
        AssignmentSubmission,
        assignment_id=pk,
        student=request.user,
        status=AssignmentSubmission.Status.DRAFT
    )

    try:

        submit_assignment(
            submission,
            request.user
        )

        messages.success(
            request,
            'Assignment submitted successfully.'
        )

    except (PermissionDenied, ValidationError) as exc:

        messages.error(
            request,
            exc.messages[0] if hasattr(exc, 'messages') else str(exc)
        )

    return redirect(
        'learning:submission_detail',
        pk=submission.pk
    )


@login_required
def assignment_history(request, pk):

    assignment = get_object_or_404(
        Assignment,
        pk=pk,
        is_published=True
    )

    return render(
        request,
        'learning/assignment_history.html',
        {
            'assignment': assignment,
            'submissions': AssignmentSubmission.objects.filter(
                assignment=assignment,
                student=request.user
            ),
        }
    )


@login_required
def submission_list(request):

    submissions = AssignmentSubmission.objects.select_related(
        'assignment',
        'assignment__lesson',
        'assignment__lesson__module',
        'assignment__lesson__module__course'
    ).filter(
        student=request.user
    )

    return render(
        request,
        'learning/submission_list.html',
        {
            'submissions': submissions,
        }
    )


@login_required
def submission_detail(request, pk):

    submission = get_object_or_404(
        AssignmentSubmission.objects.select_related(
            'assignment',
            'assignment__lesson',
            'assignment__lesson__module',
            'assignment__lesson__module__course',
            'graded_by'
        ),
        pk=pk,
        student=request.user
    )

    return render(
        request,
        'learning/submission_detail.html',
        {
            'submission': submission,
        }
    )


@login_required
def submission_download(request, pk):

    submission = get_object_or_404(
        AssignmentSubmission.objects.select_related(
            'assignment',
            'assignment__lesson',
            'assignment__lesson__module',
            'assignment__lesson__module__course',
            'student'
        ),
        pk=pk
    )

    is_owner = submission.student_id == request.user.id
    is_instructor_owner = submission.assignment.course.instructor_id == request.user.id

    if not (
        is_owner
        or is_instructor_owner
        or request.user.is_staff
    ):

        raise Http404

    if not submission.submission_file:

        raise Http404

    return FileResponse(
        submission.submission_file.open('rb'),
        as_attachment=True,
        filename=submission.original_filename or submission.submission_file.name
    )


@login_required
@require_POST
def submission_revise(request, pk):

    submission = get_object_or_404(
        AssignmentSubmission,
        pk=pk,
        student=request.user
    )

    try:

        draft, enrolment = get_or_create_assignment_draft(
            request.user,
            submission.assignment
        )

        return redirect(
            'learning:assignment_draft',
            pk=submission.assignment.pk
        )

    except (PermissionDenied, ValidationError) as exc:

        messages.error(
            request,
            exc.messages[0] if hasattr(exc, 'messages') else str(exc)
        )

        return redirect(
            'learning:submission_detail',
            pk=submission.pk
        )


@instructor_required
def instructor_assignment_list(request):

    assignments = instructor_assignments(
        request.user
    ).select_related(
        'lesson',
        'lesson__module',
        'lesson__module__course'
    ).annotate(
        submission_count=Count('submissions', distinct=True),
        pending_count=Count(
            'submissions',
            filter=Q(submissions__status__in=[
                AssignmentSubmission.Status.SUBMITTED,
                AssignmentSubmission.Status.UNDER_REVIEW,
            ]),
            distinct=True
        ),
        passed_count=Count(
            'submissions',
            filter=Q(submissions__passed=True),
            distinct=True
        ),
    )

    return render(
        request,
        'learning/instructor/assignment_list.html',
        {
            'assignments': assignments,
        }
    )


@instructor_required
def instructor_assignment_create(request):

    if request.method == 'POST':

        form = AssignmentForm(
            request.POST,
            user=request.user
        )

        if form.is_valid():

            assignment = form.save(
                commit=False
            )
            ensure_course_owner(
                request.user,
                assignment.lesson.module.course
            )
            assignment.save()
            messages.success(
                request,
                'Assignment created successfully.'
            )

            return redirect(
                'learning:instructor_assignment_list'
            )

    else:

        form = AssignmentForm(
            user=request.user
        )

    return render(
        request,
        'learning/instructor/assignment_form.html',
        {
            'form': form,
            'title': 'Create Assignment',
        }
    )


@instructor_required
def instructor_assignment_edit(request, pk):

    assignment = get_instructor_assignment(
        request.user,
        pk
    )

    if request.method == 'POST':

        form = AssignmentForm(
            request.POST,
            instance=assignment,
            user=request.user
        )

        if form.is_valid():

            assignment = form.save(
                commit=False
            )
            ensure_course_owner(
                request.user,
                assignment.lesson.module.course
            )
            assignment.save()
            messages.success(
                request,
                'Assignment updated successfully.'
            )

            return redirect(
                'learning:instructor_assignment_list'
            )

    else:

        form = AssignmentForm(
            instance=assignment,
            user=request.user
        )

    return render(
        request,
        'learning/instructor/assignment_form.html',
        {
            'form': form,
            'assignment': assignment,
            'title': 'Edit Assignment',
        }
    )


@instructor_required
@require_POST
def instructor_assignment_delete(request, pk):

    assignment = get_instructor_assignment(
        request.user,
        pk
    )
    assignment.delete()
    messages.success(
        request,
        'Assignment deleted successfully.'
    )

    return redirect(
        'learning:instructor_assignment_list'
    )


@instructor_required
def instructor_assignment_submissions(request, pk):

    assignment = get_instructor_assignment(
        request.user,
        pk
    )

    return render(
        request,
        'learning/instructor/submission_list.html',
        {
            'assignment': assignment,
            'submissions': assignment.submissions.select_related('student'),
            'statuses': AssignmentSubmission.Status.choices,
        }
    )


@instructor_required
def instructor_submission_list(request):

    submissions = instructor_submissions(
        request.user
    ).select_related(
        'assignment',
        'student',
        'assignment__lesson__module__course'
    )
    status = request.GET.get(
        'status',
        ''
    )

    if status:

        submissions = submissions.filter(
            status=status
        )

    return render(
        request,
        'learning/instructor/submission_list.html',
        {
            'submissions': submissions,
            'statuses': AssignmentSubmission.Status.choices,
            'selected_status': status,
        }
    )


@instructor_required
def instructor_submission_detail(request, pk):

    submission = get_instructor_submission(
        request.user,
        pk
    )

    return render(
        request,
        'learning/instructor/submission_detail.html',
        {
            'submission': submission,
        }
    )


@instructor_required
@require_POST
def instructor_submission_review(request, pk):

    submission = get_instructor_submission(
        request.user,
        pk
    )
    mark_submission_under_review(
        submission,
        request.user
    )
    messages.success(
        request,
        'Submission marked under review.'
    )

    return redirect(
        'learning:instructor_submission_detail',
        pk=submission.pk
    )


@instructor_required
def instructor_submission_grade(request, pk):

    submission = get_instructor_submission(
        request.user,
        pk
    )

    if request.method == 'POST':

        form = AssignmentGradingForm(
            request.POST,
            submission=submission
        )

        if form.is_valid():

            try:

                grade_assignment_submission(
                    submission,
                    request.user,
                    form.cleaned_data['score'],
                    form.cleaned_data['instructor_feedback']
                )
                messages.success(
                    request,
                    'Submission graded successfully.'
                )

                return redirect(
                    'learning:instructor_submission_detail',
                    pk=submission.pk
                )

            except ValidationError as exc:

                form.add_error(
                    None,
                    exc.messages[0]
                )

    else:

        form = AssignmentGradingForm(
            submission=submission,
            initial={
                'score': submission.score,
                'instructor_feedback': submission.instructor_feedback,
            }
        )

    return render(
        request,
        'learning/instructor/submission_grade.html',
        {
            'submission': submission,
            'form': form,
        }
    )


@instructor_required
def instructor_submission_return(request, pk):

    submission = get_instructor_submission(
        request.user,
        pk
    )

    if request.method == 'POST':

        form = AssignmentRevisionForm(
            request.POST
        )

        if form.is_valid():

            try:

                return_assignment_for_revision(
                    submission,
                    request.user,
                    form.cleaned_data['revision_message']
                )
                messages.success(
                    request,
                    'Submission returned for revision.'
                )

                return redirect(
                    'learning:instructor_submission_detail',
                    pk=submission.pk
                )

            except ValidationError as exc:

                form.add_error(
                    None,
                    exc.messages[0]
                )

    else:

        form = AssignmentRevisionForm()

    return render(
        request,
        'learning/instructor/submission_return.html',
        {
            'submission': submission,
            'form': form,
        }
    )


@login_required
@login_required
def payment_list(request):

    payments = Payment.objects.select_related('course', 'enrolment').filter(student=request.user)

    return render(request, 'learning/payments/payment_list.html', {'payments': payments})


@login_required
def payment_course(request, slug):

    course = get_object_or_404(published_courses(), slug=slug)

    if course.is_free:
        messages.info(request, 'This course is free and does not require payment.')
        return redirect('learning:course_detail', slug=course.slug)

    enrolment, created = get_or_create_paid_course_enrolment(request.user, course)
    settings_obj = get_learning_payment_settings()
    pending_payment = enrolment.payments.filter(status=Payment.Status.PENDING).first()
    latest_payment = enrolment.payments.first()

    if request.method == 'POST':
        form = PaymentSubmissionForm(request.POST, request.FILES, settings_obj=settings_obj)
        if form.is_valid():
            try:
                payment = submit_course_payment(request.user, enrolment, form.cleaned_data)
                messages.success(request, 'Payment submitted for verification.')
                return redirect('learning:payment_detail', pk=payment.pk)
            except (PermissionDenied, ValidationError) as exc:
                form.add_error(None, exc.messages[0] if hasattr(exc, 'messages') else str(exc))
    else:
        form = PaymentSubmissionForm(settings_obj=settings_obj)

    return render(
        request,
        'learning/payments/payment_course.html',
        {
            'course': course,
            'enrolment': enrolment,
            'settings_obj': settings_obj,
            'amount': get_course_payable_amount(course),
            'pending_payment': pending_payment,
            'latest_payment': latest_payment,
            'form': form,
        }
    )


@login_required
def payment_detail(request, pk):

    payment = get_object_or_404(
        Payment.objects.select_related('course', 'enrolment', 'verified_by', 'rejected_by', 'refunded_by'),
        pk=pk,
        student=request.user
    )

    return render(request, 'learning/payments/payment_detail.html', {'payment': payment})


@login_required
def payment_proof(request, pk):

    payment = get_object_or_404(Payment.objects.select_related('student'), pk=pk)

    is_owner = payment.student_id == request.user.id
    is_admin = (
        request.user.is_staff
        or request.user.is_superuser
        or request.user.has_perm('learning.verify_learning_payment')
    )

    if not (is_owner or is_admin):
        raise Http404

    if not payment.proof_of_payment:
        raise Http404

    return FileResponse(
        payment.proof_of_payment.open('rb'),
        as_attachment=True,
        filename=payment.original_filename or payment.proof_of_payment.name
    )


@login_required
def payment_resubmit(request, pk):

    payment = get_object_or_404(Payment, pk=pk, student=request.user, status=Payment.Status.REJECTED)
    return redirect('learning:payment_course', slug=payment.course.slug)


@staff_member_required
def admin_payment_list(request):

    payments = Payment.objects.select_related(
        'student',
        'course',
        'course__instructor',
        'verified_by'
    )
    status = request.GET.get('status', '')
    method = request.GET.get('method', '')
    course_id = request.GET.get('course', '')
    instructor_id = request.GET.get('instructor', '')
    q = request.GET.get('q', '').strip()
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    all_payments = payments
    if status:
        payments = payments.filter(status=status)
    if method:
        payments = payments.filter(payment_method=method)
    if course_id:
        payments = payments.filter(course_id=course_id)
    if instructor_id:
        payments = payments.filter(course__instructor_id=instructor_id)
    if q:
        payments = payments.filter(
            Q(transaction_reference__icontains=q)
            | Q(student__username__icontains=q)
            | Q(student__first_name__icontains=q)
            | Q(student__last_name__icontains=q)
            | Q(student__email__icontains=q)
            | Q(course__title__icontains=q)
        )
    if date_from:
        payments = payments.filter(submitted_at__date__gte=date_from)
    if date_to:
        payments = payments.filter(submitted_at__date__lte=date_to)

    totals = {
        'pending': all_payments.filter(status=Payment.Status.PENDING).count(),
        'paid': all_payments.filter(status=Payment.Status.PAID).count(),
        'rejected': all_payments.filter(status=Payment.Status.REJECTED).count(),
        'refunded': all_payments.filter(status=Payment.Status.REFUNDED).count(),
    }

    pending_totals = all_payments.filter(
        status=Payment.Status.PENDING
    ).values(
        'currency'
    ).annotate(
        total=Sum('amount')
    ).order_by('currency')

    confirmed_totals = all_payments.filter(
        status=Payment.Status.PAID
    ).values(
        'currency'
    ).annotate(
        total=Sum('amount')
    ).order_by('currency')

    instructors = User.objects.filter(
        learning_courses__learning_payments__isnull=False
    ).distinct().order_by(
        'first_name',
        'last_name',
        'username'
    )

    return render(
        request,
        'learning/admin/payments/payment_list.html',
        {
            'payments': payments,
            'statuses': Payment.Status.choices,
            'methods': Payment.PaymentMethod.choices,
            'courses': Course.objects.filter(learning_payments__isnull=False).distinct().order_by('title'),
            'instructors': instructors,
            'selected': {
                'status': status,
                'method': method,
                'course': course_id,
                'instructor': instructor_id,
                'q': q,
                'date_from': date_from,
                'date_to': date_to,
            },
            'totals': totals,
            'pending_totals': pending_totals,
            'confirmed_totals': confirmed_totals,
        }
    )


@staff_member_required
def admin_payment_detail(request, pk):

    payment = get_object_or_404(
        Payment.objects.select_related(
            'student',
            'course',
            'enrolment'
        ).prefetch_related(
            'audit_logs__actor'
        ),
        pk=pk
    )
    return render(
        request,
        'learning/admin/payments/payment_detail.html',
        {
            'payment': payment,
            'reason_form': PaymentReasonForm(),
        }
    )


@staff_member_required
@require_POST
def admin_payment_confirm(request, pk):

    payment = get_object_or_404(Payment, pk=pk)
    try:
        confirm_payment(payment, request.user)
        messages.success(request, 'Payment confirmed and enrolment activated.')
    except (PermissionDenied, ValidationError) as exc:
        messages.error(request, exc.messages[0] if hasattr(exc, 'messages') else str(exc))
    return redirect('learning:admin_payment_detail', pk=pk)


@staff_member_required
@require_POST
def admin_payment_reject(request, pk):

    payment = get_object_or_404(Payment, pk=pk)
    form = PaymentReasonForm(request.POST)
    if form.is_valid():
        try:
            reject_payment(payment, request.user, form.cleaned_data['reason'])
            messages.success(request, 'Payment rejected.')
        except (PermissionDenied, ValidationError) as exc:
            messages.error(request, exc.messages[0] if hasattr(exc, 'messages') else str(exc))
    return redirect('learning:admin_payment_detail', pk=pk)


@staff_member_required
@require_POST
def admin_payment_refund(request, pk):

    payment = get_object_or_404(Payment, pk=pk)
    form = PaymentReasonForm(request.POST)
    if form.is_valid():
        try:
            mark_payment_refunded(payment, request.user, form.cleaned_data['reason'])
            messages.success(request, 'Payment marked refunded and enrolment suspended.')
        except (PermissionDenied, ValidationError) as exc:
            messages.error(request, exc.messages[0] if hasattr(exc, 'messages') else str(exc))
    return redirect('learning:admin_payment_detail', pk=pk)


@staff_member_required
def admin_payment_proof(request, pk):

    return payment_proof(request, pk)


@instructor_required
def instructor_payment_list(request):

    payments = instructor_payments(request.user).select_related('student', 'course', 'enrolment')
    return render(request, 'learning/instructor/payment_list.html', {'payments': payments})


@login_required
def course_review_create(request, slug):

    course = get_object_or_404(
        published_courses(),
        slug=slug
    )

    if CourseReview.objects.filter(student=request.user, course=course).exists():
        messages.info(request, 'You have already reviewed this course. You can edit your existing review.')
        review = CourseReview.objects.get(student=request.user, course=course)
        return redirect('learning:course_review_edit', pk=review.pk)

    eligible, enrolment, reason = can_student_review_course(
        request.user,
        course
    )

    if request.method == 'POST':
        form = CourseReviewForm(request.POST)
        if form.is_valid():
            try:
                review = create_course_review(request.user, course, form.cleaned_data)
                messages.success(request, 'Your review was submitted for moderation.')
                return redirect('learning:course_review_detail', pk=review.pk)
            except (PermissionDenied, ValidationError) as exc:
                form.add_error(None, exc.messages[0] if hasattr(exc, 'messages') else str(exc))
    else:
        form = CourseReviewForm()

    return render(
        request,
        'learning/reviews/review_form.html',
        {
            'course': course,
            'enrolment': enrolment,
            'eligible': eligible,
            'eligibility_reason': reason,
            'form': form,
            'mode': 'create',
        }
    )


@login_required
def course_review_detail(request, pk):

    review = get_object_or_404(
        CourseReview.objects.select_related('course', 'student', 'enrolment', 'moderated_by'),
        pk=pk,
        student=request.user
    )

    return render(
        request,
        'learning/reviews/review_detail.html',
        {
            'review': review,
        }
    )


@login_required
def course_review_edit(request, pk):

    review = get_object_or_404(
        CourseReview.objects.select_related('course', 'enrolment'),
        pk=pk,
        student=request.user
    )

    if request.method == 'POST':
        form = CourseReviewForm(request.POST, instance=review)
        if form.is_valid():
            try:
                review = update_course_review(review, request.user, form.cleaned_data)
                messages.success(request, 'Your updated review was submitted for moderation.')
                return redirect('learning:course_review_detail', pk=review.pk)
            except (PermissionDenied, ValidationError) as exc:
                form.add_error(None, exc.messages[0] if hasattr(exc, 'messages') else str(exc))
    else:
        form = CourseReviewForm(instance=review)

    return render(
        request,
        'learning/reviews/review_form.html',
        {
            'course': review.course,
            'enrolment': review.enrolment,
            'eligible': True,
            'eligibility_reason': '',
            'form': form,
            'review': review,
            'mode': 'edit',
        }
    )


@login_required
def student_review_list(request):

    reviews = CourseReview.objects.select_related(
        'course',
        'moderated_by'
    ).filter(
        student=request.user
    )

    return render(
        request,
        'learning/reviews/review_list.html',
        {
            'reviews': reviews,
        }
    )


@instructor_required
def instructor_review_list(request):

    reviews = instructor_reviews(request.user).select_related(
        'student',
        'course'
    )
    status = request.GET.get('status', '')
    rating = request.GET.get('rating', '')
    course_id = request.GET.get('course', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    if status:
        reviews = reviews.filter(status=status)
    if rating:
        reviews = reviews.filter(rating=rating)
    if course_id:
        reviews = reviews.filter(course_id=course_id)
    if date_from:
        reviews = reviews.filter(created_at__date__gte=date_from)
    if date_to:
        reviews = reviews.filter(created_at__date__lte=date_to)

    return render(
        request,
        'learning/instructor/review_list.html',
        {
            'reviews': reviews,
            'statuses': CourseReview.Status.choices,
            'courses': instructor_courses(request.user),
            'selected': {
                'status': status,
                'rating': rating,
                'course': course_id,
                'date_from': date_from,
                'date_to': date_to,
            }
        }
    )


@staff_member_required
def admin_review_list(request):

    reviews = CourseReview.objects.select_related(
        'student',
        'course',
        'course__instructor',
        'moderated_by'
    )
    status = request.GET.get('status', '')
    rating = request.GET.get('rating', '')
    course_id = request.GET.get('course', '')
    instructor_id = request.GET.get('instructor', '')
    q = request.GET.get('q', '').strip()
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    all_reviews = reviews

    if status:
        reviews = reviews.filter(status=status)
    if rating:
        reviews = reviews.filter(rating=rating)
    if course_id:
        reviews = reviews.filter(course_id=course_id)
    if instructor_id:
        reviews = reviews.filter(course__instructor_id=instructor_id)
    if q:
        reviews = reviews.filter(
            Q(course__title__icontains=q)
            | Q(student__username__icontains=q)
            | Q(student__first_name__icontains=q)
            | Q(student__last_name__icontains=q)
            | Q(comment__icontains=q)
        )
    if date_from:
        reviews = reviews.filter(created_at__date__gte=date_from)
    if date_to:
        reviews = reviews.filter(created_at__date__lte=date_to)

    totals = {
        'pending': all_reviews.filter(status=CourseReview.Status.PENDING).count(),
        'approved': all_reviews.filter(status=CourseReview.Status.APPROVED).count(),
        'rejected': all_reviews.filter(status=CourseReview.Status.REJECTED).count(),
        'hidden': all_reviews.filter(status=CourseReview.Status.HIDDEN).count(),
        'average': all_reviews.filter(status=CourseReview.Status.APPROVED).aggregate(avg=Avg('rating'))['avg'] or 0,
    }

    return render(
        request,
        'learning/admin/reviews/review_list.html',
        {
            'reviews': reviews,
            'statuses': CourseReview.Status.choices,
            'courses': Course.objects.filter(reviews__isnull=False).distinct().order_by('title'),
            'instructors': User.objects.filter(learning_courses__reviews__isnull=False).distinct().order_by('first_name', 'last_name', 'username'),
            'selected': {
                'status': status,
                'rating': rating,
                'course': course_id,
                'instructor': instructor_id,
                'q': q,
                'date_from': date_from,
                'date_to': date_to,
            },
            'totals': totals,
        }
    )


@staff_member_required
def admin_review_detail(request, pk):

    review = get_object_or_404(
        CourseReview.objects.select_related('student', 'course', 'course__instructor', 'enrolment', 'moderated_by'),
        pk=pk
    )

    return render(
        request,
        'learning/admin/reviews/review_detail.html',
        {
            'review': review,
            'reason_form': ReviewModerationReasonForm(),
        }
    )


@staff_member_required
@require_POST
def admin_review_approve(request, pk):

    review = get_object_or_404(CourseReview, pk=pk)
    try:
        approve_course_review(review, request.user)
        messages.success(request, 'Review approved.')
    except (PermissionDenied, ValidationError) as exc:
        messages.error(request, exc.messages[0] if hasattr(exc, 'messages') else str(exc))
    return redirect('learning:admin_review_detail', pk=pk)


@staff_member_required
@require_POST
def admin_review_reject(request, pk):

    review = get_object_or_404(CourseReview, pk=pk)
    form = ReviewModerationReasonForm(request.POST)
    if form.is_valid():
        try:
            reject_course_review(review, request.user, form.cleaned_data['reason'])
            messages.success(request, 'Review rejected.')
        except (PermissionDenied, ValidationError) as exc:
            messages.error(request, exc.messages[0] if hasattr(exc, 'messages') else str(exc))
    return redirect('learning:admin_review_detail', pk=pk)


@staff_member_required
@require_POST
def admin_review_hide(request, pk):

    review = get_object_or_404(CourseReview, pk=pk)
    form = ReviewModerationReasonForm(request.POST)
    if form.is_valid():
        try:
            hide_course_review(review, request.user, form.cleaned_data['reason'])
            messages.success(request, 'Review hidden.')
        except (PermissionDenied, ValidationError) as exc:
            messages.error(request, exc.messages[0] if hasattr(exc, 'messages') else str(exc))
    return redirect('learning:admin_review_detail', pk=pk)


@instructor_required
def instructor_certificate_list(request):

    certificates = instructor_certificates(request.user).select_related(
        'student',
        'course',
        'enrolment',
    )

    return render(
        request,
        'learning/instructor/certificate_list.html',
        {
            'certificates': certificates,
        }
    )


@staff_member_required
def admin_certificate_list(request):

    if not user_can_manage_certificates(request.user):
        raise PermissionDenied('You cannot view certificates.')

    certificates = Certificate.objects.select_related(
        'student',
        'course',
        'course__instructor',
        'enrolment',
        'revoked_by',
    )
    status = request.GET.get('status', '')
    course_id = request.GET.get('course', '')
    instructor_id = request.GET.get('instructor', '')
    q = request.GET.get('q', '').strip()

    if status == 'valid':
        certificates = certificates.filter(is_valid=True)
    elif status == 'revoked':
        certificates = certificates.filter(is_valid=False)
    if course_id:
        certificates = certificates.filter(course_id=course_id)
    if instructor_id:
        certificates = certificates.filter(course__instructor_id=instructor_id)
    if q:
        certificates = certificates.filter(
            Q(certificate_number__icontains=q)
            | Q(verification_code__icontains=q)
            | Q(student__username__icontains=q)
            | Q(student__first_name__icontains=q)
            | Q(student__last_name__icontains=q)
            | Q(course__title__icontains=q)
        )

    paginator = Paginator(certificates, 25)
    certificate_page = paginator.get_page(request.GET.get('page'))
    all_certificates = Certificate.objects.all()

    return render(
        request,
        'learning/admin/certificates/certificate_list.html',
        {
            'certificates': certificate_page,
            'courses': Course.objects.filter(certificates__isnull=False).distinct().order_by('title'),
            'instructors': User.objects.filter(learning_courses__certificates__isnull=False).distinct().order_by('first_name', 'last_name', 'username'),
            'selected': {
                'status': status,
                'course': course_id,
                'instructor': instructor_id,
                'q': q,
            },
            'totals': {
                'total': all_certificates.count(),
                'valid': all_certificates.filter(is_valid=True).count(),
                'revoked': all_certificates.filter(is_valid=False).count(),
            }
        }
    )


@staff_member_required
def admin_certificate_detail(request, pk):

    if not user_can_manage_certificates(request.user):
        raise PermissionDenied('You cannot view certificates.')

    certificate = get_object_or_404(
        Certificate.objects.select_related('student', 'course', 'course__instructor', 'enrolment', 'revoked_by', 'restored_by'),
        pk=pk
    )

    return render(
        request,
        'learning/admin/certificates/certificate_detail.html',
        {
            'certificate': certificate,
            'verification_url': certificate_verification_url(certificate, request),
            'revocation_form': CertificateRevocationForm(),
        }
    )


@staff_member_required
def admin_certificate_download(request, pk):

    if not user_can_manage_certificates(request.user):
        raise PermissionDenied('You cannot download certificates.')

    certificate = get_object_or_404(Certificate, pk=pk)
    pdf = generate_certificate_pdf(certificate, request)
    filename = re.sub(r'[^A-Za-z0-9_.-]+', '-', certificate.certificate_number)
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="MITSOL-Certificate-{filename}.pdf"'
    return response


@staff_member_required
@require_POST
def admin_certificate_revoke(request, pk):

    certificate = get_object_or_404(Certificate, pk=pk)
    form = CertificateRevocationForm(request.POST)
    if form.is_valid():
        try:
            revoke_certificate(certificate, request.user, form.cleaned_data['reason'])
            messages.success(request, 'Certificate revoked.')
        except (PermissionDenied, ValidationError) as exc:
            messages.error(request, exc.messages[0] if hasattr(exc, 'messages') else str(exc))
    return redirect('learning:admin_certificate_detail', pk=pk)


@staff_member_required
@require_POST
def admin_certificate_restore(request, pk):

    certificate = get_object_or_404(Certificate, pk=pk)
    try:
        restore_certificate(certificate, request.user)
        messages.success(request, 'Certificate restored.')
    except (PermissionDenied, ValidationError) as exc:
        messages.error(request, exc.messages[0] if hasattr(exc, 'messages') else str(exc))
    return redirect('learning:admin_certificate_detail', pk=pk)


def register_student(request):

    if request.method == 'POST':

        form = StudentRegistrationForm(
            request.POST
        )

        if form.is_valid():

            user = form.save()

            group, created = Group.objects.get_or_create(
                name=STUDENT_GROUP
            )
            user.groups.add(
                group
            )

            login(
                request,
                user
            )

            messages.success(
                request,
                'Your learner account has been created.'
            )

            return redirect(
                'learning:dashboard'
            )

    else:

        form = StudentRegistrationForm()

    return render(
        request,
        'learning/register.html',
        {
            'form': form,
        }
    )


@login_required
def certificate_list(request):

    certificates = Certificate.objects.select_related(
        'course',
        'enrolment',
    ).filter(
        student=request.user
    )

    return render(
        request,
        'learning/certificates/certificate_list.html',
        {
            'certificates': certificates,
        }
    )


@login_required
def certificate_detail(request, pk):

    certificate = get_object_or_404(
        Certificate.objects.select_related('student', 'course', 'enrolment'),
        pk=pk,
        student=request.user
    )

    return render(
        request,
        'learning/certificates/certificate_detail.html',
        {
            'certificate': certificate,
            'verification_url': certificate_verification_url(certificate, request),
        }
    )


@login_required
def certificate_download(request, pk):

    certificate = get_object_or_404(
        Certificate.objects.select_related('student', 'course', 'enrolment'),
        pk=pk,
        student=request.user
    )

    if not certificate.is_valid:
        raise Http404

    pdf = generate_certificate_pdf(certificate, request)
    filename = re.sub(r'[^A-Za-z0-9_.-]+', '-', certificate.certificate_number)
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="MITSOL-Certificate-{filename}.pdf"'
    return response


def certificate_verify(request):

    certificate = None
    searched = False

    if request.method == 'POST':
        form = CertificateVerificationForm(request.POST)
        if form.is_valid():
            searched = True
            certificate = find_certificate(
                form.cleaned_data['certificate_number_or_code']
            )
    else:
        form = CertificateVerificationForm()

    return render(
        request,
        'learning/certificates/certificate_verify.html',
        {
            'form': form,
            'certificate': certificate,
            'searched': searched,
        }
    )


def certificate_verify_code(request, verification_code):

    certificate = find_certificate(
        verification_code
    )

    return render(
        request,
        'learning/certificates/certificate_verify.html',
        {
            'form': CertificateVerificationForm(),
            'certificate': certificate,
            'searched': True,
        }
    )


def published_courses():

    return Course.objects.select_related(
        'category',
        'instructor'
    ).filter(
        is_published=True,
        status=Course.Status.PUBLISHED
    )


def instructor_courses(user):

    courses = Course.objects.select_related(
        'category',
        'instructor'
    )

    if user.is_staff:

        return courses

    return courses.filter(
        instructor=user
    )


def instructor_quizzes(user):

    quizzes = Quiz.objects.all()

    if user.is_staff:

        return quizzes

    return quizzes.filter(
        lesson__module__course__instructor=user
    )


def get_instructor_quiz(user, pk):

    return get_object_or_404(
        instructor_quizzes(user).select_related(
            'lesson',
            'lesson__module',
            'lesson__module__course'
        ),
        pk=pk
    )


def get_instructor_question(user, pk):

    return get_object_or_404(
        Question.objects.select_related(
            'quiz',
            'quiz__lesson',
            'quiz__lesson__module',
            'quiz__lesson__module__course'
        ).filter(
            quiz__in=instructor_quizzes(user)
        ),
        pk=pk
    )


def instructor_attempts(user):

    attempts = QuizAttempt.objects.all()

    if user.is_staff:

        return attempts

    return attempts.filter(
        quiz__lesson__module__course__instructor=user
    )


def get_instructor_attempt(user, pk):

    return get_object_or_404(
        instructor_attempts(user).select_related(
            'student',
            'quiz',
            'quiz__lesson',
            'quiz__lesson__module',
            'quiz__lesson__module__course'
        ).prefetch_related(
            'answers__question',
            'answers__question__choices',
            'answers__selected_choices'
        ),
        pk=pk
    )


def instructor_assignments(user):

    assignments = Assignment.objects.all()

    if user.is_staff:

        return assignments

    return assignments.filter(
        lesson__module__course__instructor=user
    )


def get_instructor_assignment(user, pk):

    return get_object_or_404(
        instructor_assignments(user).select_related(
            'lesson',
            'lesson__module',
            'lesson__module__course'
        ),
        pk=pk
    )


def instructor_submissions(user):

    submissions = AssignmentSubmission.objects.all()

    if user.is_staff:

        return submissions

    return submissions.filter(
        assignment__lesson__module__course__instructor=user
    )


def get_instructor_submission(user, pk):

    return get_object_or_404(
        instructor_submissions(user).select_related(
            'assignment',
            'assignment__lesson',
            'assignment__lesson__module',
            'assignment__lesson__module__course',
            'student',
            'graded_by',
            'returned_by'
        ),
        pk=pk
    )


def instructor_payments(user):

    payments = Payment.objects.all()

    if user.is_staff:
        return payments

    return payments.filter(course__instructor=user)


def instructor_reviews(user):

    reviews = CourseReview.objects.all()

    if user.is_staff:
        return reviews

    return reviews.filter(course__instructor=user)


def instructor_certificates(user):

    certificates = Certificate.objects.all()

    if user.is_staff:
        return certificates

    return certificates.filter(course__instructor=user)


def choice_rule_warning(question):

    choices = question.choices.all()
    correct_count = choices.filter(
        is_correct=True
    ).count()
    total = choices.count()

    if question.question_type == Question.QuestionType.MULTIPLE_CHOICE and correct_count != 1:

        return 'Multiple-choice questions must have exactly one correct choice.'

    if question.question_type == Question.QuestionType.MULTIPLE_SELECT and correct_count < 1:

        return 'Multiple-select questions must have at least one correct choice.'

    if question.question_type == Question.QuestionType.TRUE_FALSE:

        values = {
            choice.choice_text.strip().lower()
            for choice in choices
        }

        if total != 2 or values != {
            'true',
            'false',
        } or correct_count != 1:

            return 'True-or-false questions must have exactly True and False choices with one correct answer.'

    return ''


def filter_courses(request, courses):

    query = request.GET.get('q', '').strip()
    category = request.GET.get('category', '').strip()
    instructor = request.GET.get('instructor', '').strip()
    level = request.GET.get('level', '').strip()
    delivery_mode = request.GET.get('delivery_mode', '').strip()
    pricing = request.GET.get('pricing', '').strip()
    min_price = request.GET.get('min_price', '').strip()
    max_price = request.GET.get('max_price', '').strip()
    sort = request.GET.get('sort', 'newest').strip()

    if query:

        courses = courses.filter(
            Q(title__icontains=query)
            | Q(short_description__icontains=query)
            | Q(full_description__icontains=query)
        )

    if category:

        courses = courses.filter(
            category__slug=category
        )

    if instructor:

        courses = courses.filter(
            instructor_id=instructor
        )

    if level:

        courses = courses.filter(
            level=level
        )

    if delivery_mode:

        courses = courses.filter(
            delivery_mode=delivery_mode
        )

    if pricing == 'free':

        courses = courses.filter(
            is_free=True
        )

    elif pricing == 'paid':

        courses = courses.filter(
            is_free=False
        )

    min_price_value = parse_decimal_filter(
        min_price
    )

    max_price_value = parse_decimal_filter(
        max_price
    )

    if min_price_value is not None:

        courses = courses.filter(
            price__gte=min_price_value
        )

    if max_price_value is not None:

        courses = courses.filter(
            price__lte=max_price_value
        )

    if sort == 'popular':

        courses = courses.annotate(
            enrolment_count=Count('enrolments')
        ).order_by(
            '-enrolment_count',
            '-created_at'
        )

    else:

        courses = courses.order_by(
            '-created_at'
        )

    return courses


def parse_decimal_filter(value):

    if not value:

        return None

    try:

        return Decimal(value)

    except (InvalidOperation, TypeError):

        return None


def catalogue_context(request, page_obj):

    return {
        'page_obj': page_obj,
        'categories': CourseCategory.objects.filter(is_active=True),
        'levels': Course.Level.choices,
        'delivery_modes': Course.DeliveryMode.choices,
        'selected': request.GET,
        'instructors': published_courses().values(
            'instructor__id',
            'instructor__first_name',
            'instructor__last_name',
            'instructor__username',
        ).annotate(
            course_count=Count('id')
        ),
    }
