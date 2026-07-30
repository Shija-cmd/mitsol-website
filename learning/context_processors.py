from .permissions import is_instructor


def learning_context(request):

    unread_count = 0
    user_is_instructor = False
    learning_shell_active = (
        request.path.startswith('/learn/')
        or request.path == '/accounts/login/'
    )

    if request.user.is_authenticated:

        unread_count = request.user.learning_notifications.filter(
            is_read=False
        ).count()
        user_is_instructor = is_instructor(
            request.user
        )

    return {
        'learning_section_enabled': True,
        'learning_shell_active': learning_shell_active,
        'learning_unread_notifications': unread_count,
        'learning_user_is_instructor': user_is_instructor,
    }
