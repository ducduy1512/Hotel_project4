# Hotel Management System – SQLite Edition

Phiên bản chạy của project dùng **SQLite nhúng trong Python**. Người dùng không cần cài MySQL Server, không cần MySQL Workbench và không cần chạy file SQL thủ công.

## Chạy project trên máy mới bằng PyCharm

1. Cài Python 3.10 trở lên và Git.
2. Clone repository rồi mở thư mục project bằng PyCharm.
3. Mở Terminal trong PyCharm và cài thư viện (chỉ cần làm lần đầu):

   ```bash
   pip install -r requirements.txt
   ```

4. Trong PyCharm, mở `app.py` và bấm **Run**. Hoặc chạy trong Terminal:

   ```bash
   python app.py
   ```

5. Mở `http://127.0.0.1:8000` để sử dụng giao diện; tài liệu API ở `http://127.0.0.1:8000/docs`.

## Database được tạo tự động

Trong lần chạy đầu tiên, ứng dụng tự tạo `data/hotel_management.db` từ các file SQLite nằm ngay trong Git repository:

- `sqlite_database/schema.sql`: 12 bảng, khóa ngoại, CHECK, UNIQUE và index.
- `sqlite_database/seed_data.sql`: dữ liệu demo đã được chuyển từ file `hotel_management_full.sql` mà nhóm cung cấp.
- `sqlite_database/views.sql`: 10 view báo cáo.
- `sqlite_database/triggers.sql`: 17 trigger SQLite cho các ràng buộc và nghiệp vụ quan trọng.

Database chỉ được khởi tạo và nạp dữ liệu mẫu khi file chưa tồn tại. Những lần chạy sau sử dụng database cục bộ hiện có, không xóa hoặc nạp đè dữ liệu. Nếu file database cũ bị thiếu bảng bắt buộc, ứng dụng báo lỗi để người dùng kiểm tra thay vì tự ý xóa dữ liệu.

`data/hotel_management.db` và khóa ký token `data/.auth_secret` là dữ liệu riêng trên từng máy, được loại khỏi Git bằng `.gitignore`. Muốn khởi tạo lại dữ liệu demo từ đầu, hãy tắt ứng dụng, sao lưu rồi xóa `data/hotel_management.db`.

## Cập nhật code từ Git

Sau khi nhóm đẩy code mới lên GitHub, người dùng chạy `git pull` rồi khởi động lại `app.py`. Database cục bộ sẽ được giữ nguyên. Lưu ý: nếu phiên bản mới thay đổi cấu trúc bảng, nhóm phải cung cấp migration riêng; `git pull` không tự ghi đè database hiện có.

## Các nghiệp vụ database

SQLite không hỗ trợ Stored Procedure theo cú pháp MySQL. Những procedure được API sử dụng đã được chuyển thành logic Python trong `database.py`; 17 trigger và 10 view có phiên bản SQLite riêng. Các API hiện tại vẫn sử dụng chung luồng nghiệp vụ đặt phòng, snapshot giá từng đêm, phụ thu mùa cao điểm, dịch vụ, thanh toán và hóa đơn.

## Cấu hình tùy chọn và thanh toán QR / SePay

Không cần tạo file `.env` để khởi động ứng dụng. Khóa ký token được tự tạo và lưu cục bộ tại `data/.auth_secret`.

Project vẫn chạy bình thường khi chưa cấu hình QR. Trong Customer Portal, phương thức **Chuyển khoản QR** sẽ không khả dụng; khách vẫn có thể chọn phương thức thanh toán khác đang được hỗ trợ.

Muốn bật QR VietQR, sao chép `.env.example` thành `.env`, sau đó điền thông tin tài khoản nhận tiền thật:

```env
PAYMENT_BANK_CODE=VCB
PAYMENT_BANK_ACCOUNT=SO_TAI_KHOAN_THAT
PAYMENT_ACCOUNT_NAME=TEN_CHU_TAI_KHOAN
```

Thay `VCB`, `SO_TAI_KHOAN_THAT` và `TEN_CHU_TAI_KHOAN` bằng thông tin đúng của tài khoản nhận tiền. Lưu `.env` rồi khởi động lại API. Không sử dụng ví dụ trên như thông tin ngân hàng thật.

Để nhận callback SePay thực tế, cần cấu hình thêm webhook, chế độ xác thực và secret theo tài khoản SePay của môi trường triển khai. Không commit `.env`, API key hoặc secret thật lên GitHub.

## Lưu ý về file SQL MySQL cũ

Các script SQL của phiên bản MySQL trước đây được lưu trong `docs/mysql_legacy/` để tham khảo. Chúng không được ứng dụng nạp hoặc thực thi. **Không cần MySQL Server và không chạy các script này để khởi động project.** Database đang chạy được tạo tự động từ `sqlite_database/`.

## An toàn khi đẩy lên GitHub

Không commit `.env`, `data/*.db`, `data/*.db-wal`, `data/*.db-shm` hoặc `data/.auth_secret`. Các mục này đã được khai báo trong `.gitignore`. Nếu file database đã từng được commit trước đó, `.gitignore` không tự bỏ theo dõi; hãy chạy `git rm --cached data/hotel_management.db` (chỉ khi file đang được Git theo dõi), rồi commit thay đổi.
