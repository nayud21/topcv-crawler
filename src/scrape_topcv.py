"""
TopCV Job Crawler
Crawl job listings from TopCV.vn with company information
"""

import time
import re
import random
import unicodedata
from typing import Dict, List, Optional, Iterable
from urllib.parse import urljoin, urlparse
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup
import pandas as pd
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

BASE = "https://www.topcv.vn"

# Rotate User-Agents to avoid detection
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]


def get_headers() -> dict:
    """Get headers with random User-Agent"""
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://www.topcv.vn/",
        "Connection": "keep-alive",
        "Cache-Control": "max-age=0",
        "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
    }


def build_session() -> requests.Session:
    s = requests.Session()
    s.headers.update(get_headers())

    retry = Retry(
        total=5,
        connect=3,
        read=3,
        status=5,
        backoff_factor=2.0,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET", "HEAD"]),
        raise_on_status=False,
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=20)
    s.mount("https://", adapter)
    s.mount("http://", adapter)

    # Initial request to get cookies
    try:
        print("[INFO] Initializing session with TopCV...")
        r = s.get(BASE, timeout=30)
        if r.status_code == 200:
            print("[INFO] Session initialized successfully")
        time.sleep(random.uniform(2.0, 4.0))
    except requests.RequestException as e:
        print(f"[WARN] Failed to initialize session: {e}")
    
    return s


def text(el) -> Optional[str]:
    if not el:
        return None
    t = el.get_text(" ", strip=True)
    return re.sub(r"\s+", " ", t) if t else None


def smart_sleep(min_s=2.0, max_s=5.0):
    """Sleep with random delay to avoid detection"""
    delay = random.uniform(min_s, max_s)
    time.sleep(delay)


def get_soup(session: requests.Session, url: str) -> BeautifulSoup:
    """Get BeautifulSoup object with retry logic and anti-bot measures"""
    for attempt in range(1, 6):
        try:
            # Rotate User-Agent on each attempt
            session.headers.update({"User-Agent": random.choice(USER_AGENTS)})
            
            # Add random delay before request
            if attempt > 1:
                wait_time = random.uniform(3.0, 6.0) * attempt
                print(f"[INFO] Waiting {wait_time:.1f}s before retry...")
                time.sleep(wait_time)
            
            r = session.get(url, timeout=30)
            
            if r.status_code == 200:
                return BeautifulSoup(r.text, "lxml")
            
            if r.status_code == 403:
                print(f"[WARN] 403 Forbidden at {url} (attempt {attempt}/5)")
                if attempt < 5:
                    # Wait longer and try with new headers
                    wait_time = random.uniform(10.0, 20.0) * attempt
                    print(f"[INFO] Waiting {wait_time:.1f}s before retry with new headers...")
                    time.sleep(wait_time)
                    session.headers.update(get_headers())
                    continue
                else:
                    print(f"[ERROR] Failed after 5 attempts for {url}")
                    return BeautifulSoup("", "lxml")
            
            if r.status_code == 429:
                retry_after = r.headers.get("Retry-After", str(30 * attempt))
                try:
                    wait = int(retry_after)
                except ValueError:
                    wait = 30 * attempt
                wait = wait + random.uniform(5.0, 15.0)
                print(f"[WARN] 429 Rate Limited → sleeping {wait:.1f}s (attempt {attempt}/5)")
                time.sleep(wait)
                continue
            
            r.raise_for_status()
            return BeautifulSoup(r.text, "lxml")
            
        except requests.exceptions.RequestException as e:
            print(f"[WARN] Request error (attempt {attempt}/5): {e}")
            if attempt < 5:
                time.sleep(random.uniform(5.0, 10.0) * attempt)
                continue
            raise
    
    return BeautifulSoup("", "lxml")


# ------------ Search page ------------
def parse_search_page(session: requests.Session, url: str) -> List[Dict]:
    soup = get_soup(session, url)
    jobs = []
    for job in soup.select("div.job-item-search-result"):
        a_title = job.select_one("h3.title a[href]")
        if not a_title:
            continue
        title = text(a_title)
        job_url = urljoin(BASE, a_title.get("href"))

        comp_a = job.select_one("a.company[href]")
        company = text(job.select_one("a.company .company-name"))
        company_url = urljoin(BASE, comp_a.get("href")) if comp_a else None

        salary = text(job.select_one("label.title-salary"))
        address = text(job.select_one("label.address .city-text"))
        exp = text(job.select_one("label.exp span"))

        jobs.append({
            "title": title,
            "job_url": job_url,
            "company": company,
            "company_url": company_url,
            "salary_list": salary,
            "address_list": address,
            "exp_list": exp,
        })
    return jobs


# ------------ Job detail page ------------
def pick_info_value(soup: BeautifulSoup, title: str) -> Optional[str]:
    for sec in soup.select(".job-detail__info--section"):
        t = text(sec.select_one(".job-detail__info--section-content-title")) or ""
        if t.lower() == title.lower():
            v = sec.select_one(".job-detail__info--section-content-value")
            return text(v) if v else text(sec)
    return None


