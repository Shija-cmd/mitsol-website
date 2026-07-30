from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import PermissionDenied


INSTRUCTOR_GROUP = 'Instructor'
STUDENT_GROUP = 'Student'


def is_instructor(user):

    return (
        user.is_authenticated
        and (
            user.is_staff
            or user.groups.filter(name=INSTRUCTOR_GROUP).exists()
            or hasattr(user, 'instructor_profile')
        )
    )


def instructor_required(view_func):

    decorated_view = login_required(
        user_passes_test(
            is_instructor
        )(
            view_func
        )
    )

    return decorated_view


def ensure_course_owner(user, course):

    if not user.is_staff and course.instructor_id != user.id:

        raise PermissionDenied(
            'You can only manage courses that you own.'
        )

    return True
