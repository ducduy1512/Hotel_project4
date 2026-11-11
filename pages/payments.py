
import tkinter as tk
from tkinter import ttk, messagebox

from database import get_connection


class PaymentsPage:
    def __init__(self, parent):
        self.parent = parent

        self.navy = "#101F35"
        self.gold = "#D5AD5B"
        self.white = "#FFFFFF"
        self.background = "#F4F6F9"
        self.gray = "#8793A5"

        self.selected_id = None

        self.build_ui()
        self.load_payments()

    def build_ui(self):
        # Tiêu đề
        tk.Label(
            self.parent,
            text="QUẢN LÝ THANH TOÁN",
            font=("Arial", 24, "bold"),
            fg=self.navy,
            bg=self.background
        ).pack(anchor="w", padx=35, pady=(30, 5))

        tk.Label(
            self.parent,
            text="Theo dõi giao dịch, phương thức và trạng thái thanh toán",
            font=("Arial", 11),
            fg=self.gray,
            bg=self.background
        ).pack(anchor="w", padx=35, pady=(0, 20))

        # Thanh tìm kiếm và lọc
        search_frame = tk.Frame(
            self.parent,
            bg=self.white,
            highlightbackground="#DDE3EA",
            highlightthickness=1
        )
        search_frame.pack(fill="x", padx=35, pady=(0, 18))

        tk.Label(
            search_frame,
            text="Tìm kiếm:",
            font=("Arial", 10, "bold"),
            bg=self.white,
            fg=self.navy
        ).pack(side="left", padx=(15, 8), pady=15)

        self.search_entry = tk.Entry(
            search_frame,
            font=("Arial", 10),
            width=23
        )
        self.search_entry.pack(side="left", padx=5, pady=12)
        self.search_entry.bind(
            "<KeyRelease>",
            lambda event: self.load_payments()
        )

        tk.Label(
            search_frame,
            text="Trạng thái:",
            font=("Arial", 10, "bold"),
            bg=self.white,
            fg=self.navy
        ).pack(side="left", padx=(12, 8))

        self.status_filter = ttk.Combobox(
            search_frame,
            values=[
                "Tất cả",
                "CHO_THANH_TOAN",
                "THANH_CONG",
                "THAT_BAI",
                "HOAN_TIEN"
            ],
            state="readonly",
            width=19,
            font=("Arial", 9)
        )
        self.status_filter.set("Tất cả")
        self.status_filter.pack(side="left", padx=5, pady=12)
        self.status_filter.bind(
            "<<ComboboxSelected>>",
            lambda event: self.load_payments()
        )

        tk.Button(
            search_frame,
            text="LÀM MỚI",
            command=self.refresh_page,
            font=("Arial", 10, "bold"),
            bg=self.navy,
            fg=self.white,
            relief="flat",
            padx=16,
            pady=9,
            cursor="hand2"
        ).pack(side="left", padx=12)

        # Thông tin giao dịch
        form_frame = tk.LabelFrame(
            self.parent,
            text=" THÔNG TIN THANH TOÁN ",
            font=("Arial", 12, "bold"),
            bg=self.white,
            fg=self.navy,
            padx=18,
            pady=18
        )
        form_frame.pack(fill="x", padx=35, pady=(0, 18))

        for col in range(3):
            form_frame.columnconfigure(col, weight=1)

        labels = [
            "Mã thanh toán",
            "Mã booking",
            "Số tiền (VNĐ)"
        ]

        for col, label in enumerate(labels):
            tk.Label(
                form_frame,
                text=label,
                font=("Arial", 9, "bold"),
                bg=self.white,
                fg=self.navy
            ).grid(
                row=0, column=col,
                sticky="w", padx=8, pady=(0, 7)
            )

        self.payment_id_var = tk.StringVar()
        self.booking_id_var = tk.StringVar()
        self.amount_var = tk.StringVar()

        self.payment_id_label = tk.Entry(
            form_frame,
            textvariable=self.payment_id_var,
            state="readonly",
            font=("Arial", 10),
            readonlybackground="#EEF1F5"
        )
        self.payment_id_label.grid(
            row=1, column=0,
            sticky="ew", padx=8, pady=(0, 15), ipady=5
        )

        self.booking_id_label = tk.Entry(
            form_frame,
            textvariable=self.booking_id_var,
            state="readonly",
            font=("Arial", 10),
            readonlybackground="#EEF1F5"
        )
        self.booking_id_label.grid(
            row=1, column=1,
            sticky="ew", padx=8, pady=(0, 15), ipady=5
        )

        self.amount_label = tk.Entry(
            form_frame,
            textvariable=self.amount_var,
            state="readonly",
            font=("Arial", 10),
            readonlybackground="#EEF1F5"
        )
        self.amount_label.grid(
            row=1, column=2,
            sticky="ew", padx=8, pady=(0, 15), ipady=5
        )

        tk.Label(
            form_frame,
            text="Phương thức thanh toán",
            font=("Arial", 9, "bold"),
            bg=self.white,
            fg=self.navy
        ).grid(
            row=2, column=0,
            sticky="w", padx=8, pady=(0, 7)
        )

        tk.Label(
            form_frame,
            text="Ngày thanh toán",
            font=("Arial", 9, "bold"),
            bg=self.white,
            fg=self.navy
        ).grid(
            row=2, column=1,
            sticky="w", padx=8, pady=(0, 7)
        )

        tk.Label(
            form_frame,
            text="Trạng thái thanh toán",
            font=("Arial", 9, "bold"),
            bg=self.white,
            fg=self.navy
        ).grid(
            row=2, column=2,
            sticky="w", padx=8, pady=(0, 7)
        )

        self.method_var = tk.StringVar()
        self.date_var = tk.StringVar()
        self.status_var = tk.StringVar()

        self.method_label = tk.Entry(
            form_frame,
            textvariable=self.method_var,
            state="readonly",
            font=("Arial", 10),
            readonlybackground="#EEF1F5"
        )
        self.method_label.grid(
            row=3, column=0,
            sticky="ew", padx=8, pady=(0, 15), ipady=5
        )

        self.date_label = tk.Entry(
            form_frame,
            textvariable=self.date_var,
            state="readonly",
            font=("Arial", 10),
            readonlybackground="#EEF1F5"
        )
        self.date_label.grid(
            row=3, column=1,
            sticky="ew", padx=8, pady=(0, 15), ipady=5
        )

        self.status_combo = ttk.Combobox(
            form_frame,
            textvariable=self.status_var,
            values=[
                "CHO_THANH_TOAN",
                "THANH_CONG",
                "THAT_BAI",
                "HOAN_TIEN"
            ],
            state="readonly",
            font=("Arial", 9)
        )
        self.status_combo.grid(
            row=3, column=2,
            sticky="ew", padx=8, pady=(0, 15), ipady=4
        )

        # Nút chức năng
        button_frame = tk.Frame(form_frame, bg=self.white)
        button_frame.grid(
            row=4, column=0,
            columnspan=3, sticky="w", padx=8
        )

        tk.Button(
            button_frame,
            text="CẬP NHẬT TRẠNG THÁI",
            command=self.update_payment_status,
            bg="#218C65",
            fg=self.white,
            font=("Arial", 10, "bold"),
            relief="flat",
            padx=18,
            pady=10,
            cursor="hand2"
        ).pack(side="left", padx=(0, 10))

        tk.Button(
            button_frame,
            text="XÓA TRẮNG",
            command=self.clear_form,
            bg="#8793A5",
            fg=self.white,
            font=("Arial", 10, "bold"),
            relief="flat",
            padx=18,
            pady=10,
            cursor="hand2"
        ).pack(side="left", padx=10)

        # Danh sách thanh toán
        table_frame = tk.Frame(
            self.parent,
            bg=self.white,
            highlightbackground="#DDE3EA",
            highlightthickness=1
        )
        table_frame.pack(
            fill="both",
            expand=True,
            padx=35,
            pady=(0, 25)
        )

        tk.Label(
            table_frame,
            text="DANH SÁCH GIAO DỊCH",
            font=("Arial", 13, "bold"),
            fg=self.navy,
            bg=self.white
        ).pack(anchor="w", padx=18, pady=12)

        columns = (
            "id", "booking", "customer", "room",
            "date", "amount", "method", "status"
        )

        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings"
        )

        headings = {
            "id": "Mã thanh toán",
            "booking": "Mã booking",
            "customer": "Khách hàng",
            "room": "Phòng",
            "date": "Ngày thanh toán",
            "amount": "Số tiền",
            "method": "Phương thức",
            "status": "Trạng thái"
        }

        widths = {
            "id": 90,
            "booking": 90,
            "customer": 160,
            "room": 75,
            "date": 130,
            "amount": 140,
            "method": 130,
            "status": 160
        }

        for col in columns:
            self.tree.heading(col, text=headings[col])
            self.tree.column(
                col,
                width=widths[col],
                anchor="center"
            )

        scrollbar_y = ttk.Scrollbar(
            table_frame,
            orient="vertical",
            command=self.tree.yview
        )

        scrollbar_x = ttk.Scrollbar(
            table_frame,
            orient="horizontal",
            command=self.tree.xview
        )

        self.tree.configure(
            yscrollcommand=scrollbar_y.set,
            xscrollcommand=scrollbar_x.set
        )

        self.tree.pack(
            side="top",
            fill="both",
            expand=True,
            padx=(12, 0)
        )

        scrollbar_y.pack(side="right", fill="y")
        scrollbar_x.pack(side="bottom", fill="x")

        self.tree.bind(
            "<<TreeviewSelect>>",
            self.select_payment
        )

    # Tải danh sách thanh toán
    def load_payments(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        keyword = self.search_entry.get().strip()
        status = self.status_filter.get()

        connection = get_connection()

        if connection is None:
            messagebox.showerror(
                "Lỗi kết nối",
                "Không thể kết nối MySQL."
            )
            return

        cursor = None

        try:
            cursor = connection.cursor()

            sql = """
                SELECT
                    p.id,
                    p.booking_id,
                    k.ho_ten,
                    r.so_phong,
                    p.ngay_thanh_toan,
                    p.so_tien,
                    p.method,
                    p.status
                FROM pay p
                JOIN booking b ON p.booking_id = b.id
                JOIN khach k ON b.khach_id = k.id
                JOIN phong r ON b.phong_id = r.id
                WHERE (
                    CAST(p.id AS CHAR) LIKE %s
                    OR CAST(p.booking_id AS CHAR) LIKE %s
                    OR k.ho_ten LIKE %s
                    OR CAST(r.so_phong AS CHAR) LIKE %s
                )
            """

            params = [
                f"%{keyword}%",
                f"%{keyword}%",
                f"%{keyword}%",
                f"%{keyword}%"
            ]

            if status != "Tất cả":
                sql += " AND p.status = %s"
                params.append(status)

            sql += " ORDER BY p.id DESC"

            cursor.execute(sql, tuple(params))

            for row in cursor.fetchall():
                payment_id, booking_id, customer, room, date, amount, method, payment_status = row

                self.tree.insert(
                    "",
                    "end",
                    values=(
                        payment_id,
                        booking_id,
                        customer,
                        room,
                        date,
                        f"{float(amount):,.0f} đ",
                        method,
                        payment_status
                    )
                )

        except Exception as e:
            messagebox.showerror("Lỗi", str(e))

        finally:
            if cursor:
                cursor.close()
            connection.close()

    # Chọn giao dịch
    def select_payment(self, event):
        selected = self.tree.selection()

        if not selected:
            return

        values = self.tree.item(selected[0], "values")

        self.selected_id = int(values[0])

        self.payment_id_var.set(values[0])
        self.booking_id_var.set(values[1])
        self.amount_var.set(values[5])
        self.method_var.set(values[6])
        self.date_var.set(str(values[4]))
        self.status_var.set(values[7])

    # Cập nhật trạng thái thanh toán
    def update_payment_status(self):
        if self.selected_id is None:
            messagebox.showwarning(
                "Chưa chọn giao dịch",
                "Vui lòng chọn một giao dịch trong danh sách."
            )
            return

        new_status = self.status_var.get()

        if not new_status:
            messagebox.showwarning(
                "Thiếu trạng thái",
                "Vui lòng chọn trạng thái thanh toán."
            )
            return

        connection = get_connection()

        if connection is None:
            messagebox.showerror(
                "Lỗi kết nối",
                "Không thể kết nối MySQL."
            )
            return

        cursor = None

        try:
            cursor = connection.cursor()

            cursor.execute(
                "SELECT status FROM pay WHERE id = %s",
                (self.selected_id,)
            )

            result = cursor.fetchone()

            if not result:
                messagebox.showerror(
                    "Không tìm thấy",
                    "Giao dịch không còn tồn tại."
                )
                return

            old_status = result[0]

            if old_status == new_status:
                messagebox.showinfo(
                    "Thông báo",
                    "Trạng thái thanh toán không thay đổi."
                )
                return

            # Kiểm soát các bước chuyển trạng thái
            allowed_transitions = {
                "CHO_THANH_TOAN": [
                    "THANH_CONG",
                    "THAT_BAI"
                ],
                "THAT_BAI": [
                    "CHO_THANH_TOAN",
                    "THANH_CONG"
                ],
                "THANH_CONG": [
                    "HOAN_TIEN"
                ],
                "HOAN_TIEN": []
            }

            if new_status not in allowed_transitions.get(old_status, []):
                messagebox.showwarning(
                    "Chuyển trạng thái không hợp lệ",
                    f"Không thể chuyển từ {old_status} sang {new_status}."
                )
                return

            confirm = messagebox.askyesno(
                "Xác nhận thanh toán",
                f"Mã giao dịch: {self.selected_id}\n"
                f"Trạng thái hiện tại: {old_status}\n"
                f"Trạng thái mới: {new_status}\n\n"
                "Bạn có chắc chắn muốn cập nhật không?"
            )

            if not confirm:
                return

            cursor.execute("""
                UPDATE pay
                SET status = %s
                WHERE id = %s
            """, (new_status, self.selected_id))

            connection.commit()

            messagebox.showinfo(
                "Thành công",
                "Cập nhật trạng thái thanh toán thành công."
            )

            self.clear_form()
            self.load_payments()

        except Exception as e:
            connection.rollback()
            messagebox.showerror(
                "Không thể cập nhật",
                "MySQL đã từ chối cập nhật hoặc xảy ra lỗi.\n\n"
                + str(e)
            )

        finally:
            if cursor:
                cursor.close()
            connection.close()

    # Xóa biểu mẫu
    def clear_form(self):
        self.selected_id = None

        self.payment_id_var.set("")
        self.booking_id_var.set("")
        self.amount_var.set("")
        self.method_var.set("")
        self.date_var.set("")
        self.status_var.set("")

        for item in self.tree.selection():
            self.tree.selection_remove(item)

    # Làm mới
    def refresh_page(self):
        self.search_entry.delete(0, tk.END)
        self.status_filter.set("Tất cả")
        self.clear_form()
        self.load_payments()
