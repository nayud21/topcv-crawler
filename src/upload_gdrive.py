"""
Upload crawled data to Google Drive
Standalone script for GitHub Actions
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from gdrive_uploader import GDriveUploader


def main():
    creds = os.environ.get('GDRIVE_CREDENTIALS')
    folder_id = os.environ.get('GDRIVE_FOLDER_ID')
    
    if not creds:
        print("❌ Error: GDRIVE_CREDENTIALS not set")
        sys.exit(1)
    
    if not folder_id:
        print("❌ Error: GDRIVE_FOLDER_ID not set")
        sys.exit(1)
    
    print("☁️ Initializing Google Drive uploader...")
    uploader = GDriveUploader(credentials_json=creds)
    
    data_dir = Path('data')
    if not data_dir.exists():
        print("❌ Error: data/ directory not found")
        sys.exit(1)
    
    uploaded = 0
    
    # Upload CSV files
    for f in data_dir.glob('*.csv'):
        print(f"📤 Uploading {f.name}...")
        try:
            uploader.upload_file(str(f), folder_id)
            uploaded += 1
        except Exception as e:
            print(f"⚠️ Failed to upload {f.name}: {e}")
    
    # Upload XLSX files
    for f in data_dir.glob('*.xlsx'):
        print(f"📤 Uploading {f.name}...")
        try:
            uploader.upload_file(str(f), folder_id)
            uploaded += 1
        except Exception as e:
            print(f"⚠️ Failed to upload {f.name}: {e}")
    
    if uploaded > 0:
        print(f"\n✅ Successfully uploaded {uploaded} file(s) to Google Drive!")
    else:
        print("\n⚠️ No files were uploaded")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
