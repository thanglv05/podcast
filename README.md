# 🔗 LinkGrabber API

Extract và filter links từ bất kỳ URL nào — REST API chạy 24/7 trên Render (miễn phí).

---

## 🚀 Deploy lên Render — hướng dẫn từng bước

### Bước 1 — Push code lên GitHub

```bash
git init
git add .
git commit -m "init linkgrabber api"
git remote add origin https://github.com/TEN_BAN/linkgrabber-api.git
git branch -M main
git push -u origin main
```

### Bước 2 — Tạo tài khoản Render
Vào https://render.com → **Get Started for Free** → **Sign up with GitHub**

### Bước 3 — Tạo Web Service
1. Click **New +** → **Web Service**
2. **Connect a repository** → chọn repo `linkgrabber-api`
3. Điền thông tin:
   - **Region**: Singapore
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: Free
4. Click **Deploy Web Service**

### Bước 4 — Thêm biến môi trường (chống sleep)
1. Vào tab **Environment** của service
2. Thêm biến:
   - Key: `RENDER_EXTERNAL_URL`
   - Value: `https://TEN-APP-CUA-BAN.onrender.com`
3. **Save Changes**

> App sẽ tự ping chính nó mỗi 10 phút → không bao giờ sleep.

### Bước 5 — Xong!
URL public: `https://TEN-APP-CUA-BAN.onrender.com`
Swagger UI: `https://TEN-APP-CUA-BAN.onrender.com/docs`

---

## 📡 API: GET /grab

| Param | Bắt buộc | Mô tả |
|-------|----------|-------|
| `url` | ✅ | URL cần crawl |
| `contains` | | Chỉ lấy links chứa chuỗi |
| `starts_with` | | Chỉ lấy links bắt đầu bằng |
| `ends_with` | | Chỉ lấy links kết thúc bằng |
| `domain` | | Chỉ lấy links từ domain này |
| `regex` | | Filter bằng regex |
| `link_type` | | `image/document/video/audio/internal/external` |
| `exclude` | | Loại bỏ links chứa chuỗi |
| `timeout` | | Timeout giây (mặc định 15) |

## 🛠 Chạy local
```bash
pip install -r requirements.txt
uvicorn main:app --reload
```
