# Hiển thị Tiền dịch vụ trong Quản lý thanh toán

## Thay đổi
- API `GET /api/payments/` và `GET /api/payments/{payment_id}` trả thêm `tien_dich_vu`.
- Tiền dịch vụ được đọc theo snapshot giao dịch Pay: `MAX(so_tien - tien_phong_ap_dung - tien_phu_phi_mua_cao_diem, 0)`.
- Giao diện HTML5 thêm cột **Tiền dịch vụ** giữa **Tiền phòng** và **Phụ phí mùa cao điểm**, cùng thứ tự thành phần với trang Quản lý hóa đơn.
- Màn hình Tkinter `pages/payments.py` cũng được cập nhật đồng bộ.

## Vì sao dùng snapshot Pay?
Bảng `pay` lưu tổng Pay, tiền phòng đã chốt và phụ phí mùa cao điểm đã chốt. Phần chênh lệch là tiền dịch vụ của chính giao dịch đó. Cách này giữ nguyên số tiền hiển thị của giao dịch cũ, kể cả khi dữ liệu dịch vụ trên Booking được thay đổi sau một giao dịch không phát hành hóa đơn.

## Database
Không cần ALTER TABLE, migration, thay đổi Trigger hoặc Stored Procedure. `tien_dich_vu` là trường tính toán trong API, không phải cột mới của bảng `pay`.

## Kiểm tra
Đối chiếu một Pay cụ thể bằng câu SQL:

```sql
SELECT
    id AS pay_id,
    booking_id,
    so_tien AS tong_pay,
    tien_phong_ap_dung,
    tien_phu_phi_mua_cao_diem,
    GREATEST(
        so_tien - tien_phong_ap_dung - tien_phu_phi_mua_cao_diem,
        0
    ) AS tien_dich_vu
FROM pay
WHERE id = 16;
```
Thay `16` bằng Pay ID cần kiểm tra. Với Pay ID 16 trong ảnh bạn gửi, tiền dịch vụ dự kiến là 800.000đ (1.800.000 - 1.000.000 - 0).
