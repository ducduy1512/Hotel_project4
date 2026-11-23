# Chuyển quan hệ PHONG – MUACAODIEM sang N–N

## Mô hình mới

- `muacaodiem(id, tu_ngay, den_ngay)`: mỗi dòng là một mùa/khoảng ngày dùng chung.
- `phong_muacaodiem(phong_id, muacaodiem_id, he_so_phu_thu)`: bảng liên kết N–N; tỷ lệ phụ thu riêng cho từng phòng.
- Khóa chính bảng liên kết: `(phong_id, muacaodiem_id)`.
- Xóa một mùa sẽ cascade các liên kết; phòng không bị xóa.

## Nâng cấp database hiện tại

1. Sao lưu database `hotel_management_erd`.
2. Dừng Backend (`Ctrl+C`).
3. Nếu migration đã chạy được tới câu `UPDATE phong_muacaodiem` nhưng dừng ở Error 1175, KHÔNG chạy lại migration từ đầu. Chạy `Hotel_Peak_Season_Rates_By_Room_Type.sql` để hoàn tất việc gán tỷ lệ và liên kết phòng còn thiếu. Nếu chưa chạy migration lần nào, dùng `Hotel_Peak_Season_NN_Migration.sql` mới. Mùa mẫu 20/12–31/12/2026 sẽ có 11 liên kết (nếu database có 11 phòng).
4. Chạy `Hotel_Procedures.sql`.
5. Chạy `Hotel_Trigger.sql`.
6. Chạy `Hotel_Report.sql`.
7. Khởi động lại `app.py`.

Không chạy `Hotel_Complete.sql` trên database đang có dữ liệu vì đây là script tạo database mới.

## Quy tắc giá

`he_so_phu_thu` là tỷ lệ cộng thêm, không phải hệ số nhân tổng giá. Ví dụ 0.25 nghĩa là cộng thêm 25% giá phòng mỗi đêm. Booking lưu snapshot từng đêm; hóa đơn cũ không bị tính lại.

## Tỷ lệ mẫu đã cấu hình

| Phòng | Loại phòng | Phụ thu |
|---|---|---:|
| 101, 102, 502, 601 | Standard | 20% |
| 201, 202, 501 | Deluxe | 25% |
| 301, 302 | VIP | 30% |
| 401, 402 | Family | 35% |

Admin tạo một mùa sẽ tạo một dòng `muacaodiem`, sau đó tạo các liên kết trong `phong_muacaodiem`. Customer xem phụ phí theo phòng và từng ngày trước khi xác nhận Booking.


## Tỷ lệ phụ thu theo loại phòng của từng phòng vật lý

Tỷ lệ được tự động gán theo `phong.loai_phong_id` -> `loaiphong.ten`, sau đó lưu trên từng dòng `phong_muacaodiem`:
- Standard: 20%
- Deluxe: 25%
- VIP: 30%
- Family: 35%

Mọi phòng thuộc cùng một loại phòng đều nhận tỷ lệ tương ứng. Ví dụ phòng 501 là Deluxe nên 25%; phòng 502 và 601 là Standard nên 20%. Chạy `Hotel_Peak_Season_Rates_By_Room_Type.sql` sau khi migration N-N cũ đã tạo bảng trung gian.
