# HOTEL MANAGEMENT SYSTEM

Dự án quản lý khách sạn dùng **MySQL + FastAPI REST API + giao diện Tkinter**. Giao diện hiện tại được giữ nguyên; mọi màn hình quản trị trao đổi dữ liệu với MySQL thông qua HTTP API.

## 1. Công nghệ và phiên bản

- Python 3.10+
- MySQL Server 8.0.16+ (để thực thi CHECK constraint)
- MySQL Workbench
- FastAPI + Uvicorn
- Tkinter (đi kèm phần lớn bản cài Python trên Windows)
- mysql-connector-python, python-dotenv

## 2. Cấu trúc dự án

```text
Hotel_project5/
├── Hotel_Table.sql          # Tạo database, 8 bảng ERD và bảng users bổ trợ
├── Hotel_InsertData.sql     # Dữ liệu mẫu (nạp trước Trigger để giữ lịch sử)
├── Hotel_Procedures.sql     # 15 Stored Procedures
├── Hotel_Trigger.sql        # 15 Trigger kiểm soát nghiệp vụ
├── Hotel_Report.sql         # 10 View phục vụ báo cáo/giao diện
├── Hotel_TestCase.sql       # Kiểm tra đối tượng, toàn vẹn và test âm
├── Hotel_Complete.sql       # Bản SQL tổng hợp một file (thay cho 5 file trên)
├── .env.example             # Mẫu cấu hình máy cá nhân
├── app.py                   # Điểm chạy GUI Tkinter
├── api_client.py            # HTTP client dùng chung, tự gửi Bearer Token
├── database.py              # Cấu hình kết nối MySQL từ .env
├── api/                     # FastAPI REST API
│   ├── main.py
│   ├── database.py
│   ├── dependencies.py
│   ├── schemas.py
│   └── routers/              # auth, customers, rooms, bookings, services...
├── pages/                   # Các màn hình Tkinter
├── images/                  # Hình ảnh giao diện
├── requirements.txt
└── README.md
```

## 3. Thiết kế Database theo ERD

Tám bảng nghiệp vụ giữ đúng các thực thể trong ERD:

1. `loaiphong` – loại phòng.
2. `phong` – phòng.
3. `khach` – khách hàng.
4. `booking` – đặt phòng.
5. `dichvu` – dịch vụ.
6. `muacaodiem` – mùa cao điểm.
7. `pay` – thanh toán.
8. `hoadon` – hóa đơn.

Bảng `users` là bảng bổ trợ xác thực tài khoản, không phải thực thể nghiệp vụ thứ 9 trong ERD. `pay.so_tien` và `hoadon.ngay_lap` được giữ làm thuộc tính bổ sung theo lựa chọn B.

### Quan hệ chính

- LoaiPhong 1–N Phong.
- Phong 1–N Booking; Khach 1–N Booking.
- Phong 1–N DichVu; Booking 1–N DichVu.
- Phong 1–N MuaCaoDiem.
- Booking 1–N Pay; Khach 1–N Pay.
- Pay 1–1 HoaDon (được bảo đảm bằng UNIQUE trên `hoadon.pay_id`).

Trong `dichvu`, dịch vụ mặc định gắn phòng có `booking_id = NULL`; dịch vụ được dùng trong một lần lưu trú có cả `phong_id` và `booking_id`. Trigger kiểm tra hai thông tin phòng phải khớp. Khi tạo Booking, Trigger sao chép dịch vụ mặc định của phòng sang Booking.

## 4. Cài đặt SQL bằng MySQL Workbench

**Cách chuẩn – chạy lần lượt 6 file:**

1. Mở MySQL Workbench và kết nối MySQL Server.
2. Mở, chạy toàn bộ `Hotel_Table.sql`.
3. Chạy `Hotel_InsertData.sql`.
4. Chạy `Hotel_Procedures.sql`.
5. Chạy `Hotel_Trigger.sql`.
6. Chạy `Hotel_Report.sql`.
7. Chạy `Hotel_TestCase.sql` để kiểm tra kết quả.

