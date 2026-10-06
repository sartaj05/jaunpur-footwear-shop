from django.conf import settings

from dashboard.models import BackgroundJobRun


def dispatch_background_task(task, *args):
    """Queue in configured deployments and execute inline in local development."""
    if not settings.CELERY_BROKER_URL:
        return task(*args, None)
    job = BackgroundJobRun.objects.create(task_name=task.name or task.__name__)
    task.apply_async(args=(*args, job.pk), task_id=str(job.pk))
    return job
