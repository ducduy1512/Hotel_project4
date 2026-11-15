# HOTEL MANAGEMENT SYSTEM

## 1. Công nghệ
- Python
- Tkinter
- FastAPI
- MySQL
- REST API

## 2. Tạo database
1. Mở MySQL Workbench.
2. Chạy file hotel_management_v2_full.sql.
3. Kiểm tra database hotel_management_v2.
4. Kiểm tra các bảng đã được tạo.

## 3. Cài thư viện Python

Mở Terminal tại thư mục project:

```bash
pip install fastapi uvicorn mysql-connector-python requests tkinter
```

## 4. Chạy REST API

```bash
cd api
uvicorn main:app --reload
```

API:
http://127.0.0.1:8000

Swagger:
http://127.0.0.1:8000/docs

## 5. Chạy GUI

Mở Terminal tại thư mục project:

```bash
python app.py
```

## 6. Kiểm tra kết nối database

Truy cập:

http://127.0.0.1:8000/health/db

Nếu kết nối thành công, API sẽ trả về thông báo database hoạt động.
