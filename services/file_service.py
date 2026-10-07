import os
import uuid
from werkzeug.utils import secure_filename
from config import Config

class FileService:
    ALLOWED_EXTENSIONS = Config.ALLOWED_EXTENSIONS
    MAX_FILE_SIZE = Config.MAX_CONTENT_LENGTH
    MATERIALS_FOLDER = Config.MATERIALS_FOLDER
    AVATARS_FOLDER = Config.AVATARS_FOLDER
    
    @classmethod
    def allowed_file(cls, filename):
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in cls.ALLOWED_EXTENSIONS
    
    @classmethod
    def validate_file(cls, file):
        if not file or not file.filename:
            return False, 'No file selected'
        
        if not cls.allowed_file(file.filename):
            return False, f'File type not allowed. Allowed types: {", ".join(cls.ALLOWED_EXTENSIONS)}'
        
        file.seek(0, os.SEEK_END)
        size = file.tell()
        file.seek(0)
        
        if size > cls.MAX_FILE_SIZE:
            return False, f'File too large. Maximum size: {cls.MAX_FILE_SIZE // (1024*1024)}MB'
        
        if size == 0:
            return False, 'File is empty'
        
        return True, None
    
    @classmethod
    def save_material(cls, file, user_id):
        is_valid, error = cls.validate_file(file)
        if not is_valid:
            return None, error
        
        original_filename = secure_filename(file.filename)
        extension = original_filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4().hex}.{extension}"
        
        user_folder = os.path.join(cls.MATERIALS_FOLDER, str(user_id))
        os.makedirs(user_folder, exist_ok=True)
        
        file_path = os.path.join(user_folder, unique_filename)
        file.save(file_path)
        
        file_size = os.path.getsize(file_path)
        mime_type = cls.get_mime_type(extension)
        
        return {
            'filename': unique_filename,
            'original_filename': original_filename,
            'file_path': file_path,
            'file_size': file_size,
            'mime_type': mime_type,
            'extension': extension
        }, None
    
    @classmethod
    def save_avatar(cls, file, user_id):
        is_valid, error = cls.validate_file(file)
        if not is_valid:
            return None, error
        
        extension = file.filename.rsplit('.', 1)[1].lower()
        unique_filename = f"avatar_{user_id}_{uuid.uuid4().hex}.{extension}"
        
        os.makedirs(cls.AVATARS_FOLDER, exist_ok=True)
        file_path = os.path.join(cls.AVATARS_FOLDER, unique_filename)
        file.save(file_path)
        
        return unique_filename, None
    
    @classmethod
    def delete_material(cls, file_path):
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
        except Exception:
            pass
        return False
    
    @classmethod
    def get_mime_type(cls, extension):
        mime_types = {
            'pdf': 'application/pdf',
            'doc': 'application/msword',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'txt': 'text/plain',
            'md': 'text/markdown',
            'ppt': 'application/vnd.ms-powerpoint',
            'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            'xls': 'application/vnd.ms-excel',
            'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'png': 'image/png',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'gif': 'image/gif',
        }
        return mime_types.get(extension.lower(), 'application/octet-stream')
    
    @classmethod
    def get_material_path(cls, filename, user_id):
        return os.path.join(cls.MATERIALS_FOLDER, str(user_id), filename)