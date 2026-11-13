# H HOTEL MANAGEMENT SYSTEM

## 1. Giới thiệu dự án

H Hotel Management System là ứng dụng quản lý khách sạn được xây dựng bằng Python, sử dụng giao diện Tkinter và cơ sở dữ liệu MySQL.

Hệ thống hỗ trợ quản lý thông tin khách hàng, phòng, đặt phòng, dịch vụ, thanh toán, hóa đơn và báo cáo doanh thu.

## 2. Công nghệ sử dụng

- **Ngôn ngữ lập trình:** Python
- **Giao diện:** Tkinter
- **Cơ sở dữ liệu:** MySQL
- **Kết nối cơ sở dữ liệu:** mysql-connector-python
- **Công cụ phát triển:** PyCharm, MySQL Workbench

## 3. Các chức năng chính

1. Tổng quan: hiển thị thông tin và tình hình hoạt động khách sạn.
2. Khách hàng: thêm, sửa, xóa và tìm kiếm khách hàng.
3. Quản lý phòng: quản lý thông tin và trạng thái phòng.
4. Loại phòng: quản lý loại phòng, giá và sức chứa.
5. Đặt phòng: tạo, tìm kiếm và hủy booking.
6. Mùa cao điểm: quản lý thời gian và hệ số giá.
7. Dịch vụ: quản lý các dịch vụ đi kèm booking.
8. Thanh toán: theo dõi và cập nhật trạng thái thanh toán.
9. Hóa đơn: xem thông tin và chi tiết hóa đơn.
10. Báo cáo: thống kê doanh thu, đặt phòng, khách hàng và hiệu suất phòng.

## 4. Cấu trúc dự án

```text
WelcomeScreen/
├── images/
├── pages/
│   ├── dashboard.py
│   ├── customers.py
│   ├── rooms.py
│   ├── room_types.py
│   ├── bookings.py
│   ├── peak_seasons.py
│   ├── services.py
│   ├── payments.py
│   ├── invoices.py
│   └── reports.py
├── app.py
├── database.py
├── requirements.txt
├── README.md
└── .gitignore
```

## 5. Cài đặt và chạy chương trình

### Bước 1: Cài đặt Python

Cài đặt Python và PyCharm trên máy tính.

### Bước 2: Cài đặt MySQL

Cài đặt MySQL Server và MySQL Workbench.

### Bước 3: Chuẩn bị cơ sở dữ liệu

Tạo và cấu hình database `hotel_management` trong MySQL Workbench.

### Bước 4: Cài đặt thư viện

Mở Terminal tại thư mục dự án và chạy:

```bash
pip install -r requirements.txt
```

### Bước 5: Cấu hình kết nối

Mở file `database.py` và kiểm tra thông tin kết nối MySQL phù hợp với máy tính đang sử dụng.

### Bước 6: Khởi chạy ứng dụng

Chạy file:

```bash
python app.py
```

## 6. Kết quả

Ứng dụng cung cấp giao diện quản lý khách sạn tập trung, hỗ trợ các nghiệp vụ quản lý phòng, khách hàng, đặt phòng, dịch vụ, thanh toán, hóa đơn và báo cáo.