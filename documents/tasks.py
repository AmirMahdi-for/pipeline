from celery import shared_task
from .models import Document, ProcessingLog
from .utils import generate_thumbnail, get_minio_client
from botocore.exceptions import ClientError
import os
import logging
from django.db import transaction

logger = logging.getLogger(__name__)

@shared_task(bind=True)
def process_file_task(self, document_id):

    try:
        logger.info(f"Starting processing for document {document_id}")

        try:
            with transaction.atomic():
                document = Document.objects.select_for_update().get(id=document_id)
                document.status = 'processing'
                document.error_message = ''
                document.save(update_fields=['status', 'error_message'])
                logger.info(f"Document {document_id} status set to processing (locked and updated)")
        except Document.DoesNotExist:
            error_msg = f"Document {document_id} not found"
            logger.error(error_msg)
            return f"Failed: {error_msg}"

        client = get_minio_client()
        bucket = os.environ.get('MINIO_BUCKET')

        try:
            logger.info(f"Downloading {document.original_filename} from MinIO")
            response = client.get_object(Bucket=bucket, Key=document.original_filename)
            file_content = response['Body'].read()
            logger.info(f"Downloaded {len(file_content)} bytes from MinIO")
        except ClientError as e:
            error_msg = f"Download failed: {str(e)}"
            logger.error(error_msg)

            with transaction.atomic():
                Document.objects.filter(id=document.id).update(status='failed', error_message=error_msg)
                ProcessingLog.objects.create(document=document, message=error_msg)
            return f"Failed: {error_msg}"

        if document.extension.lower() in ['png', 'jpeg', 'jpg', 'jpg']:
            logger.info(f"Generating thumbnail for {document.original_filename}")
            try:
                thumbnail_content = generate_thumbnail(file_content, document.extension)
            except Exception as e:
                thumbnail_content = None
                logger.exception(f"Thumbnail generation exception for {document.original_filename}: {e}")

            if thumbnail_content:
                try:
                    thumb_filename = f"thumb_{document.original_filename}"
                    logger.info(f"Uploading thumbnail: {thumb_filename}")

                    client.put_object(
                        Bucket=bucket,
                        Key=thumb_filename,
                        Body=thumbnail_content,
                        ContentType=f"image/{document.extension if document.extension != 'jpg' else 'jpeg'}",
                        ContentLength=len(thumbnail_content)
                    )

                    thumb_path = f"{os.environ.get('MINIO_ENDPOINT')}/{bucket}/{thumb_filename}"
                    logger.info(f"Thumbnail uploaded: {thumb_path}")

                    with transaction.atomic():
                        Document.objects.filter(id=document.id).update(thumbnail_storage_path=thumb_path)
                        ProcessingLog.objects.create(document=document, message="Thumbnail uploaded")
                except Exception as e:
                    error_msg = f"Thumbnail upload failed: {str(e)}"
                    logger.error(error_msg)
                    with transaction.atomic():
                        Document.objects.filter(id=document.id).update(status='failed', error_message=error_msg)
                        ProcessingLog.objects.create(document=document, message=error_msg)
                    return f"Failed: {error_msg}"
            else:
                logger.warning(f"Thumbnail generation returned None for {document.original_filename}")

                with transaction.atomic():
                    ProcessingLog.objects.create(document=document, message="Thumbnail generation returned None")

        with transaction.atomic():
            Document.objects.filter(id=document.id).update(status='done')
            ProcessingLog.objects.create(document=document, message="Processing completed successfully")

        logger.info(f"Document {document_id} processing completed successfully")
        return "Success"

    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.exception(error_msg)

        try:
            with transaction.atomic():
                if 'document' in locals():
                    Document.objects.filter(id=document.id).update(status='failed', error_message=error_msg)
                    ProcessingLog.objects.create(document=document, message=error_msg)
        except Exception as e2:
            logger.exception(f"Failed to update document failure state: {e2}")

        return f"Failed: {error_msg}"
