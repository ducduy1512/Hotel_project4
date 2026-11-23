# HOTEL MANAGEMENT SYSTEM

Dự án quản lý khách sạn dùng **MySQL + FastAPI REST API + giao diện Web HTML5/CSS/JavaScript**. Trình duyệt gọi các endpoint REST hiện có; API tiếp tục chịu trách nhiệm nghiệp vụ và kết nối MySQL. Lớp giao diện được thay mới, không thay đổi cấu trúc SQL, dataset hoặc quy tắc nghiệp vụ.

## 1. Công nghệ và phiên bản

- Python 3.10+
- MySQL Server 8.0.16+ (để thực thi CHECK constraint)
- MySQL Workbench
- FastAPI + Uvicorn
- HTML5, CSS3 và JavaScript thuần (chạy trên trình duyệt)
- mysql-connector-python, python-dotenv

## 2. Cấu trúc dự án

```text
Hotel_project5/
├── Hotel_Table.sql          # Tạo database, 8 bảng ERD và 3 bảng hỗ trợ
├── Hotel_InsertData.sql     # Dữ liệu mẫu (nạp trước Trigger để giữ lịch sử)
├── Hotel_Procedures.sql     # 18 Stored Procedures
├── Hotel_Trigger.sql        # 15 Trigger kiểm soát nghiệp vụ
├── Hotel_Report.sql         # 10 View phục vụ báo cáo/giao diện
├── Hotel_Paid_Service_Catalog_Migration.sql # Nâng cấp danh mục dịch vụ bổ sung tính phí cho DB hiện hữu
├── HUONG_DAN_DICH_VU_BO_SUNG_TINH_PHI.md # Danh mục, quy tắc tính số lượng và hướng dẫn migration
├── Hotel_Six_Issues_Fix.sql # Đồng bộ 6 lỗi SQL/API cho DB dump hiện hữu
├── SIX_ISSUES_FIX_README.txt # Hướng dẫn chạy script hòa giải
├── Hotel_TestCase.sql       # Kiểm tra đối tượng, toàn vẹn và test âm
├── Hotel_Complete.sql       # Bản SQL tổng hợp một file (thay cho 5 file trên)
├── .env.example             # Mẫu cấu hình máy cá nhân
├── app.py                   # Khởi động FastAPI/Web GUI từ PyCharm
├── api_client.py            # HTTP client dùng chung, tự gửi Bearer Token
├── database.py              # Cấu hình kết nối MySQL từ .env
├── api/                     # FastAPI REST API
│   ├── qr_payment_service.py # Sinh mã nội dung + URL QR VietQR
│   ├── main.py
│   ├── database.py
│   ├── dependencies.py
│   ├── schemas.py
│   └── routers/              # auth, customers, rooms, bookings, payments, payment_gateway...
├── frontend/                # Giao diện Web HTML/CSS/JavaScript
│   ├── index.html
│   ├── styles.css
│   └── app.js
├── pages/                   # Mã GUI Tkinter cũ (không còn là giao diện khởi chạy)
├── images/                  # Tài nguyên hình ảnh hiện có
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

Trong `dichvu`, dịch vụ mặc định miễn phí có `loai_dichvu = 'MAC_DINH'`, gắn `phong_id` và có giá 0; danh mục dịch vụ bổ sung tính phí có `loai_dichvu = 'TUY_CHON'`, `phong_id = NULL`, `booking_id = NULL`; dịch vụ được chọn sẽ được sao chép thành snapshot với `booking_id` và `phong_id` của Booking. Tên, giá, nhóm và đơn vị tính tại thời điểm chọn được giữ trong Booking. Giường phụ lưu số giường-đêm (số giường mỗi đêm × số đêm). Danh mục bị ngừng cung cấp chỉ đặt `dang_hoat_dong = 0`, không xóa các snapshot lịch sử.

Giá mùa cao điểm được tính theo từng đêm lưu trú (ngày trả phòng không tính tiền) như **phụ phí cộng thêm**, không nhân lại tiền phòng. `muacaodiem.he_so_gia` chỉ nhận các mức `0.6`, `0.5`, `0.4`, `0.3`, `0.2`, `0.1`. Phụ phí mỗi đêm = giá phòng cơ bản mỗi đêm × hệ số. `booking` lưu riêng `tien_phong_du_kien` (tiền phòng cơ bản), `tien_phu_phi_mua_cao_diem` và snapshot chi tiết; khi tạo Pay, Trigger sao chép toàn bộ snapshot sang `pay`. Hóa đơn có ba khoản riêng: `tien_phong`, `tien_phu_phi_mua_cao_diem`, `tien_dich_vu`; bắt buộc `tong_tien = tien_phong + tien_phu_phi_mua_cao_diem + tien_dich_vu`. Ví dụ: 1.000.000 + 200.000 (+0.2) + 50.000 = **1.250.000 VNĐ**. Thay đổi cấu hình sau khi Booking đã tạo chỉ ảnh hưởng Booking mới.


## Danh mục dịch vụ bổ sung tính phí

- Khi nâng cấp database hiện tại từ dump cũ, hãy sao lưu database rồi chạy **một lần** `Hotel_Paid_Service_Catalog_Migration.sql` trong MySQL Workbench. File này thêm các thuộc tính phân loại vào bảng `dichvu`, chuyển đổi các trigger/Stored Procedure liên quan, và tạo 13 lựa chọn dịch vụ mẫu.
- Khi cài mới hoàn toàn, chạy `Hotel_Complete.sql` hoặc các file `Hotel_Table.sql`, `Hotel_InsertData.sql`, `Hotel_Procedures.sql`, `Hotel_Trigger.sql`, `Hotel_Report.sql` theo thứ tự hướng dẫn. Không chạy migration sau khi đã dùng schema mới trong `Hotel_Complete.sql`.
- Admin quản lý danh mục chung tại **Dịch vụ**. Dịch vụ bổ sung không gắn Phòng/Booking; dịch vụ mặc định phải gắn phòng và có giá 0. Ngừng kinh doanh bằng cách đặt trạng thái danh mục thành “Ngừng cung cấp”.
- Customer chọn dịch vụ bổ sung ở bước đặt phòng. Các lựa chọn có checkbox mặc định bỏ trống. Chỉ dịch vụ đã tích chọn mới vào tổng tiền dịch vụ và hóa đơn.
- Danh mục mẫu gồm 13 lựa chọn: buffet 100.000đ/suất/buổi; giường phụ 300.000đ/giường-đêm; giặt ủi 25.000đ/món, 30.000đ/áo sơ mi, 80.000đ/bộ vest/đầm; minibar 25.000đ/lon nước ngọt, 35.000đ/chai nước trái cây, 30.000đ/gói snack, 45.000đ/thanh chocolate; đưa đón sân bay 650.000đ/chuyến một chiều hoặc 1.200.000đ/chuyến khứ hồi; trang trí sinh nhật 500.000đ/gói hoặc Honeymoon 750.000đ/gói. Đây là giá demo có thể sửa trong Admin.
- Với giường phụ, Customer nhập số giường mỗi đêm; Booking lưu số giường-đêm = số giường mỗi đêm × số đêm. Với buffet, số lượng là số suất ăn, không tự nhân theo số đêm.

## 4. Cài đặt SQL bằng MySQL Workbench

**Cài mới – chạy lần lượt 6 file SQL:**

1. Mở MySQL Workbench và kết nối MySQL Server.
2. Mở, chạy toàn bộ `Hotel_Table.sql`.
3. Chạy `Hotel_InsertData.sql`.
4. Chạy `Hotel_Procedures.sql`.
5. Chạy `Hotel_Trigger.sql`.
6. Chạy `Hotel_Report.sql`.
7. Chạy `Hotel_TestCase.sql` để kiểm tra kết quả.

Có thể thay bước 2–6 bằng một lần chạy `Hotel_Complete.sql`; sau đó chạy `Hotel_TestCase.sql`. **Không chạy `Hotel_Complete.sql` cùng với các file rời**, vì đó là hai cách cài đặt thay thế nhau.

`Hotel_Six_Issues_Fix.sql` không phải file bắt buộc cho cài mới. Đây là script hòa giải dành cho database hiện hữu đã xuất trong `hotel_management_full(2).sql`; cần sao lưu trước khi chạy. Script có cập nhật snapshot mẫu theo Booking #7, #12 và xử lý snapshot rỗng Booking #19, nên không dùng nguyên trạng cho database có bộ dữ liệu khác.

> **CẢNH BÁO DỮ LIỆU:** `Hotel_Table.sql` và `Hotel_Complete.sql` có `DROP DATABASE IF EXISTS hotel_management_erd`. Việc chạy sẽ xóa và tạo lại database này. Hãy sao lưu database đang có trước khi chạy.

Dữ liệu mẫu được nạp trước khi tạo Trigger để không áp các quy tắc giao dịch hiện tại lên các bản ghi lịch sử. Riêng hóa đơn của giao dịch hoàn tiền mẫu Pay #11 đã được bổ sung; giao dịch thất bại Pay #10 không có hóa đơn.

### Kết quả cấu trúc mong đợi trong Workbench

- Tables: 11 (8 bảng ERD + `users` + 2 bảng hỗ trợ QR/SePay).
- Triggers: 15.
- Stored Procedures: 18.
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

Nếu máy đã nhận lệnh `python`, có thể thay `py` bằng `python`. Nếu cả `py` và `python` đều không được nhận diện, hãy cài Python từ python.org, chọn **Add Python to PATH**, sau đó mở lại PyCharm/Terminal. Giao diện Web chạy trong trình duyệt, không cần cài Tkinter.

## 7. Chạy dự án trong PyCharm

**Khởi động ứng dụng (Backend + Web GUI):**

```powershell
py app.py
```

Ứng dụng sẽ khởi động FastAPI trong cửa sổ Run. Giữ cửa sổ này mở và truy cập `http://127.0.0.1:8000/` bằng Chrome hoặc Edge. Có thể chạy trực tiếp bằng `py -m uvicorn api.main:app --host 127.0.0.1 --port 8000`.

