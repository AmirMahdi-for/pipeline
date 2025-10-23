from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator
from django.utils import timezone

class Document(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('done', 'Done'),
        ('failed', 'Failed'),
    ]
    EXTENSION_CHOICES = [
        ('txt', 'TXT'),
        ('png', 'PNG'),
        ('jpeg', 'JPEG'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='documents')
    original_filename = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField()
    extension = models.CharField(max_length=10, choices=EXTENSION_CHOICES)
    original_storage_path = models.CharField(max_length=512)
    thumbnail_storage_path = models.CharField(max_length=512, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    error_message = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['user', 'status'])]

    def __str__(self):
        return f"{self.original_filename} ({self.status})"

class ProcessingLog(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='logs')
    message = models.TextField()
    timestamp = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-timestamp']