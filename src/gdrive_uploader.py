"""
Google Drive Uploader
Upload crawled data files to Google Drive
"""

import argparse
import glob
import json
import os
import sys
from pathlib import Path
from datetime import datetime

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


SCOPES = ['https://www.googleapis.com/auth/drive.file']


def authenticate(credentials_path: str = None, credentials_json: str = None):
    """
    Authenticate với Google Drive API
    
    Args:
        credentials_path: Đường dẫn đến file JSON credentials
        credentials_json: Nội dung JSON credentials (dùng cho GitHub Actions)
    """
    if credentials_json:
        # Parse JSON string
        creds_dict = json.loads(credentials_json)
        credentials = service_account.Credentials.from_service_account_info(
            creds_dict, scopes=SCOPES
        )
    elif credentials_path and os.path.exists(credentials_path):
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path, scopes=SCOPES
        )
    else:
        raise ValueError("Cần cung cấp credentials_path hoặc credentials_json")
    
    service = build('drive', 'v3', credentials=credentials)
    return service


def upload_file(service, file_path: str, folder_id: str, overwrite: bool = True) -> dict:
    """
    Upload file lên Google Drive
    
    Args:
        service: Google Drive service
        file_path: Đường dẫn file cần upload
        folder_id: ID folder Google Drive
        overwrite: Ghi đè nếu file đã tồn tại
    
    Returns:
        dict: Thông tin file đã upload
    """
    file_path = Path(file_path)
    file_name = file_path.name
    
    # Xác định MIME type
    mime_types = {
        '.csv': 'text/csv',
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.xls': 'application/vnd.ms-excel',
        '.json': 'application/json',
        '.txt': 'text/plain',
    }
    mime_type = mime_types.get(file_path.suffix.lower(), 'application/octet-stream')
    
    # Kiểm tra file đã tồn tại chưa
    if overwrite:
        query = f"name='{file_name}' and '{folder_id}' in parents and trashed=false"
        results = service.files().list(q=query, fields="files(id, name)").execute()
        existing_files = results.get('files', [])
        
        # Xóa file cũ nếu tồn tại
        for f in existing_files:
            print(f"   🗑️ Xóa file cũ: {f['name']} (ID: {f['id']})")
            service.files().delete(fileId=f['id']).execute()
    
    # Upload file mới
    file_metadata = {
        'name': file_name,
        'parents': [folder_id]
    }
    
    media = MediaFileUpload(
        str(file_path),
        mimetype=mime_type,
        resumable=True
    )
    
    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id, name, webViewLink'
    ).execute()
    
    return file


def upload_multiple_files(
    service, 
    file_patterns: list, 
    folder_id: str, 
    overwrite: bool = True
) -> list:
    """
    Upload nhiều files theo pattern
    
    Args:
        service: Google Drive service
        file_patterns: List các glob patterns (e.g., ['data/*.csv', 'data/*.xlsx'])
        folder_id: ID folder Google Drive
        overwrite: Ghi đè nếu file đã tồn tại
    
    Returns:
        list: Danh sách files đã upload
    """
    uploaded_files = []
    
    for pattern in file_patterns:
        files = glob.glob(pattern)
        for file_path in files:
            if os.path.isfile(file_path):
                print(f"📤 Uploading: {file_path}")
                try:
                    result = upload_file(service, file_path, folder_id, overwrite)
                    print(f"   ✅ Uploaded: {result['name']}")
                    print(f"   🔗 Link: {result.get('webViewLink', 'N/A')}")
                    uploaded_files.append(result)
                except Exception as e:
                    print(f"   ❌ Error uploading {file_path}: {e}")
    
    return uploaded_files


def main():
    parser = argparse.ArgumentParser(description="Upload files to Google Drive")
    parser.add_argument(
        "--credentials", "-c",
        type=str,
        default="credentials.json",
        help="Path to credentials JSON file"
    )
    parser.add_argument(
        "--credentials-json",
        type=str,
        default=None,
        help="Credentials JSON string (alternative to file)"
    )
    parser.add_argument(
        "--folder-id", "-f",
        type=str,
        required=True,
        help="Google Drive folder ID"
    )
    parser.add_argument(
        "--file-pattern", "-p",
        type=str,
        nargs="+",
        default=["data/*.csv", "data/*.xlsx"],
        help="File patterns to upload (default: data/*.csv data/*.xlsx)"
    )
    parser.add_argument(
        "--no-overwrite",
        action="store_true",
        help="Don't overwrite existing files"
    )
    
    args = parser.parse_args()
    
    print("=" * 50)
    print("☁️  Google Drive Uploader")
    print("=" * 50)
    print(f"📁 Folder ID: {args.folder_id}")
    print(f"📋 Patterns: {args.file_pattern}")
    print("=" * 50)
    
    # Check if any files exist
    all_files = []
    for pattern in args.file_pattern:
        all_files.extend(glob.glob(pattern))
    
    if not all_files:
        print("⚠️ Không tìm thấy file nào để upload")
        print(f"   Patterns: {args.file_pattern}")
        return 0
    
    print(f"\n📂 Tìm thấy {len(all_files)} files:")
    for f in all_files:
        print(f"   - {f}")
    print()
    
    try:
        # Authenticate
        print("🔐 Đang xác thực với Google Drive...")
        
        # Ưu tiên credentials từ environment variable (GitHub Actions)
        creds_json = args.credentials_json or os.environ.get('GDRIVE_CREDENTIALS')
        
        if creds_json:
            service = authenticate(credentials_json=creds_json)
        else:
            service = authenticate(credentials_path=args.credentials)
        
        print("✅ Xác thực thành công!\n")
        
        # Upload files
        uploaded = upload_multiple_files(
            service,
            args.file_pattern,
            args.folder_id,
            overwrite=not args.no_overwrite
        )
        
        print("\n" + "=" * 50)
        print(f"🎉 Đã upload {len(uploaded)} files lên Google Drive!")
        print("=" * 50)
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())