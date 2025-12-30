"""
Core models module containing abstract base classes.
All models in the application should inherit from these base classes.

Usage:
    - AbstractUUID: Provides UUID primary key
    - AbstractMonitor: Provides created_at and updated_at timestamps
    - AbstractActive: Provides is_active soft delete functionality
    - AbstractBaseModel: Combines all three (UUID + Monitor + Active)
"""
import uuid
from django.db import models


class ActiveManager(models.Manager):
    """Manager that returns only active (non-deleted) records."""
    
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)


class AbstractUUID(models.Model):
    """
    Abstract base model that provides UUID primary key.
    Inherit from this when you need UUID as primary key.
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier for this record"
    )

    class Meta:
        abstract = True


class AbstractMonitor(models.Model):
    """
    Abstract base model that provides timestamp fields.
    Inherit from this when you need created_at and updated_at tracking.
    """
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the record was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when the record was last updated"
    )

    class Meta:
        abstract = True
        ordering = ['-created_at']


class AbstractActive(models.Model):
    """
    Abstract base model that provides soft delete functionality.
    Inherit from this when you need is_active flag for soft deletion.
    """
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Soft delete flag. Set to False to deactivate."
    )

    # Managers
    objects = ActiveManager()

    class Meta:
        abstract = True

    def soft_delete(self):
        """Soft delete the record by setting is_active to False."""
        self.is_active = False
        self.save(update_fields=['is_active', 'updated_at'] if hasattr(self, 'updated_at') else ['is_active'])


class AbstractBaseModel(AbstractUUID, AbstractMonitor, AbstractActive):
    """
    Complete abstract base model combining:
    - UUID primary key
    - created_at / updated_at timestamps
    - is_active soft delete flag
    
    Use this as the default base for most models.
    """

    class Meta:
        abstract = True
        ordering = ['-created_at']


