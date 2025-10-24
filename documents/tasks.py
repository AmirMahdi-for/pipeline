from celery import shared_task
from .models import Document, ProcessingLog
from .utils import generate_thumbnail, get_minio_client
from botocore.exceptions import ClientError
import os
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True)
def process_file_task(self, document_id):

    try:
        logger.info(f" Starting processing for document {document_id}")

        document = Document.objects.get(id=document_id)
        document.status = 'processing'
        document.save()
        logger.info(f" Document {document_id} status set to processing")

        client = get_minio_client()
        bucket = os.environ.get('MINIO_BUCKET')

        try:
            logger.info(f" Downloading {document.original_filename} from MinIO")
            response = client.get_object(Bucket=bucket, Key=document.original_filename)
            file_content = response['Body'].read()
            logger.info(f" Downloaded {len(file_content)} bytes from MinIO")

        except ClientError as e:
            error_msg = f"Download failed: {str(e)}"
            logger.error(f" {error_msg}")
            document.status = 'failed'
            document.error_message = error_msg
            document.save()

            ProcessingLog.objects.create(
                document=document,
                message=error_msg
            )
            return f"Failed: {error_msg}"

        if document.extension.lower() in ['png', 'jpeg', 'jpg']:
            logger.info(f" Generating thumbnail for {document.original_filename}")

            thumbnail_content = generate_thumbnail(file_content, document.extension)

            if thumbnail_content:
                try:
                    thumb_filename = f"thumb_{document.original_filename}"
                    logger.info(f" Uploading thumbnail: {thumb_filename}")

                    client.put_object(
                        Bucket=bucket,
                        Key=thumb_filename,
                        Body=thumbnail_content,
                        ContentType=f'image/{document.extension}',
                        ContentLength=len(thumbnail_content)
                    )

                    document.thumbnail_storage_path = f"{os.environ.get('MINIO_ENDPOINT')}/{bucket}/{thumb_filename}"
                    logger.info(f" Thumbnail uploaded: {document.thumbnail_storage_path}")

                except Exception as e:
                    error_msg = f"Thumbnail upload failed: {str(e)}"
                    logger.error(f" {error_msg}")
                    document.status = 'failed'
                    document.error_message = error_msg
                    document.save()

                    ProcessingLog.objects.create(
                        document=document,
                        message=error_msg
                    )
                    return f"Failed: {error_msg}"
            else:
                logger.warning(f" Thumbnail generation returned None for {document.original_filename}")

        document.status = 'done'
        document.save()
        logger.info(f" Document {document_id} processing completed successfully")

        ProcessingLog.objects.create(
            document=document,
            message="Processing completed successfully"
        )

        return "Success"

    except Document.DoesNotExist:
        error_msg = f"Document {document_id} not found"
        logger.error(f" {error_msg}")
        return f"Failed: {error_msg}"

    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(f" {error_msg}")

        if 'document' in locals():
            document.status = 'failed'
            document.error_message = error_msg
            document.save()

            ProcessingLog.objects.create(
                document=document,
                message=error_msg
            )

        return f"Failed: {error_msg}"