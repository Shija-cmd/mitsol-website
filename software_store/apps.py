from django.apps import AppConfig


class SoftwareStoreConfig(AppConfig):

    default_auto_field = 'django.db.models.BigAutoField'

    name = 'software_store'

    verbose_name = 'Software Store'

    def ready(self):

        import software_store.signals  # noqa: F401
