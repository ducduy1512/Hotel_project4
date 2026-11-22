# HƯỚNG DẪN DANH MỤC DỊCH VỤ BỔ SUNG TÍNH PHÍ

## 1. Mục tiêu

Bổ sung danh mục dịch vụ tính phí dùng chung cho mọi loại phòng, do ADMIN quản lý và CUSTOMER chủ động chọn ở bước đặt phòng. Không tạo bảng nghiệp vụ thứ 9; phần mở rộng nằm trong bảng `dichvu` hiện có.

## 2. 13 mục dịch vụ được nạp ban đầu

| Nhóm | Dịch vụ | Giá demo | Đơn vị tính |
|---|---|---:|---|
| Ăn sáng | Ăn sáng buffet | 100.000đ | Suất/buổi |
| Giường phụ | Giường phụ | 300.000đ | Giường/đêm |
| Giặt ủi | Giặt ủi quần áo thường | 25.000đ | Món |
| Giặt ủi | Giặt ủi áo sơ mi | 30.000đ | Áo |
| Giặt ủi | Giặt ủi vest/đầm | 80.000đ | Bộ |
| Minibar | Nước ngọt | 25.000đ | Lon |
| Minibar | Nước trái cây | 35.000đ | Chai |
| Minibar | Snack | 30.000đ | Gói |
| Minibar | Chocolate | 45.000đ | Thanh |
| Đưa đón | Đưa đón sân bay một chiều | 650.000đ | Chuyến |
| Đưa đón | Đưa đón sân bay khứ hồi | 1.200.000đ | Chuyến |
| Trang trí | Trang trí sinh nhật cơ bản | 500.000đ | Gói |
| Trang trí | Trang trí kỷ niệm / Honeymoon | 750.000đ | Gói |

Đây là giá mẫu để trình diễn và kiểm thử; ADMIN có thể chỉnh sửa. Khách chỉ bị tính tiền với các mục đã tích chọn.

## 3. Quy tắc lưu dữ liệu

Bảng `dichvu` có thêm bốn cột:

- `loai_dichvu`: `MAC_DINH` hoặc `TUY_CHON`.
- `nhom_dich_vu`: mã nhóm như `AN_SANG`, `GIAT_UI`, `MINIBAR`.
- `don_vi_tinh`: `suất/buổi`, `giường/đêm`, `món`, `chuyến`, `gói`...
- `dang_hoat_dong`: 1 đang kinh doanh, 0 ngừng cung cấp.

Ba dạng bản ghi:

1. Dịch vụ mặc định miễn phí: `MAC_DINH`, có `phong_id`, `booking_id IS NULL`, `don_gia = 0`.
2. Mục danh mục tính phí dùng chung: `TUY_CHON`, `phong_id IS NULL`, `booking_id IS NULL`, `don_gia > 0`.
3. Dịch vụ đã được chọn: có `booking_id` và `phong_id`; tên, giá, nhóm và đơn vị tính được sao chép thành snapshot tại thời điểm đặt.

## 4. Quy tắc tính số lượng

- Buffet: CUSTOMER nhập số suất ăn. Giá tính theo số suất, không tự nhân số đêm.
- Giường phụ: CUSTOMER nhập số giường mỗi đêm. Stored Procedure lưu `số giường × số đêm` thành số giường-đêm; ví dụ 2 giường trong 3 đêm = 6 giường-đêm = 1.800.000đ.
- Giặt ủi, minibar, đưa đón, trang trí: tính theo đơn vị và số lượng khách chọn.
- Dịch vụ mặc định có giá 0đ nên không làm tăng tiền dịch vụ.

## 5. Cài đặt trên database hiện tại

1. Export/backup database `hotel_management_erd` trước khi thay đổi.
2. Mở `Hotel_Paid_Service_Catalog_Migration.sql` trong MySQL Workbench và chạy toàn bộ một lần.
3. Kiểm tra danh mục bằng câu lệnh:

```sql
SELECT id, ten, don_gia, nhom_dich_vu, don_vi_tinh, dang_hoat_dong
FROM dichvu
WHERE loai_dichvu = 'TUY_CHON'
  AND phong_id IS NULL AND booking_id IS NULL
ORDER BY nhom_dich_vu, ten;
```

4. Chạy `Hotel_TestCase.sql` và kiểm tra các test `PAID_OPTIONAL_CATALOG_COUNT`, `INVALID_ROOM_DEFAULT_SERVICE`, `INVALID_GLOBAL_PAID_SERVICE`, `INVALID_BOOKING_SERVICE_TYPE_PRICE`.
5. Khởi động lại `app.py`, đăng nhập ADMIN → **Dịch vụ** để chỉnh giá/trạng thái; đăng nhập CUSTOMER để thử chọn dịch vụ.

**Chỉ chạy migration này một lần** trên database cũ. Không chạy `Hotel_Table.sql` hoặc `Hotel_Complete.sql` trên database có dữ liệu vì hai file cài mới sẽ tạo lại database. Các bản cài mới đã dùng `Hotel_Complete.sql` hoặc bộ SQL rời mới thì không cần chạy migration.

## 6. Pay, hóa đơn và lịch sử

Các Trigger hiện tại của `pay` và `hoadon` tiếp tục tính tổng dịch vụ từ `SUM(don_gia * so_luong)` của các dòng dịch vụ gắn Booking. Dịch vụ bổ sung chỉ được sao chép vào Booking khi khách chọn. Thay đổi giá hoặc ngừng kinh doanh ở danh mục không sửa các snapshot đã gắn Booking và không làm thay đổi hóa đơn cũ.
