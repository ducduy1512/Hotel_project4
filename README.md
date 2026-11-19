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
├── Hotel_Table.sql          # Tạo database, 8 bảng ERD và 3 bảng hỗ trợ
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
│   ├── qr_payment_service.py # Sinh mã nội dung + URL QR VietQR
│   ├── main.py
│   ├── database.py
│   ├── dependencies.py
│   ├── schemas.py
│   └── routers/              # auth, customers, rooms, bookings, payments, payment_gateway...
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

Các bảng `users`, `payment_qr`, `sepay_webhook_events` là bảng bổ trợ xác thực/đối soát thanh toán, không phải thực thể nghiệp vụ trong ERD. `pay.so_tien` và `hoadon.ngay_lap` được giữ làm thuộc tính bổ sung theo lựa chọn B.

### Quan hệ chính

- LoaiPhong 1–N Phong.
- Phong 1–N Booking; Khach 1–N Booking.
- Phong 1–N DichVu; Booking 1–N DichVu.
- Phong 1–N MuaCaoDiem.
- Booking 1–N Pay; Khach 1–N Pay.
- Pay 1–1 HoaDon (được bảo đảm bằng UNIQUE trên `hoadon.pay_id`).

Trong `dichvu`, dịch vụ mặc định gắn phòng có `booking_id = NULL`; dịch vụ được dùng trong một lần lưu trú có cả `phong_id` và `booking_id`. Trigger kiểm tra hai thông tin phòng phải khớp. Khi tạo Booking, Trigger sao chép dịch vụ mặc định của phòng sang Booking.

Giá mùa cao điểm được tính theo từng đêm lưu trú (ngày trả phòng không tính tiền). `booking` lưu snapshot gồm `tien_phong_du_kien`, `ap_dung_mua_cao_diem`, `chi_tiet_mua_cao_diem`; khi tạo Pay, Trigger sao chép snapshot sang `pay.tien_phong_ap_dung`, `pay.ap_dung_mua_cao_diem`, `pay.chi_tiet_mua_cao_diem`. Hóa đơn kiểm tra tiền phòng theo snapshot của Pay, không đọc lại cấu hình mùa cao điểm có thể đã bị thay đổi. Vì vậy, thay đổi hệ số sau khi Booking đã tạo chỉ ảnh hưởng Booking mới.

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

- Tables: 11 (8 bảng ERD + `users` + 2 bảng hỗ trợ QR/SePay).
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

Endpoint `/health/db` chỉ báo OK khi tìm thấy đủ 8 bảng ERD, 3 bảng hỗ trợ (`users`, `payment_qr`, `sepay_webhook_events`), 15 Trigger, 15 Stored Procedure và 10 View.

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
5. Kiểm tra giá dự kiến theo từng đêm; những đêm nằm trong `muacaodiem` được nhân hệ số đã cấu hình.
6. Lập hóa đơn/tính tiền theo snapshot Booking, hệ số mùa cao điểm và dịch vụ.
7. Cập nhật Pay sang `THANH_CONG` sau khi hóa đơn hợp lệ đã tồn tại.
8. Trả phòng; kiểm tra trạng thái phòng được đồng bộ.
9. Thử đặt trùng phòng, gắn dịch vụ sai phòng, sửa giao dịch sau khi tạo và xóa hóa đơn đã thanh toán; các thao tác trái quy tắc phải bị từ chối.

## 10. Lưu ý kiểm thử

Mã Python đã được kiểm tra cú pháp trong gói bàn giao. SQL cần được thực thi trên MySQL Server 8.0.16+ để xác nhận cú pháp/runtime của Trigger, Stored Procedure và View trong môi trường máy bạn. Tôi không đánh dấu SQL là đã chạy thành công trên MySQL khi chưa có kết nối tới MySQL Server thực tế.
## Cổng khách hàng (CUSTOMER)

Ứng dụng có hai không gian làm việc tách biệt theo role:

- `ADMIN`: giữ giao diện quản trị hiện tại.
- `CUSTOMER`: sau khi đăng nhập sẽ mở cổng khách hàng riêng, không nhìn thấy menu quản trị.

Khách hàng có thể tìm phòng trống theo ngày, gửi Booking, xem/hủy Booking của chính mình (theo điều kiện nghiệp vụ), xem chi tiết dịch vụ và hóa đơn, đồng thời tạo yêu cầu thanh toán. API lấy `khach_id` từ Bearer Token; không nhận `khach_id` từ payload khách gửi lên.

