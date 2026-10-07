from celery import shared_task


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={'max_retries': 3})
def check_production_operations_task(self):
    from .operations import run_production_operations_checks

    return run_production_operations_checks()