Có thể thay bước 2–6 bằng một lần chạy `Hotel_Complete.sql`. **Không chạy `Hotel_Complete.sql` cùng với các file rời**, vì đó là hai cách cài đặt thay thế nhau.

> **CẢNH BÁO DỮ LIỆU:** `Hotel_Table.sql` và `Hotel_Complete.sql` có `DROP DATABASE IF EXISTS hotel_management_erd`. Việc chạy sẽ xóa và tạo lại database này. Hãy sao lưu database đang có trước khi chạy.

Dữ liệu mẫu được nạp trước khi tạo Trigger để không áp các quy tắc giao dịch hiện tại lên các bản ghi lịch sử. Riêng hóa đơn của giao dịch hoàn tiền mẫu Pay #11 đã được bổ sung; giao dịch thất bại Pay #10 không có hóa đơn.

### Kết quả cấu trúc mong đợi trong Workbench

- Tables: 9 (8 bảng ERD + `users`).
- Triggers: 15.
- Stored Procedures: 15.
- Views: 10.

`Hotel_TestCase.sql` trả về số lượng đối tượng và các bộ đếm lỗi quan hệ. Các cột `invalid_count`/`invalid_pair_count` cần bằng 0. Dùng kết quả `SHOW TABLES`, `SHOW TRIGGERS`, `SHOW PROCEDURE STATUS`, và `SHOW FULL TABLES WHERE Table_type = 'VIEW'` để chụp hình minh chứng tương tự bố cục bài tham khảo Retail.

## 5. Cấu hình trên máy cá nhân

Tại thư mục gốc project, sao chép `.env.example` thành `.env`, sau đó chỉnh mật khẩu MySQL và chuỗi bí mật:

```dotenv
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=mat_khau_mysql_cua_ban
DB_NAME=hotel_management_erd
DB_CONNECT_TIMEOUT=10
HOTEL_API_URL=http://127.0.0.1:8000
HOTEL_AUTH_SECRET=mot_chuoi_bi_mat_ngau_nhien_dai_hon_32_ky_tu
```

Không gửi file `.env` hoặc `session.json` lên Git. `.env` và phiên đăng nhập đã được thêm vào `.gitignore`.

## 6. Cài thư viện Python

Mở Terminal trong thư mục gốc `Hotel_project5` (PyCharm cũng dùng thư mục này làm Working Directory):

```powershell
py --version
py -m venv .venv
.venv\Scripts\Activate.ps1
py -m pip install --upgrade pip
py -m pip install -r requirements.txt
```

Nếu máy đã nhận lệnh `python`, có thể thay `py` bằng `python`. Nếu cả `py` và `python` đều không được nhận diện, hãy cài Python từ python.org, chọn **Add Python to PATH**, sau đó mở lại PyCharm/Terminal. Trên Windows, Tkinter thường được cài kèm Python; nếu `import tkinter` không hoạt động, cài lại Python với thành phần Tcl/Tk được chọn.

## 7. Chạy dự án trong PyCharm

**Terminal 1 – khởi động API:**

