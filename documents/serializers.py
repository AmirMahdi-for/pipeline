from rest_framework import serializers
from .models import Document

class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = '__all__'
        read_only_fields = ['user', 'status', 'created_at', 'updated_at', 'original_storage_path', 'thumbnail_storage_path']

class UploadSerializer(serializers.Serializer):
    file = serializers.FileField()

    def validate_file(self, value):
        allowed_extensions = ['txt', 'png', 'jpeg']
        ext = value.name.split('.')[-1].lower()
        if ext not in allowed_extensions:
            raise serializers.ValidationError("Invalid file type. Only TXT, PNG, JPEG allowed.")
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError("File too large.")
        return value


