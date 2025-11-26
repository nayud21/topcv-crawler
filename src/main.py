"""
Main entry point for TopCV Job Crawler
Crawl jobs and upload to Google Drive
"""

import os
import sys
import argparse
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.scrape_topcv import crawl_many_keywords, slugify
from src.gdrive_uploader import GDriveUploader, upload_to_gdrive


# Default keywords to crawl
DEFAULT_KEYWORDS = [
    "Data Analyst",
    "Data Engineer", 
    "Data Scientist",
    "Backend Developer",
    "Frontend Developer",
    "DevOps Engineer",
    "QA Engineer",
    "Mobile Developer",
    "Software Engineer",
    "Machine Learning",
    "Python Developer",
    "Java Developer",
]


def main():
    parser = argparse.ArgumentParser(
        description="Crawl TopCV IT jobs and upload to Google Drive"
    )
    
    # Crawl options
    parser.add_argument(
        "--keywords", "-k", 
        nargs="+", 
        default=DEFAULT_KEYWORDS,
        help="Keywords to search for"
    )
    parser.add_argument(
        "--start-page", 
        type=int, 
        default=1,
        help="Start page number"
    )
    parser.add_argument(
        "--end-page", 
        type=int, 
        default=3,
        help="End page number"
    )
    parser.add_argument(
        "--crawl-date",
        type=str,
        default=None,
        help="Crawl date (YYYY-MM-DD). Default: today"
    )
    
    # Output options
    parser.add_argument(
        "--output-dir", "-o",
        default="./data",
        help="Output directory for crawled data"
    )
    parser.add_argument(
        "--output-prefix",
        default="topcv_jobs",
        help="Prefix for output files"
    )
    
    # Google Drive options
    parser.add_argument(
        "--upload-gdrive",
        action="store_true",
        help="Upload to Google Drive after crawling"
    )
    parser.add_argument(
        "--gdrive-folder-id",
        default=None,
        help="Google Drive folder ID. Can also use GDRIVE_FOLDER_ID env var"
    )
    parser.add_argument(
        "--gdrive-credentials",
        default=None,
        help="Path to Google Drive service account JSON. Can also use GDRIVE_CREDENTIALS env var"
    )
    
    args = parser.parse_args()
    
    # Set crawl date
    crawl_date = args.crawl_date or datetime.now().strftime("%Y-%m-%d")
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("🕷️  TopCV Job Crawler")
    print("=" * 60)
    print(f"📅 Crawl date: {crawl_date}")
    print(f"🔍 Keywords: {', '.join(args.keywords)}")
    print(f"📄 Pages: {args.start_page} - {args.end_page}")
    print(f"📁 Output: {output_dir}")
    print("=" * 60)
    
    # Crawl data
    print("\n🚀 Starting crawl...")
    df = crawl_many_keywords(
        keywords=args.keywords,
        start_page=args.start_page,
        end_page=args.end_page,
        delay_between_pages=(1.0, 2.0),
        sleep_between_keywords=(2.0, 3.0),
        crawl_date=crawl_date
    )
    
    if df.empty:
        print("❌ No data collected!")
        return 1
    
    print(f"\n✅ Collected {len(df)} jobs")
    
    # Save combined file
    output_prefix = f"{args.output_prefix}_{crawl_date}"
    csv_path = output_dir / f"{output_prefix}_combined.csv"
    xlsx_path = output_dir / f"{output_prefix}_combined.xlsx"
    
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"💾 Saved: {csv_path}")
    
    try:
        df.to_excel(xlsx_path, index=False)
        print(f"💾 Saved: {xlsx_path}")
    except Exception as e:
        print(f"⚠️ XLSX save failed: {e}")
        xlsx_path = None
    
    # Save per-keyword files
    saved_files = [csv_path]
    if xlsx_path:
        saved_files.append(xlsx_path)
    
    for kw in args.keywords:
        slug = slugify(kw)
        df_kw = df[df["search_slug"] == slug] if "search_slug" in df.columns else df
        if not df_kw.empty:
            kw_path = output_dir / f"{args.output_prefix}_{slug}_{crawl_date}.csv"
            df_kw.to_csv(kw_path, index=False, encoding="utf-8-sig")
            print(f"💾 Saved: {kw_path}")
            saved_files.append(kw_path)
    
    # Upload to Google Drive
    if args.upload_gdrive:
        print("\n☁️  Uploading to Google Drive...")
        
        folder_id = args.gdrive_folder_id or os.environ.get('GDRIVE_FOLDER_ID')
        credentials_json = os.environ.get('GDRIVE_CREDENTIALS')
        credentials_file = args.gdrive_credentials
        
        if not folder_id:
            print("❌ No Google Drive folder ID provided!")
            print("   Set --gdrive-folder-id or GDRIVE_FOLDER_ID env var")
            return 1
        
        if not credentials_json and not credentials_file:
            print("❌ No Google Drive credentials provided!")
            print("   Set --gdrive-credentials or GDRIVE_CREDENTIALS env var")
            return 1
        
        try:
            uploader = GDriveUploader(
                credentials_json=credentials_json,
                credentials_file=credentials_file
            )
            
            # Upload main files (CSV and XLSX)
            for file_path in [csv_path, xlsx_path]:
                if file_path and file_path.exists():
                    uploader.upload_file(str(file_path), folder_id)
            
            print("\n✅ Upload complete!")
            
        except Exception as e:
            print(f"❌ Upload failed: {e}")
            return 1
    
    print("\n" + "=" * 60)
    print("🎉 Crawl completed successfully!")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