Các API CUSTOMER mới (đều yêu cầu role `CUSTOMER`):

- `GET /api/customer/me` – hồ sơ tài khoản hiện tại.
- `GET /api/customer/available-rooms?ngay_nhan=YYYY-MM-DD&ngay_tra=YYYY-MM-DD` – tra phòng trống kèm giá dự kiến và cờ mùa cao điểm.
- `GET /api/customer/rooms/{room_id}/price-preview?ngay_nhan=YYYY-MM-DD&ngay_tra=YYYY-MM-DD` – xem chi tiết giá từng đêm trước khi đặt.
- `POST /api/customer/bookings` – tạo Booking cho chính khách hàng đang đăng nhập.
- `GET /api/customer/bookings` và `GET /api/customer/bookings/{booking_id}` – lịch sử/chi tiết Booking của chính mình.
- `POST /api/customer/bookings/{booking_id}/cancel` – gửi yêu cầu hủy theo Stored Procedure.
- `POST /api/customer/bookings/{booking_id}/payment` – tạo Pay ở trạng thái `CHO_THANH_TOAN` và hóa đơn.
- `GET /api/customer/invoices` – chỉ xem hóa đơn của chính khách hàng.
- `GET /api/customer/payments/{pay_id}/qr` và `GET /api/customer/payments/{pay_id}/status` – lấy QR / theo dõi Pay của chính khách hàng.

**Thanh toán QR:** Khi chọn `CHUYEN_KHOAN`, hệ thống tạo Pay + hóa đơn theo Stored Procedure hiện có, sau đó hiển thị QR VietQR với số tiền và nội dung riêng `HTL{PayID}`. Khách không thể tự đánh dấu đã thanh toán. Server chỉ chuyển `pay.status` sang `THANH_CONG` khi nhận webhook SePay đã xác thực, đúng tài khoản nhận, đúng mã thanh toán và đúng số tiền. `TIEN_MAT`/`THE` tiếp tục cần ADMIN xác nhận. Các webhook đều được lưu để đối soát; trùng `transaction_id` không được xử lý lần hai.

## 10. Cổng thanh toán QR VietQR + SePay

### 10.1. Cấu hình tài khoản nhận tiền

Sao chép `.env.example` thành `.env` và điền thông tin tài khoản nhận tiền thật:

```dotenv
PAYMENT_BANK_CODE=Vietcombank
PAYMENT_BANK_ACCOUNT=0123456789
PAYMENT_ACCOUNT_NAME=TEN CHU TAI KHOAN
PAYMENT_QR_IMAGE_URL=https://vietqr.app/img

SEPAY_WEBHOOK_AUTH_MODE=HMAC_SHA256
SEPAY_WEBHOOK_SECRET=secret_key_tao_trong_sepay
SEPAY_WEBHOOK_ACCOUNT_NUMBER=0123456789
```

`PAYMENT_BANK_CODE` phải là mã ngân hàng mà VietQR hỗ trợ (ví dụ `Vietcombank`); `PAYMENT_BANK_ACCOUNT` là số tài khoản nhận tiền. Không đưa `.env` lên Git. Khi chưa điền đủ ba thông tin ngân hàng, API sẽ từ chối tạo thanh toán QR thay vì hiển thị QR giả.

### 10.2. Cấu hình SePay

1. Đăng ký/đăng nhập <https://my.sepay.vn/> và liên kết đúng tài khoản ngân hàng nhận tiền.
2. Cấu hình cấu trúc mã thanh toán để SePay nhận diện mã bắt đầu bằng `HTL` (mỗi Pay tạo mã duy nhất như `HTL00000015`).
3. Tạo Webhook, chọn sự kiện **Có tiền vào / In_only**, định dạng **JSON**, phương thức xác thực **HMAC-SHA256**.
4. URL webhook: `https://TEN-MIEN-CONG-KHAI/api/webhooks/sepay`.
5. Sao chép Secret Key vào `SEPAY_WEBHOOK_SECRET`; đặt `SEPAY_WEBHOOK_ACCOUNT_NUMBER` đúng số tài khoản nhận tiền.
6. Khởi động lại FastAPI sau khi sửa `.env`.

