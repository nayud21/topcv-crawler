"""
TopCV Job Crawler - Main Entry Point
"""

import argparse
import sys
import os
from datetime import datetime
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from scrape_topcv import crawl_many_keywords, slugify


def parse_keywords(keywords_input: str) -> list:
    """
    Parse keywords from input string.
    Supports both comma-separated and semicolon-separated.
    
    Examples:
        "Data Analyst,Data Engineer" -> ["Data Analyst", "Data Engineer"]
        "Data Analyst;Data Engineer" -> ["Data Analyst", "Data Engineer"]
    """
    # Try semicolon first (safer for keywords with spaces)
    if ';' in keywords_input:
        keywords = [k.strip() for k in keywords_input.split(';')]
    else:
        keywords = [k.strip() for k in keywords_input.split(',')]
    
    # Remove empty strings
    keywords = [k for k in keywords if k]
    return keywords


def main():
    parser = argparse.ArgumentParser(
        description="TopCV Job Crawler - Crawl job listings from TopCV.vn"
    )
    parser.add_argument(
        "--keywords", "-k",
        type=str,
        default="Data Analyst;Data Engineer;Python Developer",
        help="Keywords to search (semicolon-separated recommended, e.g., 'Data Analyst;Data Engineer')"
    )
    parser.add_argument(
        "--start-page", "-s",
        type=int,
        default=1,
        help="Start page number (default: 1)"
    )
    parser.add_argument(
        "--end-page", "-e",
        type=int,
        default=3,
        help="End page number (default: 3)"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="data",
        help="Output directory (default: data)"
    )
    parser.add_argument(
        "--crawl-date",
        type=str,
        default=None,
        help="Crawl date in YYYY-MM-DD format (default: today)"
    )
    parser.add_argument(
        "--format", "-f",
        type=str,
        choices=["csv", "xlsx", "both"],
        default="both",
        help="Output format (default: both)"
    )

    args = parser.parse_args()

    # Parse keywords
    keywords = parse_keywords(args.keywords)
    
    if not keywords:
        print("❌ Error: No valid keywords provided")
        sys.exit(1)

    # Set crawl date
    crawl_date = args.crawl_date or datetime.now().strftime("%Y-%m-%d")

    # Create output directory
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Print info
    print("=" * 60)
    print("🕷️  TopCV Job Crawler")
    print("=" * 60)
    print(f"📅 Crawl date: {crawl_date}")
    print(f"🔍 Keywords ({len(keywords)}): {keywords}")
    print(f"📄 Pages: {args.start_page} - {args.end_page}")
    print(f"📁 Output: {output_dir}")
    print("=" * 60)

    # Show URL preview
    print("\n📋 URL Preview:")
    for kw in keywords:
        slug = slugify(kw)
        url = f"https://www.topcv.vn/tim-viec-lam-{slug}?page=1"
        print(f"   - '{kw}' → {url}")
    print()

    print("\n🚀 Starting crawl...")

    try:
        df = crawl_many_keywords(
            keywords=keywords,
            start_page=args.start_page,
            end_page=args.end_page,
            crawl_date=crawl_date
        )

        if df is None or df.empty:
            print("⚠️ Warning: No data collected")
            # Create empty file to indicate run completed
            empty_file = output_dir / f"no_data_{crawl_date}.txt"
            empty_file.write_text(f"No data collected on {crawl_date}\nKeywords: {keywords}")
            sys.exit(0)

        print(f"\n✅ Collected {len(df)} jobs")

        # Save files
        base_filename = f"topcv_jobs_{crawl_date}"

        if args.format in ["csv", "both"]:
            csv_path = output_dir / f"{base_filename}.csv"
            df.to_csv(csv_path, index=False, encoding="utf-8-sig")
            print(f"💾 Saved: {csv_path}")

        if args.format in ["xlsx", "both"]:
            xlsx_path = output_dir / f"{base_filename}.xlsx"
            df.to_excel(xlsx_path, index=False, engine="openpyxl")
            print(f"💾 Saved: {xlsx_path}")

        print("\n🎉 Crawl completed successfully!")

    except Exception as e:
        print(f"\n❌ Error during crawl: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()