Tài liệu API: http://127.0.0.1:8000/docs

API health: http://127.0.0.1:8000/health

Kiểm tra đầy đủ database/object: http://127.0.0.1:8000/health/db

Endpoint `/health/db` chỉ báo OK khi tìm thấy đủ 8 bảng ERD, 3 bảng hỗ trợ (`users`, `payment_qr`, `sepay_webhook_events`), 15 Trigger, 18 Stored Procedure và 10 View.

## 8. Tài khoản và phân quyền

Sau khi chạy SQL mẫu:

- Username: `admin`
- Password: `Admin@123`
- Role: `ADMIN`

Đổi mật khẩu quản trị trước khi sử dụng thật. API đăng ký công khai luôn tạo `CUSTOMER`. Khi đăng nhập, ADMIN vào giao diện quản trị Web; CUSTOMER được chuyển sang Cổng khách hàng Web riêng. Các router quản lý khách, phòng, Booking, dịch vụ, thanh toán, hóa đơn và báo cáo yêu cầu Bearer Token của ADMIN. Router `/api/customer/*` yêu cầu Bearer Token của CUSTOMER và lọc dữ liệu theo hồ sơ khách hàng gắn với tài khoản. Frontend lưu Bearer Token trong localStorage của trình duyệt và tự đính kèm token cho các request API cần xác thực.

