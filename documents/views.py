from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from .serializers import UploadSerializer, DocumentSerializer
from .models import Document
from .tasks import process_file_task
from .utils import get_minio_client
import os
from datetime import timedelta
from django.utils.timezone import now
from django.db.models.functions import TruncDate
from django.db.models import Count
from typing import Dict, Any, List

class UploadView(APIView):

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        methods=['POST'],
        description="Upload a TXT, PNG, or JPEG file for processing.",
        request=UploadSerializer,
        responses={201: DocumentSerializer, 400: {"error": "Validation errors"}, 500: {"error": "Server error"}},
    )
    def post(self, request) -> Response:

        serializer = UploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        file = serializer.validated_data['file']
        document = self._handle_file_upload(request.user, file)
        if document:
            process_file_task.delay(document.id)
            return Response(DocumentSerializer(document).data, status=status.HTTP_201_CREATED)
        return Response({"error": "Failed to process upload"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _handle_file_upload(self, user, file) -> Document:

        filename = file.name
        ext = filename.split('.')[-1].lower()
        bucket = os.environ['MINIO_BUCKET']

        try:
            storage_path = self._upload_to_minio(file, bucket, filename)
            return Document.objects.create(
                user=user,
                original_filename=filename,
                file_size=file.size,
                extension=ext,
                original_storage_path=storage_path,
            )
        except Exception as e:
            raise Exception(f"Upload failed: {str(e)}")

    def _upload_to_minio(self, file, bucket: str, filename: str) -> str:

        client = get_minio_client()
        file.seek(0)
        client.put_object(
            Bucket=bucket,
            Key=filename,
            Body=file,
            ContentLength=file.size,
            ContentType=file.content_type
        )
        return f"{os.environ['MINIO_ENDPOINT']}/{bucket}/{filename}"


class DocumentListView(generics.ListAPIView):

    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['extension', 'created_at']

    @extend_schema(description="List documents with optional filters (extension, created_at)")
    def get_queryset(self):
        return Document.objects.filter(user=self.request.user).order_by('-created_at')


class DocumentDetailView(generics.RetrieveAPIView):

    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    @extend_schema(description="Get details of a specific document")
    def get_queryset(self):
        return Document.objects.filter(user=self.request.user)


class ReportView(APIView):

    permission_classes = [IsAuthenticated]

    @extend_schema(
        description="Get daily upload counts for the last 14 days",
        responses={200: List[Dict[str, Any]]}
    )
    def get(self, request) -> Response:

        end_date = now().date()
        start_date = end_date - timedelta(days=13)
        queryset = (Document.objects
                   .filter(user=request.user,
                           created_at__date__gte=start_date,
                           created_at__date__lte=end_date)
                   .annotate(date=TruncDate('created_at'))
                   .values('date')
                   .annotate(count=Count('id'))
                   .order_by('date'))

        results = {date: 0 for date in [start_date + timedelta(days=x) for x in range(14)]}
        for item in queryset:
            results[item['date']] = item['count']

        report = [{"date": date.strftime('%Y-%m-%d'), "count": count} for date, count in results.items()]
        return Response(report)