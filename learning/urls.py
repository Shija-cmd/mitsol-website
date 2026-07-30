from django.urls import path

from . import views


app_name = 'learning'


urlpatterns = [
    path(
        '',
        views.learning_home,
        name='home'
    ),
    path(
        'courses/',
        views.course_catalogue,
        name='course_list'
    ),
    path(
        'courses/<slug:slug>/',
        views.course_detail,
        name='course_detail'
    ),
    path(
        'categories/<slug:slug>/',
        views.category_courses,
        name='category'
    ),
    path(
        'enrol/<slug:slug>/',
        views.enrol_course,
        name='enrol'
    ),
    path(
        'my-courses/',
        views.my_courses,
        name='my_courses'
    ),
    path(
        'course/<slug:course_slug>/lesson/<slug:lesson_slug>/',
        views.lesson_detail,
        name='lesson_detail'
    ),
    path(
        'dashboard/',
        views.student_dashboard,
        name='dashboard'
    ),
    path(
        'instructor/',
        views.instructor_dashboard,
        name='instructor_dashboard'
    ),
    path(
        'instructor/courses/',
        views.instructor_course_list,
        name='instructor_courses'
    ),
    path(
        'instructor/courses/create/',
        views.instructor_course_create,
        name='instructor_course_create'
    ),
    path(
        'instructor/courses/<int:pk>/edit/',
        views.instructor_course_edit,
        name='instructor_course_edit'
    ),
    path(
        'instructor/courses/<int:pk>/modules/',
        views.instructor_course_modules,
        name='instructor_course_modules'
    ),
    path(
        'register/',
        views.register_student,
        name='register'
    ),
    path(
        'certificates/',
        views.certificates_placeholder,
        name='certificates'
    ),
    path(
        'certificates/verify/',
        views.certificate_verify_placeholder,
        name='certificate_verify'
    ),
]
