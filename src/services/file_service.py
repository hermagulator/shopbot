# src/services/file_service.py
import os
import aiofiles
import hashlib
import magic
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, BinaryIO
from ..config import Config

class FileService:
    """سرویس مدیریت فایل‌ها"""
    
    ALLOWED_EXTENSIONS = {
        # تصاویر
        'image/jpeg': '.jpg',
        'image/png': '.png',
        'image/gif': '.gif',
        
        # فایل‌های دیجیتال
        'application/pdf': '.pdf',
        'application/zip': '.zip',
        'application/x-rar-compressed': '.rar',
        'application/x-7z-compressed': '.7z',
        
        # فایل‌های نرم‌افزاری
        'application/x-msdownload': '.exe',
        'application/x-apple-diskimage': '.dmg',
        'application/x-debian-package': '.deb',
        'application/vnd.android.package-archive': '.apk'
    }
    
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
    
    def __init__(self, db):
        self.db = db
        self.upload_path = Config.UPLOAD_DIR
        self.ensure_directories()
        
    def ensure_directories(self):
        """اطمینان از وجود دایرکتوری‌های مورد نیاز"""
        paths = [
            self.upload_path / 'products',
            self.upload_path / 'receipts',
            self.upload_path / 'temp'
        ]
        
        for path in paths:
            path.mkdir(parents=True, exist_ok=True)
            
    async def save_file(self, file: BinaryIO, file_type: str, 
                       original_filename: str) -> Optional[Dict[str, Any]]:
        """ذخیره فایل آپلود شده"""
        try:
            # خواندن محتوای فایل
            file_content = file.read()
            
            # بررسی سایز فایل
            if len(file_content) > self.MAX_FILE_SIZE:
                return {
                    'success': False,
                    'error': 'حجم فایل بیش از حد مجاز است'
                }
                
            # بررسی نوع فایل
            mime_type = magic.from_buffer(file_content, mime=True)
            if mime_type not in self.ALLOWED_EXTENSIONS:
                return {
                    'success': False,
                    'error': 'نوع فایل مجاز نیست'
                }
                
            # ایجاد نام یکتا برای فایل
            file_hash = hashlib.sha256(file_content).hexdigest()
            extension = self.ALLOWED_EXTENSIONS[mime_type]
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{timestamp}_{file_hash[:8]}{extension}"
            
            # تعیین مسیر ذخیره‌سازی
            save_path = self.upload_path / file_type / filename
            
            # ذخیره فایل
            async with aiofiles.open(save_path, 'wb') as f:
                await f.write(file_content)
                
            return {
                'success': True,
                'filename': filename,
                'mime_type': mime_type,
                'size': len(file_content),
                'path': str(save_path)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'خطا در ذخیره فایل: {str(e)}'
            }

    async def get_file_path(self, filename: str, file_type: str) -> Optional[Path]:
        """دریافت مسیر فایل"""
        file_path = self.upload_path / file_type / filename
        if file_path.exists():
            return file_path
        return None
        
    async def delete_file(self, filename: str, file_type: str) -> bool:
        """حذف فایل"""
        try:
            file_path = self.upload_path / file_type / filename
            if file_path.exists():
                file_path.unlink()
                return True
            return False
        except Exception:
            return False
