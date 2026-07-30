from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import CourseForm, LessonForm, ModuleForm, StudentRegistrationForm
from .models import Course, CourseCategory, Enrolment, Lesson, LessonProgress
from .permissions import STUDENT_GROUP, ensure_course_owner, instructor_required, is_instructor
from .services import enrol_student_in_course, mark_lesson_complete, recalculate_enrolment_progress


def learning_home(request):

    featured_courses = published_courses().filter(
        is_featured=True
    )[:3]

    recent_courses = published_courses()[:6]

    categories = CourseCategory.objects.filter(
        is_active=True
    ).annotate(
        course_count=Count(
            'courses',
            filter=Q(courses__is_published=True)
        )
    )[:8]

    instructors = published_courses().values(
        'instructor__id',
        'instructor__first_name',
        'instructor__last_name',
        'instructor__username',
    ).annotate(
        course_count=Count('id')
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

    return render(
        request,
        'learning/course_detail.html',
        {
            'course': course,
            'enrolment': enrolment,
        }
    )


@login_required
def enrol_course(request, slug):

    course = get_object_or_404(
        published_courses(),
        slug=slug
    )

    enrolment, created = enrol_student_in_course(
        request.user,
        course
    )

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

    return render(
        request,
        'learning/dashboard.html',
        {
            'enrolments': enrolments[:6],
            'recent_progress': recent_progress,
            'active_count': enrolments.filter(status=Enrolment.Status.ACTIVE).count(),
            'completed_count': enrolments.filter(status=Enrolment.Status.COMPLETED).count(),
            'pending_count': enrolments.filter(status=Enrolment.Status.PENDING).count(),
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
            ]
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

    return render(
        request,
        'learning/lesson_detail.html',
        {
            'course': course,
            'lesson': lesson,
            'enrolment': enrolment,
            'progress': progress,
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
def certificates_placeholder(request):

    return render(
        request,
        'learning/certificates.html'
    )


def certificate_verify_placeholder(request):

    return render(
        request,
        'learning/certificate_verify.html'
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
