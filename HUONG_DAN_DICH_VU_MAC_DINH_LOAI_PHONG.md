# Cấu hình dịch vụ mặc định theo loại phòng

## Cách sử dụng trên Admin

1. Đăng nhập bằng tài khoản ADMIN.
2. Mở menu **Loại phòng**.
3. Tại loại phòng cần cấu hình, chọn **Dịch vụ mặc định**.
4. Thêm/sửa tên dịch vụ, đơn giá (VNĐ) và số lượng áp dụng cho mỗi phòng.
5. Chọn **Lưu và đồng bộ**. Hệ thống cập nhật cùng một danh sách cho tất cả phòng hiện có thuộc loại đó. Có thể xóa toàn bộ dòng dịch vụ rồi lưu để bỏ dịch vụ mặc định.

## Đồng bộ sang Customer Portal

- Trang Chọn loại phòng hiển thị tên dịch vụ, giá, số phòng đang áp dụng và số lượng trên mỗi phòng.
- Khi khách chọn phòng cụ thể, Customer Portal tải chính xác dịch vụ mặc định của phòng đó. Khách có thể chọn/bỏ chọn dịch vụ và điều chỉnh số lượng trước khi gửi Booking.
- Booking mới lưu bản sao dịch vụ khách đã chọn. Thay đổi cấu hình mặc định sau đó không làm thay đổi dịch vụ của Booking đã tạo, các giao dịch hoặc hóa đơn cũ.
- Phòng mới tạo sẽ kế thừa bộ dịch vụ từ phòng cùng loại đang có cấu hình đầy đủ nhất. Khi chuyển một phòng sang loại khác, các dịch vụ mặc định của phòng sẽ được thay bằng cấu hình của loại mới.

## Tác động lên MySQL / ERD

Không cần chạy file SQL migration và không thêm bảng mới. Chức năng sử dụng cấu trúc hiện tại: dịch vụ mặc định là các dòng `dichvu` có `booking_id IS NULL` và `phong_id` trỏ đến phòng tương ứng. API đồng bộ các dòng này trên tất cả phòng cùng loại. Các dòng `dichvu` có `booking_id IS NOT NULL` là dữ liệu dịch vụ của Booking và không bị xóa/sửa khi Admin cập nhật dịch vụ mặc định.

**Lưu ý:** loại phòng cần có ít nhất một phòng thực tế trước khi cấu hình dịch vụ mặc định.