SePay phải gọi được URL từ Internet. Khi chạy demo trên máy cá nhân, dùng HTTPS tunnel (ví dụ ngrok/Cloudflare Tunnel) trỏ về cổng 8000; không nhập `localhost` hoặc `127.0.0.1` làm Webhook URL. Dùng HTTPS khi triển khai thật. API cũng hỗ trợ `SEPAY_WEBHOOK_AUTH_MODE=API_KEY` cùng `SEPAY_WEBHOOK_API_KEY` nếu cấu hình webhook bằng API Key, nhưng HMAC-SHA256 được khuyến nghị.

### 10.3. Luồng hoạt động và kiểm tra

1. CUSTOMER chọn phương thức `CHUYEN_KHOAN` và gửi yêu cầu thanh toán cho Booking đã được xác nhận.
2. API gọi Stored Procedure tạo Pay + hóa đơn, tạo mã chuyển khoản HTL duy nhất và trả QR VietQR.
3. Giao diện hiển thị QR, ngân hàng, số tài khoản, chủ tài khoản, số tiền và nội dung chuyển khoản; tự hỏi API trạng thái mỗi 3 giây.
4. Khách quét QR bằng ứng dụng ngân hàng. Không thay đổi số tiền hoặc nội dung chuyển khoản.
5. SePay POST webhook. API xác minh HMAC/timestamp (hoặc API Key), chống webhook lặp, kiểm tra chiều tiền vào, tài khoản nhận, mã Pay, trạng thái Booking và số tiền hóa đơn.
6. Chỉ giao dịch khớp chính xác mới UPDATE `pay.status='THANH_CONG'`. Trigger `trg_pay_before_update` tiếp tục kiểm tra hóa đơn và Trigger `trg_pay_after_update` đồng bộ Booking theo quy tắc hiện tại.
7. ADMIN mở **Quản lý thanh toán → Nhật ký giao dịch QR (SePay)** để xem webhook khớp, không khớp hoặc sai số tiền.

Webhook endpoint công khai (tự xác thực, không dùng Bearer Token): `POST /api/webhooks/sepay`. Endpoint CUSTOMER yêu cầu Bearer Token: `GET /api/customer/payments/{pay_id}/qr` và `GET /api/customer/payments/{pay_id}/status`.

**Giới hạn bảo vệ:** phiên bản này hỗ trợ một lần chuyển khoản đúng toàn bộ số tiền cho mỗi Pay. Chuyển thiếu/thừa, sai tài khoản, sai mã hoặc Booking đã hủy sẽ được ghi nhật ký nhưng không tự xác nhận; ADMIN cần đối soát thủ công với ngân hàng. QR VietQR chỉ tạo chỉ dẫn chuyển khoản, việc xác nhận tự động phụ thuộc webhook SePay được cấu hình và có thể truy cập công khai.

## 11. Cập nhật QR cho database đã tồn tại

Nếu database đã có dữ liệu, không chạy lại `Hotel_Table.sql` hoặc `Hotel_Complete.sql`. Hãy sao lưu database, sau đó chạy một lần `Hotel_QR_Payment_Migration.sql` trên database `hotel_management_erd`. File này chỉ tạo hai bảng hỗ trợ QR/webhook, không DROP hay sửa dữ liệu Booking/Pay/HoaDon.

Nếu database hiện tại chưa có snapshot mùa cao điểm, chạy tiếp `Hotel_Peak_Season_Migration.sql` theo hướng dẫn bên dưới. Nếu đã chạy migration mùa cao điểm rồi thì không cần chạy lại.

## 12. Cập nhật mùa cao điểm cho database đang có dữ liệu

Nếu database đã được tạo từ phiên bản trước, không chạy lại `Hotel_Table.sql` hoặc `Hotel_Complete.sql` vì hai file này tạo lại database. Hãy sao lưu và chạy một lần `Hotel_Peak_Season_Migration.sql` trên đúng database trong `.env` (`DB_NAME`). Sau đó khởi động lại API và GUI. File migration bổ sung snapshot cho `booking` và `pay`, backfill các bản ghi cũ, rồi cập nhật Trigger/Stored Procedure liên quan.

`Hotel_Complete.sql` và bộ SQL module rời (`Hotel_Table.sql`, `Hotel_InsertData.sql`, `Hotel_Procedures.sql`, `Hotel_Trigger.sql`, `Hotel_Report.sql`) đã được đồng bộ để dùng cho cài mới.
