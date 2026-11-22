# Hướng dẫn giao diện Web HTML5

## Chạy ứng dụng

1. Cài các thư viện trong `requirements.txt` vào virtual environment.
2. Tạo `.env` từ `.env.example`; cấu hình `DB_PASSWORD` và `HOTEL_AUTH_SECRET` (chuỗi ngẫu nhiên riêng tối thiểu 32 ký tự). Không chia sẻ file `.env`.
3. Khởi động MySQL và nạp database theo hướng dẫn SQL hiện có. Không cần chạy migration chỉ để thay giao diện.
4. Chạy tại thư mục `Hotel_project5`:

   ```powershell
   .venv\Scripts\Activate.ps1
   python app.py
   ```

5. Trình duyệt mở `http://127.0.0.1:8000/`. Nếu không tự mở, truy cập địa chỉ này thủ công.

## Thành phần thay đổi

- `frontend/index.html`: trang gốc Web GUI.
- `frontend/styles.css`: giao diện responsive.
- `frontend/app.js`: đăng nhập/đăng ký, điều hướng, biểu mẫu và gọi API.
- `api/main.py`: phục vụ trang HTML tại `/` và static files tại `/static`; các router REST `/api/*` không đổi.
- Ảnh loại phòng nằm trong `images/` ở thư mục gốc dự án và được phục vụ tại `/images/<ten-anh>.jpg` (Standard, Deluxe, VIP, Family).
- `app.py`: khởi chạy Uvicorn; mở `http://127.0.0.1:8000/` trong Chrome hoặc Edge.

## Những phần không thay đổi

- Không chỉnh sửa file `.sql`, cấu trúc bảng, dữ liệu mẫu, Stored Procedure, Function hoặc Trigger.
- Không thay đổi schema request/response hoặc đường dẫn endpoint API hiện có.
- Tính toán, xác nhận nghiệp vụ và truy cập MySQL vẫn do FastAPI/SQL đảm nhiệm; JavaScript chỉ hiển thị và gọi API.

## Lưu ý

Thư mục `pages/` còn chứa mã Tkinter cũ để đối chiếu/lưu trữ, nhưng không còn được `app.py` sử dụng. Hãy dùng `python app.py` hoặc `python -m uvicorn api.main:app --host 127.0.0.1 --port 8000` để chạy giao diện Web.
