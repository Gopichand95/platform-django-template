from django.db import models


class BaseModel(models.Model):
    """
    Base model class that all models in the application should inherit from.
    """

    id = models.BigAutoField(primary_key=True, editable=False)
    created_at = models.DateTimeField(
        auto_now_add=True,
        editable=False,
        db_column="_created_at",
    )
    last_modified_at = models.DateTimeField(
        auto_now=True,
        db_column="_last_modified_at",
    )

    class Meta:
        abstract = True
        ordering = ["-created_at"]
