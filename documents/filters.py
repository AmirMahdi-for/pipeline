import django_filters
from .models import Document

class DocumentFilter(django_filters.FilterSet):
    extension = django_filters.ChoiceFilter(choices=Document.EXTENSION_CHOICES)
    date_from = django_filters.DateFilter(field_name='created_at', lookup_expr='gte')
    date_to = django_filters.DateFilter(field_name='created_at', lookup_expr='lte')

    class Meta:
        model = Document
        fields = ['extension', 'date_from', 'date_to']