def extract_deadline(soup: BeautifulSoup) -> Optional[str]:
    for el in soup.select(".job-detail__info--deadline, .job-detail__information-detail--actions-label"):
        t = text(el)
        if t and "Hạn nộp" in t:
            m = re.search(r"(\d{1,2}/\d{1,2}/\d{4})", t)
            return m.group(1) if m else t
    return None


def extract_tags(soup: BeautifulSoup):
    return [text(a) for a in soup.select(".job-tags a.item") if text(a)]


def extract_desc_blocks(soup: BeautifulSoup):
    data = {}
    for item in soup.select(".job-description .job-description__item"):
        h3 = text(item.select_one("h3")) or ""
        content = item.select_one(".job-description__item--content")
        if content:
            data[h3] = text(content)
    return data


def extract_working_addresses(soup: BeautifulSoup):
    out = []
    for item in soup.select(".job-description__item h3"):
        if "Địa điểm làm việc" in (text(item) or ""):
            wrap = item.find_parent(class_="job-description__item")
            if wrap:
                for d in wrap.select(".job-description__item--content div, .job-description__item--content li"):
                    val = text(d)
                    if val:
                        out.append(val)
    return out


def extract_working_times(soup: BeautifulSoup):
    out = []
    for item in soup.select(".job-description__item h3"):
        if "Thời gian làm việc" in (text(item) or ""):
            wrap = item.find_parent(class_="job-description__item")
            if wrap:
                for d in wrap.select(".job-description__item--content div, .job-description__item--content li"):
                    val = text(d)
                    if val:
                        out.append(val)
    return out


def extract_company_link_from_job(soup: BeautifulSoup) -> Optional[str]:
    cand = soup.select_one("a.company[href]") or soup.select_one("a[href*='/cong-ty/']")
    return urljoin(BASE, cand["href"]) if cand and cand.has_attr("href") else None


def scrape_job_detail(session: requests.Session, job_url: str) -> Dict:
    soup = get_soup(session, job_url)
    smart_sleep()

    title = text(soup.select_one(".job-detail__info--title, h1"))
    salary = pick_info_value(soup, "Mức lương")
    location = pick_info_value(soup, "Địa điểm")
    experience = pick_info_value(soup, "Kinh nghiệm")
    deadline = extract_deadline(soup)
    tags = extract_tags(soup)
    desc_blocks = extract_desc_blocks(soup)
    addrs = extract_working_addresses(soup)
    times = extract_working_times(soup)
    company_url_detail = extract_company_link_from_job(soup)

    return {
        "detail_title": title,
        "detail_salary": salary,
        "detail_location": location,
        "detail_experience": experience,
        "deadline": deadline,
        "tags": "; ".join(tags) if tags else None,
        "desc_mota": desc_blocks.get("Mô tả công việc"),
        "desc_yeucau": desc_blocks.get("Yêu cầu ứng viên"),
        "desc_quyenloi": desc_blocks.get("Quyền lợi"),
        "working_addresses": "; ".join(addrs) if addrs else None,
        "working_times": "; ".join(times) if times else None,
        "company_url_from_job": company_url_detail,
    }


# ------------ Company page ------------
def scrape_company(session: requests.Session, company_url: Optional[str]) -> Dict:
    if not company_url:
        return {
            "company_name_full": None,
            "company_website": None,
            "company_size": None,
            "company_industry": None,
            "company_address": None,
            "company_description": None,
        }
    soup = get_soup(session, company_url)
    smart_sleep()

    company_name = None
    for css in ["h1.company-name", "h1.title", "div.company-header h1", "div.company-info h1",
                "meta[property='og:title']", "meta[property='og:site_name']", "title"]:
        el = soup.select_one(css)
        if el:
            company_name = el.get("content") if el.name == "meta" else text(el)
            if company_name:
                company_name = re.sub(r"\s*\|\s*TopCV.*$", "", company_name, flags=re.I)
                break

    website = size = industry = address = None
    containers = [
        "div.company-overview", "div.company-detail", "div.company-profile",
        "section#company", "section.company-info", "div.box-intro-company",
        "div.company-info-container"
    ]
    container = None
    for css in containers:
        c = soup.select_one(css)
        if c:
            container = c
            break
    if container is None:
        container = soup

    rows = container.select("li, .row, .item, .info-item, .company-info-item, .dl, .d-flex")
    for row in rows:
        row_text = text(row) or ""
        label = None
        value = None
        strong = row.find(["strong", "b"])
        if strong:
            label = text(strong)
            value = row_text
            if label:
                value = re.sub(re.escape(label), "", value, flags=re.I).strip(" :-–—")
        else:
            m = re.match(r"^([^:：]+)[:：]\s*(.+)$", row_text)
            if m:
                label, value = m.group(1).strip(), m.group(2).strip()

        if not label or not value:
            continue

        ln = re.sub(r"\s+", " ", label.lower())
        if "website" in ln or "trang web" in ln:
            website = value
        elif "quy mô" in ln or "size" in ln or "nhân sự" in ln:
            size = value
        elif "lĩnh vực" in ln or "industry" in ln or "ngành" in ln:
            industry = value
        elif "địa chỉ" in ln or "address" in ln:
            address = value

    description = None
    for css in [
        "div.company-description", "div#company-description", "div.box-intro-company",
        "div.company-introduction", "div.description", "section.company-description",
        "div#readmore-company", "div#readmore-content"
    ]:
        el = soup.select_one(css)
        if el:
            description = text(el)
            if description:
                break

    return {
        "company_name_full": company_name,
        "company_website": website,
        "company_size": size,
        "company_industry": industry,
        "company_address": address,
        "company_description": description,
    }


