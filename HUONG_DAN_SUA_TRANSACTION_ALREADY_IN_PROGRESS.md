# Khắc phục lỗi `Transaction already in progress`

## Nguyên nhân

FastAPI tái sử dụng dependency `get_db()` trong cùng request. Dependency xác thực Admin (`get_current_user`) thực hiện SELECT bằng MySQL Connector/Python. Vì kết nối mặc định `autocommit=False`, SELECT mở một read transaction. Endpoint được bảo vệ sau đó dùng lại cùng connection và gọi `db.start_transaction()`, gây lỗi `Transaction already in progress`.

## Cách sửa

Trong `api/routers/auth.py`, sau khi đọc tài khoản thành công, gọi `db.rollback()` để kết thúc transaction chỉ đọc trước khi trả kết quả xác thực. Không có dữ liệu nào bị ghi bởi truy vấn xác thực này. Sau đó endpoint quản trị có thể mở transaction riêng.

## Cập nhật dự án

1. Sao lưu thư mục dự án hiện tại.
2. Giải nén ZIP bản đã sửa.
3. Sao chép `.env` hiện tại vào thư mục `Hotel_project5` của bản mới.
4. Khởi động lại `app.py` để FastAPI nạp lại `auth.py`.
5. Vào Admin → Thanh toán → Pay #16 → Lưu thay đổi.

Không cần chạy SQL Migration, không cần sửa trực tiếp bảng `pay`, không cần import lại database.

## Kiểm thử cần thực hiện trên MySQL của máy triển khai

- Mở Pay #16, thử cập nhật trạng thái hợp lệ theo quy tắc hiện tại.
- Xác nhận API không còn trả `Transaction already in progress`.
- Xác nhận Pay và hóa đơn vẫn giữ nguyên tổng tiền, tiền phòng, tiền dịch vụ và phụ phí mùa cao điểm.
- Nếu Pay chuyển sang `THANH_CONG`, chỉ thực hiện khi giao dịch đã có hóa đơn hợp lệ và tiền hóa đơn khớp Pay.
