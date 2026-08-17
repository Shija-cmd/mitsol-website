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
        'courses/<slug:slug>/review/',
        views.course_review_create,
        name='course_review_create'
    ),
    path(
        'categories/<slug:slug>/',
        views.category_courses,
        name='category'
    ),
    path(
        'instructors/',
        views.instructor_list,
        name='instructor_list'
    ),
    path(
        'instructors/<str:username>/',
        views.instructor_profile_detail,
        name='instructor_profile'
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
        'quiz/<int:pk>/',
        views.quiz_detail,
        name='quiz_detail'
    ),
    path(
        'quiz/<int:pk>/start/',
        views.quiz_start,
        name='quiz_start'
    ),
    path(
        'quiz/attempt/<int:pk>/',
        views.quiz_attempt,
        name='quiz_attempt'
    ),
    path(
        'quiz/attempt/<int:pk>/submit/',
        views.quiz_submit,
        name='quiz_submit'
    ),
    path(
        'quiz/attempt/<int:pk>/result/',
        views.quiz_result,
        name='quiz_result'
    ),
    path(
        'quiz/<int:pk>/attempts/',
        views.quiz_attempt_history,
        name='quiz_attempt_history'
    ),
    path(
        'assignment/<int:pk>/',
        views.assignment_detail,
        name='assignment_detail'
    ),
    path(
        'assignment/<int:pk>/draft/',
        views.assignment_draft,
        name='assignment_draft'
    ),
    path(
        'assignment/<int:pk>/history/',
        views.assignment_history,
        name='assignment_history'
    ),
    path(
        'assignment/<int:pk>/submit/',
        views.assignment_submit,
        name='assignment_submit'
    ),
    path(
        'submissions/',
        views.submission_list,
        name='submission_list'
    ),
    path(
        'submissions/<int:pk>/',
        views.submission_detail,
        name='submission_detail'
    ),
    path(
        'submissions/<int:pk>/download/',
        views.submission_download,
        name='submission_download'
    ),
    path(
        'submissions/<int:pk>/revise/',
        views.submission_revise,
        name='submission_revise'
    ),
    path('reviews/', views.student_review_list, name='student_review_list'),
    path('reviews/<int:pk>/', views.course_review_detail, name='course_review_detail'),
    path('reviews/<int:pk>/edit/', views.course_review_edit, name='course_review_edit'),
    path('payments/', views.payment_list, name='payment_list'),
    path('payments/course/<slug:slug>/', views.payment_course, name='payment_course'),
    path('payments/<int:pk>/', views.payment_detail, name='payment_detail'),
    path('payments/<int:pk>/proof/', views.payment_proof, name='payment_proof'),
    path('payments/<int:pk>/resubmit/', views.payment_resubmit, name='payment_resubmit'),
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
        'instructor/profile/',
        views.instructor_profile_manage,
        name='instructor_profile_manage'
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
        'instructor/lessons/<int:pk>/edit/',
        views.instructor_lesson_edit,
        name='instructor_lesson_edit'
    ),
    path(
        'register/',
        views.register_student,
        name='register'
    ),
    path(
        'certificates/',
        views.certificate_list,
        name='certificate_list'
    ),
    path(
        'certificates/<int:pk>/',
        views.certificate_detail,
        name='certificate_detail'
    ),
    path(
        'certificates/<int:pk>/download/',
        views.certificate_download,
        name='certificate_download'
    ),
    path(
        'certificates/verify/',
        views.certificate_verify,
        name='certificate_verify'
    ),
    path(
        'certificates/verify/<str:verification_code>/',
        views.certificate_verify_code,
        name='certificate_verify_code'
    ),
    path(
        'announcements/',
        views.announcement_list,
        name='announcements'
    ),
    path(
        'instructor/announcements/',
        views.instructor_announcement_list,
        name='instructor_announcements'
    ),
    path(
        'instructor/assignments/',
        views.instructor_assignment_list,
        name='instructor_assignment_list'
    ),
    path(
        'instructor/assignments/create/',
        views.instructor_assignment_create,
        name='instructor_assignment_create'
    ),
    path(
        'instructor/assignments/<int:pk>/edit/',
        views.instructor_assignment_edit,
        name='instructor_assignment_edit'
    ),
    path(
        'instructor/assignments/<int:pk>/delete/',
        views.instructor_assignment_delete,
        name='instructor_assignment_delete'
    ),
    path(
        'instructor/assignments/<int:pk>/submissions/',
        views.instructor_assignment_submissions,
        name='instructor_assignment_submissions'
    ),
    path(
        'instructor/submissions/',
        views.instructor_submission_list,
        name='instructor_submission_list'
    ),
    path(
        'instructor/submissions/<int:pk>/',
        views.instructor_submission_detail,
        name='instructor_submission_detail'
    ),
    path(
        'instructor/submissions/<int:pk>/review/',
        views.instructor_submission_review,
        name='instructor_submission_review'
    ),
    path(
        'instructor/submissions/<int:pk>/grade/',
        views.instructor_submission_grade,
        name='instructor_submission_grade'
    ),
    path(
        'instructor/submissions/<int:pk>/return/',
        views.instructor_submission_return,
        name='instructor_submission_return'
    ),
    path('instructor/payments/', views.instructor_payment_list, name='instructor_payment_list'),
    path('instructor/reviews/', views.instructor_review_list, name='instructor_review_list'),
    path('instructor/certificates/', views.instructor_certificate_list, name='instructor_certificate_list'),
    path(
        'instructor/quizzes/',
        views.instructor_quiz_list,
        name='instructor_quizzes'
    ),
    path(
        'instructor/quizzes/create/',
        views.instructor_quiz_create,
        name='instructor_quiz_create'
    ),
    path(
        'instructor/quizzes/<int:pk>/edit/',
        views.instructor_quiz_edit,
        name='instructor_quiz_edit'
    ),
    path(
        'instructor/quizzes/<int:pk>/questions/',
        views.instructor_quiz_questions,
        name='instructor_quiz_questions'
    ),
    path(
        'instructor/questions/<int:pk>/edit/',
        views.instructor_question_edit,
        name='instructor_question_edit'
    ),
    path(
        'instructor/questions/<int:pk>/delete/',
        views.instructor_question_delete,
        name='instructor_question_delete'
    ),
    path(
        'instructor/questions/<int:pk>/choices/',
        views.instructor_question_choices,
        name='instructor_question_choices'
    ),
    path(
        'instructor/quiz-attempts/',
        views.instructor_quiz_attempt_list,
        name='instructor_quiz_attempts'
    ),
    path(
        'instructor/quiz-attempts/<int:pk>/',
        views.instructor_quiz_attempt_detail,
        name='instructor_quiz_attempt_detail'
    ),
    path(
        'instructor/quiz-attempts/<int:pk>/grade/',
        views.instructor_quiz_attempt_grade,
        name='instructor_quiz_attempt_grade'
    ),
    path(
        'instructor/announcements/create/',
        views.instructor_announcement_create,
        name='instructor_announcement_create'
    ),
    path(
        'instructor/announcements/<int:pk>/edit/',
        views.instructor_announcement_edit,
        name='instructor_announcement_edit'
    ),
    path(
        'admin/announcements/',
        views.admin_announcement_list,
        name='admin_announcements'
    ),
    path('admin/payments/', views.admin_payment_list, name='admin_payment_list'),
    path('admin/payments/<int:pk>/', views.admin_payment_detail, name='admin_payment_detail'),
    path('admin/payments/<int:pk>/confirm/', views.admin_payment_confirm, name='admin_payment_confirm'),
    path('admin/payments/<int:pk>/reject/', views.admin_payment_reject, name='admin_payment_reject'),
    path('admin/payments/<int:pk>/refund/', views.admin_payment_refund, name='admin_payment_refund'),
    path('admin/payments/<int:pk>/proof/', views.admin_payment_proof, name='admin_payment_proof'),
    path('admin/reviews/', views.admin_review_list, name='admin_review_list'),
    path('admin/reviews/<int:pk>/', views.admin_review_detail, name='admin_review_detail'),
    path('admin/reviews/<int:pk>/approve/', views.admin_review_approve, name='admin_review_approve'),
    path('admin/reviews/<int:pk>/reject/', views.admin_review_reject, name='admin_review_reject'),
    path('admin/reviews/<int:pk>/hide/', views.admin_review_hide, name='admin_review_hide'),
    path('admin/certificates/', views.admin_certificate_list, name='admin_certificate_list'),
    path('admin/certificates/<int:pk>/', views.admin_certificate_detail, name='admin_certificate_detail'),
    path('admin/certificates/<int:pk>/approve/', views.admin_certificate_approve, name='admin_certificate_approve'),
    path('admin/certificates/<int:pk>/download/', views.admin_certificate_download, name='admin_certificate_download'),
    path('admin/certificates/<int:pk>/revoke/', views.admin_certificate_revoke, name='admin_certificate_revoke'),
    path('admin/certificates/<int:pk>/restore/', views.admin_certificate_restore, name='admin_certificate_restore'),
    path(
        'notifications/',
        views.notification_list,
        name='notifications'
    ),
    path(
        'notifications/<int:pk>/read/',
        views.notification_read,
        name='notification_read'
    ),
    path(
        'notifications/read-all/',
        views.notifications_read_all,
        name='notifications_read_all'
    ),
]