# ------------ Pipeline with Timestamp ------------
def crawl_to_dataframe(
    query_url_template: str, 
    start_page: int = 1, 
    end_page: int = 1,
    delay_between_pages=(0.5, 1),
    crawl_date: str = None
) -> pd.DataFrame:
    """
    Crawl and add crawl_date column to DataFrame
    
    Args:
        query_url_template: URL template with {page}
        start_page: Start page
        end_page: End page
        delay_between_pages: Delay between pages
        crawl_date: Crawl date (format YYYY-MM-DD). If None, use today
    """
    if crawl_date is None:
        crawl_date = datetime.now().strftime("%Y-%m-%d")
    
    rows: List[Dict] = []
    seen_jobs = set()

    s = build_session()

    for page in range(start_page, end_page + 1):
        url = query_url_template.format(page=page)
        print(f"[INFO] Crawling search page {page}: {url}")
        jobs = parse_search_page(s, url)

        if not jobs:
            print(f"[INFO] Page {page} has no jobs — stopping early.")
            break

        for j in jobs:
            job_url = j["job_url"]
            job_id = urlparse(job_url).path
            if job_id in seen_jobs:
                continue
            seen_jobs.add(job_id)

            try:
                detail = scrape_job_detail(s, job_url)
            except Exception as e:
                print(f"[WARN] Error job detail {job_url}: {e}")
                detail = {k: None for k in [
                    "detail_title", "detail_salary", "detail_location",
                    "detail_experience", "deadline", "tags", "desc_mota",
                    "desc_yeucau", "desc_quyenloi", "working_addresses",
                    "working_times", "company_url_from_job"
                ]}

            company_url = detail.get("company_url_from_job") or j.get("company_url")

            try:
                comp = scrape_company(s, company_url)
            except Exception as e:
                print(f"[WARN] Error company {company_url}: {e}")
                comp = {k: None for k in [
                    "company_name_full", "company_website", "company_size",
                    "company_industry", "company_address", "company_description"
                ]}

            row = {**j, **detail, **comp}
            row["crawl_date"] = crawl_date
            rows.append(row)

        smart_sleep(*delay_between_pages)

    df = pd.DataFrame(rows)
    
    cols = [
        "crawl_date",
        "title", "detail_title",
        "job_url",
        "company", "company_name_full",
        "company_url", "company_url_from_job",
        "salary_list", "detail_salary",
        "address_list", "detail_location",
        "exp_list", "detail_experience",
        "deadline", "tags",
        "working_addresses", "working_times",
        "desc_mota", "desc_yeucau", "desc_quyenloi",
        "company_website", "company_size", "company_industry",
        "company_address", "company_description",
    ]
    cols = [c for c in cols if c in df.columns]
    return df.loc[:, cols] if cols else df


def slugify(text: str) -> str:
    """'Data Engineer' -> 'data-engineer', 'Kỹ sư phần mềm' -> 'ky-su-phan-mem'."""
    text = unicodedata.normalize("NFD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9\s-]", " ", text)
    text = re.sub(r"\s+", "-", text.strip())
    text = re.sub(r"-+", "-", text)
    return text.lower()


def build_search_template(keyword: str) -> str:
    slug = slugify(keyword)
    return f"https://www.topcv.vn/tim-viec-lam-{slug}?type_keyword=1&page={{page}}&sba=1"


def crawl_many_keywords(
    keywords: Iterable[str],
    start_page: int,
    end_page: int,
    delay_between_pages=(0.5, 1.0),
    sleep_between_keywords=(1.0, 2.0),
    crawl_date: str = None
) -> pd.DataFrame:
    """Crawl multiple keywords and return combined DataFrame."""
    if crawl_date is None:
        crawl_date = datetime.now().strftime("%Y-%m-%d")
    
    all_frames: List[pd.DataFrame] = []

    for kw in keywords:
        qtpl = build_search_template(kw)
        df_kw = crawl_to_dataframe(
            qtpl, 
            start_page=start_page, 
            end_page=end_page, 
            delay_between_pages=delay_between_pages,
            crawl_date=crawl_date
        )
        if df_kw is None or df_kw.empty:
            continue
        df_kw.insert(1, "search_keyword", kw)
        df_kw.insert(2, "search_slug", slugify(kw))
        all_frames.append(df_kw)
        smart_sleep(*sleep_between_keywords)

    if not all_frames:
        return pd.DataFrame()

    df_all = pd.concat(all_frames, ignore_index=True)
    for key in ("job_path", "job_url"):
        if key in df_all.columns:
            df_all = df_all.drop_duplicates(subset=[key])
            break
    return df_all