```powershell
py -m uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

**Terminal 2 – khởi động GUI:**

```powershell
py app.py
```

Tài liệu API: http://127.0.0.1:8000/docs

API health: http://127.0.0.1:8000/health

Kiểm tra đầy đủ database/object: http://127.0.0.1:8000/health/db

Endpoint `/health/db` chỉ báo OK khi tìm thấy đủ 8 bảng ERD, bảng `users`, 15 Trigger, 15 Stored Procedure và 10 View.

## 8. Tài khoản và phân quyền

Sau khi chạy SQL mẫu:

- Username: `admin`
- Password: `Admin@123`
- Role: `ADMIN`

Đổi mật khẩu quản trị trước khi sử dụng thật. API đăng ký công khai luôn tạo `CUSTOMER`. Khi đăng nhập, ADMIN vào giao diện quản trị hiện tại; CUSTOMER được chuyển sang Cổng khách hàng riêng. Các router quản lý khách, phòng, Booking, dịch vụ, thanh toán, hóa đơn và báo cáo yêu cầu Bearer Token của ADMIN. Router `/api/customer/*` yêu cầu Bearer Token của CUSTOMER và lọc dữ liệu theo hồ sơ khách hàng gắn với tài khoản. API Client của GUI tự đính kèm token sau đăng nhập.

## 9. Luồng nghiệp vụ cần kiểm thử

1. Tạo khách hàng và phòng (nếu không dùng dữ liệu mẫu).
2. Kiểm tra phòng trống theo ngày.
3. Tạo Booking và xác nhận Booking.
4. Nhận phòng, thêm dịch vụ.
5. Lập hóa đơn/tính tiền theo số đêm, hệ số mùa cao điểm và dịch vụ.
6. Cập nhật Pay sang `THANH_CONG` sau khi hóa đơn hợp lệ đã tồn tại.
7. Trả phòng; kiểm tra trạng thái phòng được đồng bộ.
8. Thử đặt trùng phòng, gắn dịch vụ sai phòng, sửa giao dịch sau khi tạo và xóa hóa đơn đã thanh toán; các thao tác trái quy tắc phải bị từ chối.

## 10. Lưu ý kiểm thử

Mã Python đã được kiểm tra cú pháp trong gói bàn giao. SQL cần được thực thi trên MySQL Server 8.0.16+ để xác nhận cú pháp/runtime của Trigger, Stored Procedure và View trong môi trường máy bạn. Tôi không đánh dấu SQL là đã chạy thành công trên MySQL khi chưa có kết nối tới MySQL Server thực tế.
## Cổng khách hàng (CUSTOMER)

Ứng dụng có hai không gian làm việc tách biệt theo role:

- `ADMIN`: giữ giao diện quản trị hiện tại.
- `CUSTOMER`: sau khi đăng nhập sẽ mở cổng khách hàng riêng, không nhìn thấy menu quản trị.

Khách hàng có thể tìm phòng trống theo ngày, gửi Booking, xem/hủy Booking của chính mình (theo điều kiện nghiệp vụ), xem chi tiết dịch vụ và hóa đơn, đồng thời tạo yêu cầu thanh toán. API lấy `khach_id` từ Bearer Token; không nhận `khach_id` từ payload khách gửi lên.

Các API CUSTOMER mới (đều yêu cầu role `CUSTOMER`):

- `GET /api/customer/me` – hồ sơ tài khoản hiện tại.
- `GET /api/customer/available-rooms?ngay_nhan=YYYY-MM-DD&ngay_tra=YYYY-MM-DD` – tra phòng trống.
- `POST /api/customer/bookings` – tạo Booking cho chính khách hàng đang đăng nhập.
- `GET /api/customer/bookings` và `GET /api/customer/bookings/{booking_id}` – lịch sử/chi tiết Booking của chính mình.
- `POST /api/customer/bookings/{booking_id}/cancel` – gửi yêu cầu hủy theo Stored Procedure.
- `POST /api/customer/bookings/{booking_id}/payment` – tạo Pay ở trạng thái `CHO_THANH_TOAN` và hóa đơn.
- `GET /api/customer/invoices` – chỉ xem hóa đơn của chính khách hàng.

**Lưu ý thanh toán:** dự án chưa tích hợp cổng thanh toán điện tử. Chức năng CUSTOMER hiện tạo yêu cầu thanh toán và chứng từ ở trạng thái chờ; nhân viên ADMIN cần xác nhận giao dịch sau khi nhận tiền. Không xem thao tác này là thanh toán trực tuyến đã hoàn tất.

