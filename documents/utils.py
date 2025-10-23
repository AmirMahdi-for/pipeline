import boto3
from botocore.client import Config
from PIL import Image
from io import BytesIO
import os
import logging

logger = logging.getLogger(__name__)

def get_minio_client():
    return boto3.client(
        's3',
        endpoint_url=os.environ['MINIO_ENDPOINT'],
        aws_access_key_id=os.environ['MINIO_ACCESS_KEY'],
        aws_secret_access_key=os.environ['MINIO_SECRET_KEY'],
        config=Config(signature_version='s3v4')
    )

def generate_thumbnail(file_content, extension):

    try:
        logger.info(f"Generating thumbnail for extension: {extension}")

        if extension.lower() == 'jpg':
            extension = 'jpeg'

        if extension.lower() not in ['png', 'jpeg']:
            logger.info(f"Thumbnail not needed for extension: {extension}")
            return None

        img = Image.open(BytesIO(file_content))
        logger.info(f"Original image size: {img.size}, mode: {img.mode}")

        if img.mode in ('RGBA', 'LA', 'P'):

            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        width, height = img.size
        logger.info(f"Calculating thumbnail size from {width}x{height}")

        if width > height:
            new_width = 256
            new_height = int(height * 256 / width)
        else:
            new_height = 256
            new_width = int(width * 256 / height)

        logger.info(f"Thumbnail size: {new_width}x{new_height}")

        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        buffer = BytesIO()
        img.save(buffer, format=extension.upper(), quality=85)
        buffer.seek(0)

        thumbnail_data = buffer.getvalue()
        logger.info(f"Thumbnail generated, size: {len(thumbnail_data)} bytes")

        return thumbnail_data

    except Exception as e:
        logger.error(f"Error in thumbnail generation: {str(e)}")
        return None