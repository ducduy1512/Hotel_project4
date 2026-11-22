# Cập nhật Customer Portal – bố cục loại phòng 2×2

## Thay đổi
- Customer Portal hiển thị thẻ loại phòng theo lưới 2 cột, 2 hàng khi có 4 loại phòng.
- Mỗi thẻ có vùng ảnh trống ở phía trên; có thể thêm ảnh thật sau.
- Phần thông tin hiển thị tên, giá/đêm, sức chứa, số phòng và dịch vụ mặc định tổng hợp từ các phòng cùng loại.
- Chọn một thẻ trước, sau đó chọn ngày và tìm phòng khả dụng thuộc loại đã chọn.
- Khi chọn phòng cụ thể, ứng dụng vẫn tải đúng dịch vụ mặc định của phòng đó để khách tùy chỉnh.
- URL CSS/JS có phiên bản mới để tránh trình duyệt dùng cache cũ.
- app.py không truyền tham số app_dir vào uvicorn.Config.

## Cách chạy
1. Mở thư mục `Hotel_Project5_HTML5_GUI/Hotel_project5` trong PyCharm.
2. Chọn Python Interpreter là `.venv` trong thư mục project (nếu PyCharm chưa tự nhận diện).
3. Cấu hình Run dùng Script `app.py`, Working directory là thư mục `Hotel_project5`.
4. Chạy `app.py`; giữ cửa sổ Run mở.
5. Truy cập `http://127.0.0.1:8000/` bằng Chrome hoặc Edge.
6. Nhấn `Ctrl + F5` nếu trình duyệt đang mở giao diện cũ.

## Dữ liệu dịch vụ ở thẻ loại phòng
Trong schema hiện tại, dịch vụ mặc định được gắn với từng phòng qua `dichvu.phong_id` với `booking_id IS NULL`. API tổng hợp dịch vụ theo tên và đơn giá cho các phòng cùng loại. Đây là phần mô tả tổng hợp; khi khách chọn phòng, API vẫn trả dịch vụ riêng của phòng đó. Không cần thay đổi cấu trúc SQL cho phần giao diện này.

## Ghi chú
- Không chạy hai server đồng thời trên cổng 8000.
- Không chia sẻ file `.env` công khai vì có thể chứa thông tin kết nối MySQL và khóa dịch vụ thanh toán.
- Project cần MySQL và các bảng / stored procedures hiện có để chạy chức năng booking thực tế.
