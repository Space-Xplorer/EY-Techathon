"""
File Validation Utilities
Validates uploaded files for security and integrity
"""

import os
import magic
from PyPDF2 import PdfReader
from typing import Dict, Optional


class FileValidator:
    """Validates files before processing"""
    
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
    ALLOWED_TYPES = ['.pdf']
    MAX_BATCH_SIZE = 10
    
    @staticmethod
    def validate_pdf(file_path: str) -> Dict:
        """
        Comprehensive PDF validation
        
        Returns:
            {
                "valid": bool,
                "error": str | None,
                "metadata": {
                    "size_mb": float,
                    "pages": int,
                    "encrypted": bool
                }
            }
        """
        result = {
            "valid": False,
            "error": None,
            "metadata": {}
        }
        
        try:
            # Check 1: File exists
            if not os.path.exists(file_path):
                result["error"] = "File does not exist"
                return result
            
            # Check 2: File size
            file_size = os.path.getsize(file_path)
            size_mb = file_size / (1024 * 1024)
            result["metadata"]["size_mb"] = round(size_mb, 2)
            
            if file_size > FileValidator.MAX_FILE_SIZE:
                result["error"] = f"File too large: {size_mb:.2f}MB (max: 50MB)"
                return result
            
            # Check 3: File extension
            _, ext = os.path.splitext(file_path)
            if ext.lower() not in FileValidator.ALLOWED_TYPES:
                result["error"] = f"Invalid file type: {ext} (allowed: .pdf)"
                return result
            
            # Check 4: Valid PDF header
            with open(file_path, 'rb') as f:
                header = f.read(4)
                if header != b'%PDF':
                    result["error"] = "Invalid PDF file (missing PDF header)"
                    return result
            
            # Check 5: Can open with PyPDF2 (not corrupted)
            try:
                reader = PdfReader(file_path)
                num_pages = len(reader.pages)
                is_encrypted = reader.is_encrypted
                
                result["metadata"]["pages"] = num_pages
                result["metadata"]["encrypted"] = is_encrypted
                
                if is_encrypted:
                    result["error"] = "PDF is password protected"
                    return result
                
                if num_pages == 0:
                    result["error"] = "PDF has no pages"
                    return result
                
            except Exception as e:
                result["error"] = f"Corrupted PDF: {str(e)}"
                return result
            
            # Check 6: Detect embedded executables (basic check)
            with open(file_path, 'rb') as f:
                content = f.read()
                if b'/EmbeddedFile' in content:
                    result["error"] = "PDF contains embedded files (security risk)"
                    return result
                
                # Check for JavaScript (security risk)
                if b'/JavaScript' in content or b'/JS' in content:
                    result["error"] = "PDF contains JavaScript (security risk)"
                    return result
            
            # All checks passed
            result["valid"] = True
            return result
            
        except Exception as e:
            result["error"] = f"Validation error: {str(e)}"
            return result
    
    @staticmethod
    def validate_batch(file_paths: list) -> Dict:
        """
        Validate a batch of files
        
        Returns:
            {
                "valid": bool,
                "errors": list,
                "valid_files": list,
                "invalid_files": list
            }
        """
        if len(file_paths) > FileValidator.MAX_BATCH_SIZE:
            return {
                "valid": False,
                "errors": [f"Too many files: {len(file_paths)} (max: {FileValidator.MAX_BATCH_SIZE})"],
                "valid_files": [],
                "invalid_files": file_paths
            }
        
        valid_files = []
        invalid_files = []
        errors = []
        
        for file_path in file_paths:
            validation = FileValidator.validate_pdf(file_path)
            if validation["valid"]:
                valid_files.append(file_path)
            else:
                invalid_files.append(file_path)
                errors.append(f"{file_path}: {validation['error']}")
        
        return {
            "valid": len(invalid_files) == 0,
            "errors": errors,
            "valid_files": valid_files,
            "invalid_files": invalid_files
        }


if __name__ == "__main__":
    # Test validation
    test_file = "backend/data/rfps/test.pdf"
    result = FileValidator.validate_pdf(test_file)
    print(f"Validation result: {result}")
