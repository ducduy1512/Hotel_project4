# Cập nhật tính tiền mùa cao điểm

## Quy tắc tính tiền

- Mỗi đêm lưu trú được tính riêng: `giá cơ bản/đêm × hệ số mùa cao điểm của đúng ngày đó`.
- Ngày nhận phòng được tính; ngày trả phòng không tính tiền.
- Nếu Booking chỉ nằm trong mùa cao điểm một phần, chỉ những đêm thuộc khoảng `tu_ngay` đến `den_ngay` (bao gồm hai đầu) mới nhân hệ số.
- Ví dụ: giá cơ bản 1.000.000 VNĐ/đêm, hệ số 1,5 áp dụng từ 20/12 đến 24/12. Booking 19/12–22/12 có 3 đêm: 1.000.000 + 1.500.000 + 1.500.000 = 4.000.000 VNĐ tiền phòng.

## Đồng bộ dữ liệu

Không thêm bảng mới; vẫn giữ ERD 8 bảng hiện tại.

- `booking.tien_phong_du_kien`: tiền phòng đã tính khi tạo Booking.
- `booking.ap_dung_mua_cao_diem`: đánh dấu Booking có ít nhất một đêm áp dụng mùa cao điểm.
- `booking.chi_tiet_mua_cao_diem`: JSON chi tiết từng đêm, mã mùa cao điểm, hệ số và tiền đêm.
- `pay.tien_phong_ap_dung`, `pay.ap_dung_mua_cao_diem`, `pay.chi_tiet_mua_cao_diem`: bản sao bất biến từ Booking tại thời điểm tạo Pay.
- `hoadon.tien_phong`, `tien_dich_vu`, `tong_tien` được kiểm tra với Pay snapshot và các dịch vụ của Booking.

Khi cấu hình mùa cao điểm thay đổi sau khi Booking đã được tạo, giá Booking cũ không tự thay đổi. Booking mới sẽ dùng cấu hình mới. Khi đổi ngày/phòng của Booking chưa có Pay, trigger tính lại snapshot. Khi đã có Pay, không cho đổi ngày/phòng để tránh làm sai lệch giao dịch.

## Cài đặt vào database hiện có

1. Sao lưu database trước khi chạy SQL.
2. Mở MySQL Workbench hoặc terminal MySQL, chọn đúng database mà API đang dùng trong `.env` (`DB_NAME`).
3. Chạy toàn bộ file `Hotel_Peak_Season_Migration.sql` một lần.
4. Khởi động lại API và ứng dụng Tkinter.
5. Kiểm tra các cột mới:

```sql
SELECT id, ngay_nhan, ngay_tra, tien_phong_du_kien,
       ap_dung_mua_cao_diem, chi_tiet_mua_cao_diem
FROM booking;

SELECT id, booking_id, so_tien, tien_phong_ap_dung,
       ap_dung_mua_cao_diem, chi_tiet_mua_cao_diem
FROM pay;
```

**Quan trọng:** `Hotel_Complete.sql` là script cài đặt lại database từ đầu và có lệnh `DROP DATABASE`. Nếu đang có dữ liệu cần giữ, chỉ chạy file migration ở trên, không chạy lại toàn bộ `Hotel_Complete.sql`.

## Kiểm thử đề xuất

1. Trong trang Mùa cao điểm, tạo quy tắc cho một phòng, ví dụ `2026-12-20` đến `2026-12-24`, hệ số `1.50`.
2. Đăng nhập Customer, tìm phòng và đặt từ `2026-12-19` đến `2026-12-22`.
3. Hộp thoại đặt phòng phải hiển thị 1 đêm hệ số `1.00` và 2 đêm hệ số `1.50`.
4. Kiểm tra `booking`: `ap_dung_mua_cao_diem = 1`, `tien_phong_du_kien` là tổng tiền đã nhân hệ số.
5. Tạo Pay/hóa đơn. Kiểm tra Pay có cùng cờ, tiền phòng và JSON chi tiết; `hoadon.tien_phong` phải bằng `pay.tien_phong_ap_dung`.
6. Thay đổi hệ số trong trang Mùa cao điểm rồi kiểm tra Booking/Pay/Hóa đơn cũ: số tiền cũ phải giữ nguyên.

Yêu cầu MySQL 8.0.16+ do dự án đang sử dụng JSON và các tính năng SQL tương ứng.
