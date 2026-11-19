
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

from api_client import api_client, APIError


class PaymentsPage:
    METHODS = ["TIEN_MAT", "CHUYEN_KHOAN", "THE"]
    STATUSES = [
        "CHO_THANH_TOAN",
        "THANH_CONG",
        "THAT_BAI",
        "HOAN_TIEN"
    ]

    def __init__(self, parent):
        self.parent = parent
        self.selected_id = None
        self.bookings = []

        self.frame = ttk.Frame(parent)
        self.frame.pack(fill="both", expand=True, padx=15, pady=15)

        self.create_widgets()
        self.load_bookings()
        self.load_payments()

    def create_widgets(self):
        title = ttk.Label(
            self.frame,
            text="QUẢN LÝ THANH TOÁN",
            font=("Arial", 18, "bold")
        )
        title.pack(pady=(0, 15))

        form = ttk.LabelFrame(
            self.frame,
            text="Thông tin thanh toán",
            padding=12
        )
        form.pack(fill="x", pady=5)

        ttk.Label(form, text="Booking ID:").grid(
            row=0, column=0, padx=5, pady=7, sticky="w"
        )
        self.booking_var = tk.StringVar()
        self.booking_combo = ttk.Combobox(
            form,
            textvariable=self.booking_var,
            state="readonly",
            width=25
        )
        self.booking_combo.grid(row=0, column=1, padx=5, pady=7)

        ttk.Label(form, text="Số tiền:").grid(
            row=0, column=2, padx=5, pady=7, sticky="w"
        )
        self.amount_var = tk.StringVar()
        ttk.Entry(
            form,
            textvariable=self.amount_var,
            width=25
        ).grid(row=0, column=3, padx=5, pady=7)

        ttk.Label(form, text="Phương thức:").grid(
            row=1, column=0, padx=5, pady=7, sticky="w"
        )
        self.method_var = tk.StringVar(value=self.METHODS[0])
        ttk.Combobox(
            form,
            textvariable=self.method_var,
            values=self.METHODS,
            state="readonly",
            width=23
        ).grid(row=1, column=1, padx=5, pady=7)

        ttk.Label(form, text="Trạng thái:").grid(
            row=1, column=2, padx=5, pady=7, sticky="w"
        )
        self.status_var = tk.StringVar(value="CHO_THANH_TOAN")
        ttk.Combobox(
            form,
            textvariable=self.status_var,
            values=self.STATUSES,
            state="readonly",
            width=23
        ).grid(row=1, column=3, padx=5, pady=7)

        buttons = ttk.Frame(form)
        buttons.grid(
            row=2, column=0, columnspan=4,
            pady=10, sticky="w"
        )

        ttk.Button(
            buttons, text="Thêm",
            command=self.add_payment
        ).pack(side="left", padx=5)

        ttk.Button(
            buttons, text="Cập nhật",
            command=self.update_payment
        ).pack(side="left", padx=5)

        ttk.Button(
            buttons, text="Xóa",
            command=self.delete_payment
        ).pack(side="left", padx=5)

        ttk.Button(
            buttons, text="Làm mới",
            command=self.refresh
        ).pack(side="left", padx=5)

        search_frame = ttk.Frame(self.frame)
        search_frame.pack(fill="x", pady=10)

        ttk.Label(
            search_frame, text="Tìm theo Booking ID:"
        ).pack(side="left", padx=5)

        self.search_var = tk.StringVar()
        ttk.Entry(
            search_frame,
            textvariable=self.search_var,
            width=20
        ).pack(side="left", padx=5)

        ttk.Button(
            search_frame,
            text="Tìm kiếm",
            command=self.search_payments
        ).pack(side="left", padx=5)

        ttk.Button(
            search_frame,
            text="Hiển thị tất cả",
            command=self.load_payments
        ).pack(side="left", padx=5)

        ttk.Button(
            search_frame,
            text="Nhật ký giao dịch QR (SePay)",
            command=self.show_qr_webhook_events
        ).pack(side="left", padx=10)

        table_frame = ttk.Frame(self.frame)
        table_frame.pack(fill="both", expand=True)

        columns = (
            "id",
            "booking_id",
            "ngay_thanh_toan",
            "so_tien",
            "tien_phong_ap_dung",
            "mua_cao_diem",
            "method",
            "status"
        )

        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            height=15
        )

        headings = {
            "id": "Payment ID",
            "booking_id": "Booking ID",
            "ngay_thanh_toan": "Ngày thanh toán",
            "so_tien": "Tổng Pay",
            "tien_phong_ap_dung": "Tiền phòng đã chốt",
            "mua_cao_diem": "Mùa cao điểm",
            "method": "Phương thức",
            "status": "Trạng thái"
        }

        widths = {
            "id": 90,
            "booking_id": 100,
            "ngay_thanh_toan": 170,
            "so_tien": 130,
            "tien_phong_ap_dung": 150,
            "mua_cao_diem": 115,
            "method": 130,
            "status": 180
        }

        for col in columns:
            self.tree.heading(col, text=headings[col])
            self.tree.column(
                col,
                width=widths[col],
                anchor="center"
            )

        scrollbar = ttk.Scrollbar(
            table_frame,
            orient="vertical",
            command=self.tree.yview
        )
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(
            side="left", fill="both", expand=True
        )
        scrollbar.pack(side="right", fill="y")

        self.tree.bind(
            "<<TreeviewSelect>>",
            self.on_select
        )

    @staticmethod
    def extract_list(response):
        if isinstance(response, list):
            return response

        if isinstance(response, dict):
            for key in ("payments", "data", "items", "results"):
                value = response.get(key)
                if isinstance(value, list):
                    return value

        return []

    def load_bookings(self):
        try:
            response = api_client.get("/api/bookings/")
            self.bookings = self.extract_list(response)

            values = []
            for booking in self.bookings:
                booking_id = booking.get(
                    "id", booking.get("booking_id")
                )
                if booking_id is not None:
                    values.append(str(booking_id))

            self.booking_combo["values"] = values

            if values and not self.booking_var.get():
                self.booking_var.set(values[0])

        except APIError as error:
            messagebox.showerror(
                "Lỗi tải booking", str(error)
            )

    def load_payments(self):
        try:
            response = api_client.get("/api/payments/")
            payments = self.extract_list(response)
            self.display_payments(payments)

        except APIError as error:
            messagebox.showerror(
                "Lỗi tải thanh toán", str(error)
            )

    def display_payments(self, payments):
        for item in self.tree.get_children():
            self.tree.delete(item)

        for payment in payments:
            self.tree.insert(
                "",
                "end",
                values=(
                    payment.get("id", payment.get("pay_id", "")),
                    payment.get(
                        "booking_id", payment.get("booking_id", "")
                    ),
                    payment.get("ngay_thanh_toan", ""),
                    payment.get("so_tien", 0),
                    payment.get("tien_phong_ap_dung", 0),
                    "CÓ" if payment.get("ap_dung_mua_cao_diem") else "KHÔNG",
                    payment.get("method", ""),
                    payment.get("status", "")
                )
            )

    def get_form_data(self):
        booking_id = self.booking_var.get().strip()
        amount_text = self.amount_var.get().strip()

        if not booking_id:
            raise ValueError("Vui lòng chọn Booking ID.")

        if not amount_text:
            raise ValueError("Vui lòng nhập số tiền.")

        try:
            amount = float(amount_text.replace(",", ""))
        except ValueError:
            raise ValueError("Số tiền phải là một số hợp lệ.")

        if amount <= 0:
            raise ValueError("Số tiền phải lớn hơn 0.")

        return {
            "booking_id": int(booking_id),
            "so_tien": amount,
            "method": self.method_var.get(),
            "status": self.status_var.get()
        }

    def add_payment(self):
        try:
            data = self.get_form_data()

            # Ngày thanh toán được tạo tại thời điểm thao tác.
            data["ngay_thanh_toan"] = datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            result = api_client.post(
                "/api/payments/", data
            )

            messagebox.showinfo(
                "Thành công",
                result.get("message", "Thêm thanh toán thành công.")
                if isinstance(result, dict)
                else "Thêm thanh toán thành công."
            )

            self.clear_form()
            self.load_payments()

        except ValueError as error:
            messagebox.showwarning("Dữ liệu không hợp lệ", str(error))
        except APIError as error:
            messagebox.showerror("Lỗi API", str(error))

    def update_payment(self):
        if self.selected_id is None:
            messagebox.showwarning(
                "Thông báo",
                "Vui lòng chọn thanh toán cần cập nhật."
            )
            return

        try:
            data = self.get_form_data()

            data["ngay_thanh_toan"] = datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            result = api_client.put(
                f"/api/payments/{self.selected_id}",
                data
            )

            messagebox.showinfo(
                "Thành công",
                result.get("message", "Cập nhật thanh toán thành công.")
                if isinstance(result, dict)
                else "Cập nhật thanh toán thành công."
            )

            self.clear_form()
            self.load_payments()

        except ValueError as error:
            messagebox.showwarning("Dữ liệu không hợp lệ", str(error))
        except APIError as error:
            messagebox.showerror("Lỗi API", str(error))

    def delete_payment(self):
        if self.selected_id is None:
            messagebox.showwarning(
                "Thông báo",
                "Vui lòng chọn thanh toán cần xóa."
            )
            return

        confirm = messagebox.askyesno(
            "Xác nhận",
            f"Bạn có chắc muốn xóa thanh toán ID {self.selected_id}?"
        )

        if not confirm:
            return

        try:
            result = api_client.delete(
                f"/api/payments/{self.selected_id}"
            )

            messagebox.showinfo(
                "Thành công",
                result.get("message", "Xóa thanh toán thành công.")
                if isinstance(result, dict)
                else "Xóa thanh toán thành công."
            )

            self.clear_form()
            self.load_payments()

        except APIError as error:
            messagebox.showerror("Không thể xóa", str(error))

    def show_qr_webhook_events(self):
        """Show all provider callbacks, including unmatched or wrong-amount transfers."""
        try:
            response = api_client.get("/api/payments/webhook-events", params={"limit": 200})
            events = response.get("events", []) if isinstance(response, dict) else []
        except APIError as exc:
            messagebox.showerror("Lỗi nhật ký QR", str(exc), parent=self.frame)
            return

        window = tk.Toplevel(self.frame)
        window.title("Nhật ký thanh toán QR - SePay")
        window.geometry("1120x460")
        columns = ("id", "transaction", "code", "amount", "pay", "result", "reference", "time")
        tree = ttk.Treeview(window, columns=columns, show="headings", height=16)
        headings = {
            "id": "Log ID", "transaction": "SePay Transaction ID", "code": "Mã chuyển khoản",
            "amount": "Số tiền nhận", "pay": "Pay ID", "result": "Kết quả đối soát",
            "reference": "Mã tham chiếu ngân hàng", "time": "Thời điểm nhận",
        }
        widths = {"id": 65, "transaction": 145, "code": 130, "amount": 115,
                  "pay": 65, "result": 190, "reference": 180, "time": 150}
        for col in columns:
            tree.heading(col, text=headings[col])
            tree.column(col, width=widths[col], anchor="center")
        yscroll = ttk.Scrollbar(window, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=yscroll.set)
        tree.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)
        yscroll.pack(side="right", fill="y", padx=(0, 8), pady=8)
        for item in events:
            tree.insert("", "end", values=(
                item.get("id"), item.get("transaction_id"), item.get("payment_code"),
                f"{float(item.get('transfer_amount') or 0):,.0f} VNĐ", item.get("pay_id") or "",
                item.get("processing_result"), item.get("reference_code") or "", item.get("received_at"),
            ))
        if not events:
            ttk.Label(window, text="Chưa có webhook giao dịch nào được ghi nhận.").pack(pady=10)

    def on_select(self, event=None):
        selected = self.tree.selection()

        if not selected:
            return

        values = self.tree.item(selected[0], "values")

        self.selected_id = int(values[0])
        self.booking_var.set(str(values[1]))
        self.amount_var.set(str(values[3]))
        self.method_var.set(values[4])
        self.status_var.set(values[5])

    def search_payments(self):
        keyword = self.search_var.get().strip()

        if not keyword:
            self.load_payments()
            return

        try:
            response = api_client.get("/api/payments/")
            payments = self.extract_list(response)

            filtered = [
                payment for payment in payments
                if str(payment.get("booking_id", "")) == keyword
            ]

            self.display_payments(filtered)

        except APIError as error:
            messagebox.showerror("Lỗi API", str(error))

    def clear_form(self):
        self.selected_id = None
        self.amount_var.set("")
        self.method_var.set(self.METHODS[0])
        self.status_var.set("CHO_THANH_TOAN")

        if self.tree.selection():
            self.tree.selection_remove(self.tree.selection())

    def refresh(self):
        self.clear_form()
        self.load_bookings()
        self.load_payments()