## 9. Luồng nghiệp vụ cần kiểm thử

1. Tạo khách hàng và phòng (nếu không dùng dữ liệu mẫu).
2. Kiểm tra phòng trống theo ngày.
3. Tạo Booking và xác nhận Booking.
4. Nhận phòng, thêm dịch vụ.
5. Kiểm tra giá dự kiến theo từng đêm; mỗi đêm thuộc `muacaodiem` cộng phụ phí = giá phòng cơ bản × hệ số 0.1–0.6.
6. Lập hóa đơn/tính tiền từ snapshot Booking theo công thức: tiền phòng cơ bản + phụ phí mùa cao điểm + tiền dịch vụ.
7. Cập nhật Pay sang `THANH_CONG` sau khi hóa đơn hợp lệ đã tồn tại.
8. Trả phòng; kiểm tra trạng thái phòng được đồng bộ.
9. Thử đặt trùng phòng, gắn dịch vụ sai phòng, sửa giao dịch sau khi tạo và xóa hóa đơn đã thanh toán; các thao tác trái quy tắc phải bị từ chối.

## 10. Lưu ý kiểm thử

Mã Python đã được kiểm tra cú pháp trong gói bàn giao. SQL cần được thực thi trên MySQL Server 8.0.16+ để xác nhận cú pháp/runtime của Trigger, Stored Procedure và View trong môi trường máy bạn. Tôi không đánh dấu SQL là đã chạy thành công trên MySQL khi chưa có kết nối tới MySQL Server thực tế.
## Cổng khách hàng (CUSTOMER)

