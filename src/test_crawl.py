"""
Quick test script for TopCV crawler
Run: python test_crawl.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_connection():
    """Test 1: Kiểm tra kết nối đến TopCV"""
    print("=" * 50)
    print("🧪 Test 1: Kiểm tra kết nối đến TopCV")
    print("=" * 50)
    
    from scrape_topcv import build_session, BASE
    import requests
    
    session = build_session()
    
    try:
        r = session.get(BASE, timeout=30)
        print(f"   Status code: {r.status_code}")
        
        if r.status_code == 200:
            print(f"✅ Kết nối thành công!")
            return True, session
        elif r.status_code == 403:
            print("❌ Bị chặn (403 Forbidden)")
            return False, None
        else:
            print(f"❌ Lỗi: {r.status_code}")
            return False, None
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False, None


def test_search_page_html(session):
    """Test 2: Kiểm tra HTML của trang tìm kiếm"""
    print("\n" + "=" * 50)
    print("🧪 Test 2: Kiểm tra HTML trang tìm kiếm")
    print("=" * 50)
    
    from scrape_topcv import get_soup, slugify
    
    keyword = "Data Analyst"
    slug = slugify(keyword)
    url = f"https://www.topcv.vn/tim-viec-lam-{slug}?page=1"
    
    print(f"   URL: {url}")
    
    soup = get_soup(session, url)
    
    # Kiểm tra có nội dung không
    if not soup or not soup.text.strip():
        print("❌ Không lấy được HTML")
        return False
    
    print(f"   HTML length: {len(soup.text)} chars")
    
    # Kiểm tra các selector có thể dùng
    selectors_to_check = [
        "div.job-item-search-result",
        "div.job-item",
        "div[class*='job']",
        "div.job-list",
        "div.job-listing",
        "article.job",
        "div.job-item-2",
        "div.job-item-default",
    ]
    
    print("\n   Kiểm tra các CSS selectors:")
    found_selector = None
    for sel in selectors_to_check:
        elements = soup.select(sel)
        count = len(elements)
        status = "✅" if count > 0 else "❌"
        print(f"   {status} '{sel}': {count} elements")
        if count > 0 and found_selector is None:
            found_selector = sel
    
    # Lưu HTML để debug
    debug_file = Path("data/debug_search_page.html")
    debug_file.parent.mkdir(exist_ok=True)
    debug_file.write_text(soup.prettify()[:50000], encoding="utf-8")
    print(f"\n   💾 Saved HTML to: {debug_file}")
    
    return found_selector is not None


def test_find_jobs(session):
    """Test 3: Tìm cấu trúc job thực tế"""
    print("\n" + "=" * 50)
    print("🧪 Test 3: Phân tích cấu trúc trang")
    print("=" * 50)
    
    from scrape_topcv import get_soup, slugify
    from bs4 import BeautifulSoup
    
    keyword = "Data Analyst"
    slug = slugify(keyword)
    url = f"https://www.topcv.vn/tim-viec-lam-{slug}?page=1"
    
    soup = get_soup(session, url)
    
    # Tìm tất cả các thẻ có chứa "job" trong class
    job_elements = []
    for tag in soup.find_all(True):
        classes = tag.get("class", [])
        if any("job" in c.lower() for c in classes):
            job_elements.append((tag.name, classes))
    
    print(f"   Tìm thấy {len(job_elements)} elements có 'job' trong class:")
    
    # Đếm và hiển thị unique classes
    from collections import Counter
    class_counter = Counter()
    for tag_name, classes in job_elements:
        for c in classes:
            if "job" in c.lower():
                class_counter[f"{tag_name}.{c}"] += 1
    
    for selector, count in class_counter.most_common(10):
        print(f"      - {selector}: {count}")
    
    # Tìm các link job
    job_links = soup.select("a[href*='/viec-lam/']")
    print(f"\n   Tìm thấy {len(job_links)} links đến trang job detail")
    
    if job_links:
        print("   Ví dụ 3 links đầu:")
        for link in job_links[:3]:
            href = link.get("href", "")
            title = link.get_text(strip=True)[:50]
            print(f"      - {title}... → {href[:60]}...")
        return True
    
    return False


def test_parse_with_new_selector(session):
    """Test 4: Thử parse với selector mới"""
    print("\n" + "=" * 50)
    print("🧪 Test 4: Parse jobs với selector khác")
    print("=" * 50)
    
    from scrape_topcv import get_soup, slugify, text
    from urllib.parse import urljoin
    
    BASE = "https://www.topcv.vn"
    keyword = "Data Analyst"
    slug = slugify(keyword)
    url = f"https://www.topcv.vn/tim-viec-lam-{slug}?page=1"
    
    soup = get_soup(session, url)
    jobs = []
    
    # Thử nhiều selector khác nhau
    selectors = [
        "div.job-item-search-result",
        "div.job-item-2",
        "div.job-item-default", 
        "div.job-item",
        "div.job-list-item",
        "div[data-job-id]",
        "article.job-item",
    ]
    
    for selector in selectors:
        job_cards = soup.select(selector)
        if job_cards:
            print(f"   ✅ Selector '{selector}' tìm thấy {len(job_cards)} jobs")
            
            # Parse job đầu tiên
            job = job_cards[0]
            
            # Tìm title
            title_el = job.select_one("h3 a, h2 a, .title a, a.job-title, [class*='title'] a")
            title = text(title_el) if title_el else "N/A"
            href = title_el.get("href") if title_el else "N/A"
            
            # Tìm company
            company_el = job.select_one("a.company, .company-name, [class*='company'] a")
            company = text(company_el) if company_el else "N/A"
            
            # Tìm salary
            salary_el = job.select_one(".salary, .title-salary, [class*='salary']")
            salary = text(salary_el) if salary_el else "N/A"
            
            print(f"      Title: {title[:50]}...")
            print(f"      Company: {company}")
            print(f"      Salary: {salary}")
            print(f"      URL: {href}")
            
            jobs.append({
                "selector": selector,
                "title": title,
                "company": company,
                "salary": salary,
                "url": href
            })
            break
    
    if not jobs:
        print("   ❌ Không tìm được selector nào hoạt động")
        return False
    
    return True


def main():
    print("\n" + "=" * 60)
    print("🕷️  TopCV Crawler - Debug & Test Script")
    print("=" * 60)
    
    # Test 1: Connection
    success, session = test_connection()
    if not success:
        print("\n❌ Không thể kết nối. Kiểm tra lại network hoặc TopCV đang chặn.")
        return 1
    
    # Test 2: HTML
    test_search_page_html(session)
    
    # Test 3: Find structure
    test_find_jobs(session)
    
    # Test 4: Parse
    test_parse_with_new_selector(session)
    
    print("\n" + "=" * 60)
    print("📋 Kiểm tra file debug: data/debug_search_page.html")
    print("   Mở file này trong browser để xem cấu trúc HTML thực tế")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())