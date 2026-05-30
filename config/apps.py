from background_task.apps import BackgroundTasksAppConfig as BaseBackgroundTasksAppConfig


class BackgroundTasksAppConfig(BaseBackgroundTasksAppConfig):
    default_auto_field = "django.db.models.AutoField"
