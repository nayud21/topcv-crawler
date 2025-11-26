# 🕷️ TopCV Job Crawler

Tự động crawl dữ liệu việc làm IT từ TopCV.vn và upload lên Google Drive.

## 📁 Cấu trúc project

```
crawl/
├── .github/
│   └── workflows/
│       └── crawl.yml          # GitHub Actions workflow
├── src/
│   ├── __init__.py
│   ├── scrape_topcv.py        # Crawler chính
│   ├── gdrive_uploader.py     # Upload Google Drive
│   └── main.py                # Entry point
├── data/                      # Dữ liệu crawl được
├── .gitignore
├── requirements.txt
└── README.md
```

## 🚀 Hướng dẫn cài đặt

### 1. Clone repository

```bash
git clone https://github.com/YOUR_USERNAME/topcv-crawler.git
cd topcv-crawler
```

### 2. Cài đặt dependencies

```bash
pip install -r requirements.txt
```

### 3. Chạy thủ công (local)

```bash
# Crawl cơ bản
python -m src.main

# Crawl với tùy chọn
python -m src.main \
    --keywords "Data Engineer" "Backend Developer" \
    --start-page 1 \
    --end-page 5 \
    --output-dir ./data
```

## ☁️ Cài đặt Google Drive Upload

### Bước 1: Tạo Google Cloud Project

1. Truy cập [Google Cloud Console](https://console.cloud.google.com/)
2. Tạo project mới hoặc chọn project có sẵn
3. Bật **Google Drive API**:
   - Vào **APIs & Services** → **Library**
   - Tìm "Google Drive API" → **Enable**

### Bước 2: Tạo Service Account

1. Vào **APIs & Services** → **Credentials**
2. Click **Create Credentials** → **Service Account**
3. Điền tên (ví dụ: `gdrive-uploader`)
4. Click **Done**
5. Click vào service account vừa tạo
6. Vào tab **Keys** → **Add Key** → **Create new key**
7. Chọn **JSON** → **Create**
8. File JSON sẽ được download - **giữ file này an toàn!**

### Bước 3: Chia sẻ folder Google Drive

1. Tạo folder trên Google Drive để lưu data
2. Copy **Folder ID** từ URL:
   ```
   https://drive.google.com/drive/folders/FOLDER_ID_Ở_ĐÂY
   ```
3. **Share folder** với email của service account:
   - Mở file JSON đã download
   - Copy email từ field `client_email`
   - Share folder với email này (quyền **Editor**)

### Bước 4: Cấu hình GitHub Secrets

1. Vào repository GitHub → **Settings** → **Secrets and variables** → **Actions**
2. Thêm 2 secrets:

   | Secret Name | Value |
   |-------------|-------|
   | `GDRIVE_CREDENTIALS` | Nội dung file JSON service account (copy toàn bộ) |
   | `GDRIVE_FOLDER_ID` | Folder ID từ URL Google Drive |

## ⚙️ GitHub Actions

### Tự động chạy

Workflow sẽ tự động chạy hàng ngày lúc **13:00 (Vietnam time)** / 6:00 UTC.

### Chạy thủ công

1. Vào tab **Actions** trên GitHub
2. Chọn workflow **Crawl TopCV Jobs**
3. Click **Run workflow**
4. Tùy chỉnh parameters nếu cần:
   - **Keywords**: Các keyword cách nhau bởi dấu phẩy
   - **Start page**: Trang bắt đầu
   - **End page**: Trang kết thúc

## 📊 Dữ liệu output

Mỗi lần crawl sẽ tạo ra các file:

- `topcv_jobs_YYYY-MM-DD_combined.csv` - Tất cả jobs
- `topcv_jobs_YYYY-MM-DD_combined.xlsx` - File Excel
- `topcv_jobs_<keyword>_YYYY-MM-DD.csv` - Jobs theo từng keyword

### Các cột dữ liệu

| Cột | Mô tả |
|-----|-------|
| `crawl_date` | Ngày crawl |
| `search_keyword` | Keyword tìm kiếm |
| `title` | Tiêu đề job |
| `job_url` | Link job |
| `company` | Tên công ty |
| `salary_list` | Mức lương |
| `address_list` | Địa điểm |
| `exp_list` | Yêu cầu kinh nghiệm |
| `deadline` | Hạn nộp hồ sơ |
| `tags` | Tags công nghệ |
| `desc_mota` | Mô tả công việc |
| `desc_yeucau` | Yêu cầu ứng viên |
| `desc_quyenloi` | Quyền lợi |
| `company_size` | Quy mô công ty |
| `company_industry` | Lĩnh vực |
| `company_address` | Địa chỉ công ty |

## 🔧 Tùy chỉnh

### Thay đổi danh sách keywords mặc định

Sửa file `src/main.py`:

```python
DEFAULT_KEYWORDS = [
    "Data Analyst",
    "Data Engineer",
    # Thêm keywords của bạn
]
```

### Thay đổi lịch chạy

Sửa file `.github/workflows/crawl.yml`:

```yaml
schedule:
  # Chạy lúc 6:00 AM UTC (13:00 Vietnam)
  - cron: '0 6 * * *'
  
  # Chạy mỗi thứ 2 và thứ 5 lúc 8:00 AM UTC
  # - cron: '0 8 * * 1,4'
```

## 🛡️ Lưu ý bảo mật

- ⚠️ **KHÔNG** commit file credentials JSON vào repository
- ⚠️ **KHÔNG** share secrets với người khác
- ✅ Sử dụng GitHub Secrets để lưu credentials
- ✅ File `.gitignore` đã được cấu hình để ignore các file nhạy cảm

## 📝 License

MIT License

## 🤝 Contributing

Pull requests are welcome! For major changes, please open an issue first.