Ứng dụng có hai không gian làm việc tách biệt theo role:

- `ADMIN`: giao diện quản trị Web HTML5.
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
PAYMENT_BANK_ACCOUNT=YOUR_BANK_ACCOUNT_NUMBER
PAYMENT_ACCOUNT_NAME=YOUR_ACCOUNT_NAME
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
3. Giao diện Web hiển thị QR, ngân hàng, số tài khoản, chủ tài khoản, số tiền và nội dung chuyển khoản; khách có thể yêu cầu kiểm tra trạng thái từ giao diện.
4. Khách quét QR bằng ứng dụng ngân hàng. Không thay đổi số tiền hoặc nội dung chuyển khoản.
5. SePay POST webhook. API xác minh HMAC/timestamp (hoặc API Key), chống webhook lặp, kiểm tra chiều tiền vào, tài khoản nhận, mã Pay, trạng thái Booking và số tiền hóa đơn.
6. Chỉ giao dịch khớp chính xác mới UPDATE `pay.status='THANH_CONG'`. Trigger `trg_pay_before_update` tiếp tục kiểm tra hóa đơn và Trigger `trg_pay_after_update` đồng bộ Booking theo quy tắc hiện tại.
7. ADMIN mở **Quản lý thanh toán → Nhật ký giao dịch QR (SePay)** để xem webhook khớp, không khớp hoặc sai số tiền.

Webhook endpoint công khai (tự xác thực, không dùng Bearer Token): `POST /api/webhooks/sepay`. Endpoint CUSTOMER yêu cầu Bearer Token: `GET /api/customer/payments/{pay_id}/qr` và `GET /api/customer/payments/{pay_id}/status`.

**Giới hạn bảo vệ:** phiên bản này hỗ trợ một lần chuyển khoản đúng toàn bộ số tiền cho mỗi Pay. Chuyển thiếu/thừa, sai tài khoản, sai mã hoặc Booking đã hủy sẽ được ghi nhật ký nhưng không tự xác nhận; ADMIN cần đối soát thủ công với ngân hàng. QR VietQR chỉ tạo chỉ dẫn chuyển khoản, việc xác nhận tự động phụ thuộc webhook SePay được cấu hình và có thể truy cập công khai.

## 11. Cập nhật database đã tồn tại

Nếu database đã có dữ liệu, **không chạy lại** `Hotel_Table.sql` hoặc `Hotel_Complete.sql` vì hai file sẽ DROP và tạo lại database.

Với database `hotel_management_erd` được xuất từ file dump `hotel_management_full(1).sql` bạn vừa gửi, hãy sao lưu database trước, sau đó chạy **một lần** `Hotel_Paid_Service_Catalog_Migration.sql`. Migration này chỉ nâng cấp bảng `dichvu`, phân loại các dòng dịch vụ hiện có, thêm 13 mục dịch vụ bổ sung tính phí và cập nhật Trigger/Stored Procedure phục vụ chọn dịch vụ. Không cần import lại dump và không cần chạy `Hotel_Complete.sql`.

Migration có lệnh `ALTER TABLE ADD COLUMN`, vì vậy **không chạy lần thứ hai** trên cùng database. Nếu MySQL báo một trong bốn cột `loai_dichvu`, `nhom_dich_vu`, `don_vi_tinh`, `dang_hoat_dong` đã tồn tại, hãy dừng và kiểm tra schema trước khi chạy tiếp; không xóa cột hoặc chạy lại tùy tiện.

