from django.db import models


class AsyncResults(models.Model):
    """
  Temporary records of async task_id, the results as a JSON blob
  with a status code,
  and the user who requested the task.
  """
    # the id of the celery task that generated the result
    task_id = models.CharField(
        blank=False,
        max_length=255,
        null=False,
        verbose_name="task id",
        db_index=True)  # the tasks's result - represented as a JSON blob
    result = models.TextField(
        blank=False,
        verbose_name="task result")

    created_on = models.DateTimeField(
        db_index=True,
        editable=False,
        verbose_name="created_on",
        auto_now_add=True)
