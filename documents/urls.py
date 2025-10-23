from django.urls import path
from .views import UploadView, DocumentListView, DocumentDetailView, ReportView

urlpatterns = [
    path('upload/', UploadView.as_view(), name='upload'),
    path('documents/', DocumentListView.as_view(), name='document-list'),
    path('documents/<int:id>/', DocumentDetailView.as_view(), name='document-detail'),
    path('report/', ReportView.as_view(), name='report'),
]