Với database cài mới hoàn toàn, dùng `Hotel_Complete.sql` hoặc bộ SQL rời theo thứ tự tại mục cài đặt. Các bản cài mới đã có sẵn cấu trúc dịch vụ và 13 mục mẫu, **không chạy migration** trên các bản này.

Sau khi migration hoàn tất, chạy `Hotel_TestCase.sql`. Các kiểm tra mới gồm sự hiện diện của ít nhất 13 mục danh mục mẫu, cấu trúc hợp lệ của dịch vụ mặc định, danh mục chung và snapshot Booking.

### Quy tắc tính tiền dịch vụ

- Dịch vụ mặc định có giá 0đ và không làm tăng hóa đơn.
- Dịch vụ bổ sung chỉ được sao chép vào Booking nếu Customer tích chọn.
- Giá/tên/đơn vị tính được chốt trong bản ghi Booking; thay đổi danh mục không sửa Booking cũ.
- Giường phụ nhập số giường mỗi đêm, lưu thành giường-đêm = số giường × số đêm. Buffet tính theo số suất/buổi, không tự nhân theo số đêm.
- Pay và hóa đơn tiếp tục cộng `don_gia * so_luong` từ các dòng dịch vụ của Booking; không thay đổi snapshot tiền phòng và phụ phí mùa cao điểm.

Không tự sửa `tien_phong`, `tien_phu_phi_mua_cao_diem`, `tien_dich_vu`, `tong_tien` trực tiếp trên hóa đơn đã tạo. Trigger kiểm tra từng khoản theo snapshot Pay/Booking và dịch vụ đã chốt để ngăn hóa đơn lệch.


## Mùa cao điểm áp dụng toàn bộ phòng và xem giá trước Booking

- Quản trị viên dùng nút **Tạo mùa cho tất cả phòng** để khai báo một khoảng ngày cao điểm trong một lần.
- Hệ thống tạo một dòng `muacaodiem` cho từng phòng và vẫn giữ `muacaodiem.phong_id` làm khóa ngoại tới `phong.id`. Có thể đặt tỷ lệ phụ thu khác nhau theo từng phòng trong cùng khoảng ngày.
- Nếu một phòng đã có mùa cao điểm giao với khoảng ngày mới, toàn bộ thao tác bị từ chối để tránh dữ liệu chồng lấn hoặc chọn nhầm mức phụ thu.
- Khi khách chọn ngày nhận/trả và tìm phòng, API tính giá theo từng đêm, đúng `phong_id`, sau đó giao diện hiển thị tiền phòng, tỷ lệ phụ thu và số tiền phụ thu trước khi khách xác nhận Booking.
- Khi Booking được tạo, Trigger/Stored Procedure của cơ sở dữ liệu tiếp tục tạo snapshot theo phòng và từng ngày; các hóa đơn cũ không bị tính lại.

**Cập nhật cơ sở dữ liệu:** Không cần migration mới cho thay đổi này. Bảng `muacaodiem` đã có `phong_id` và FK tới `phong`; bản cập nhật dùng quan hệ hiện tại, chỉ bổ sung API tạo nhiều dòng có kiểm tra trùng ngày.


## Peak-season relationship (N:N)

The database now models `PHONG` and `MUACAODIEM` as many-to-many through
`PHONG_MUACAODIEM`. `MUACAODIEM` stores one shared date range; the junction
table stores `phong_id`, `muacaodiem_id`, and the room-specific `he_so_phu_thu`.
This lets one season apply to many rooms while each room retains its own rate.

For an existing 1:N database, back up `hotel_management_erd`, stop the API,
run `Hotel_Peak_Season_NN_Migration.sql`, then run `Hotel_Procedures.sql`,
`Hotel_Trigger.sql`, and `Hotel_Report.sql` in that order. Restart the API only
after all four scripts complete successfully. The migration preserves Booking,
Pay and invoice snapshot JSON and does not recalculate historical totals.

The current sample season (2026-12-20 through 2026-12-31) uses 20% for rooms
all physical rooms inherit the surcharge for their assigned room type: Standard 20%, Deluxe 25%, VIP 30%, Family 35%.
