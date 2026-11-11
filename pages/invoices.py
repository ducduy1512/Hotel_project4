
import tkinter as tk
from tkinter import ttk, messagebox
from database import get_connection


class InvoicesPage:
    def __init__(self, parent):
        self.parent = parent
        self.frame = tk.Frame(parent, bg="#F3F5F9")
        self.frame.pack(fill="both", expand=True)

        self.search_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Tất cả")

        self.invoices = {}
        self.selected_invoice = None

        self.build_ui()
        self.load_invoices()

    def build_ui(self):
        # ================= HEADER =================
        header = tk.Frame(self.frame, bg="#F3F5F9")
        header.pack(fill="x", padx=25, pady=(20, 10))

        tk.Label(
            header,
            text="QUẢN LÝ HÓA ĐƠN",
            font=("Arial", 23, "bold"),
            fg="#10233F",
            bg="#F3F5F9"
        ).pack(anchor="w")

        tk.Label(
            header,
            text="Tra cứu hóa đơn và thông tin chi tiết thanh toán",
            font=("Arial", 11),
            fg="#8190A5",
            bg="#F3F5F9"
        ).pack(anchor="w", pady=(5, 0))

        # ================= SEARCH =================
        search_frame = tk.Frame(
            self.frame,
            bg="white",
            highlightbackground="#DCE2EA",
            highlightthickness=1
        )
        search_frame.pack(fill="x", padx=25, pady=10)

        tk.Label(
            search_frame,
            text="Tìm kiếm:",
            font=("Arial", 10, "bold"),
            bg="white",
            fg="#10233F"
        ).pack(side="left", padx=(15, 8), pady=15)

        search_entry = ttk.Entry(
            search_frame,
            textvariable=self.search_var,
            width=30
        )
        search_entry.pack(side="left", padx=5, pady=15)
        search_entry.bind(
            "<KeyRelease>",
            lambda event: self.load_invoices()
        )

        tk.Label(
            search_frame,
            text="Trạng thái thanh toán:",
            font=("Arial", 10, "bold"),
            bg="white",
            fg="#10233F"
        ).pack(side="left", padx=(20, 8))

        status_combo = ttk.Combobox(
            search_frame,
            textvariable=self.status_var,
            values=[
                "Tất cả",
                "CHO_THANH_TOAN",
                "THANH_CONG",
                "THAT_BAI",
                "HOAN_TIEN"
            ],
            state="readonly",
            width=20
        )
        status_combo.pack(side="left", padx=5)
        status_combo.bind(
            "<<ComboboxSelected>>",
            lambda event: self.load_invoices()
        )

        tk.Button(
            search_frame,
            text="LÀM MỚI",
            font=("Arial", 10, "bold"),
            bg="#10233F",
            fg="white",
            activebackground="#243D5C",
            activeforeground="white",
            relief="flat",
            cursor="hand2",
            command=self.refresh
        ).pack(side="left", padx=15, ipadx=12, ipady=8)

        # ================= DETAILS =================
        detail_frame = tk.LabelFrame(
            self.frame,
            text="  THÔNG TIN HÓA ĐƠN  ",
            font=("Arial", 11, "bold"),
            bg="white",
            fg="#10233F",
            padx=15,
            pady=12
        )
        detail_frame.pack(fill="x", padx=25, pady=10)

        self.detail_vars = {
            "id": tk.StringVar(),
            "pay_id": tk.StringVar(),
            "booking_id": tk.StringVar(),
            "customer": tk.StringVar(),
            "room": tk.StringVar(),
            "room_price": tk.StringVar(),
            "service_price": tk.StringVar(),
            "total": tk.StringVar(),
            "date": tk.StringVar(),
            "method": tk.StringVar(),
            "status": tk.StringVar()
        }

        fields = [
            ("Mã hóa đơn", "id"),
            ("Mã thanh toán", "pay_id"),
            ("Mã booking", "booking_id"),
            ("Khách hàng", "customer"),
            ("Số phòng", "room"),
            ("Tiền phòng", "room_price"),
            ("Tiền dịch vụ", "service_price"),
            ("Tổng tiền", "total"),
            ("Ngày lập", "date"),
            ("Phương thức", "method"),
            ("Trạng thái thanh toán", "status")
        ]

        for index, (label, key) in enumerate(fields):
            row = index // 3
            col = index % 3

            cell = tk.Frame(detail_frame, bg="white")
            cell.grid(
                row=row,
                column=col,
                sticky="ew",
                padx=8,
                pady=7
            )

            tk.Label(
                cell,
                text=label,
                font=("Arial", 9, "bold"),
                bg="white",
                fg="#35465E"
            ).pack(anchor="w")

            entry = ttk.Entry(
                cell,
                textvariable=self.detail_vars[key],
                state="readonly",
                width=35
            )
            entry.pack(fill="x", pady=(5, 0))

        for col in range(3):
            detail_frame.columnconfigure(col, weight=1)

        # ================= BUTTONS =================
        button_frame = tk.Frame(detail_frame, bg="white")
        button_frame.grid(
            row=4,
            column=0,
            columnspan=3,
            sticky="w",
            padx=8,
            pady=(10, 2)
        )

        tk.Button(
            button_frame,
            text="XEM TRƯỚC HÓA ĐƠN",
            font=("Arial", 10, "bold"),
            bg="#D6A84F",
            fg="#10233F",
            relief="flat",
            cursor="hand2",
            command=self.preview_invoice
        ).pack(side="left", ipadx=12, ipady=8)

        tk.Button(
            button_frame,
            text="XÓA LỰA CHỌN",
            font=("Arial", 10, "bold"),
            bg="#8794A6",
            fg="white",
            relief="flat",
            cursor="hand2",
            command=self.clear_selection
        ).pack(side="left", padx=12, ipadx=12, ipady=8)

        # ================= INVOICE LIST =================
        list_frame = tk.Frame(
            self.frame,
            bg="white",
            highlightbackground="#DCE2EA",
            highlightthickness=1
        )
        list_frame.pack(
            fill="both",
            expand=True,
            padx=25,
            pady=(5, 20)
        )

        tk.Label(
            list_frame,
            text="DANH SÁCH HÓA ĐƠN",
            font=("Arial", 13, "bold"),
            bg="white",
            fg="#10233F"
        ).pack(anchor="w", padx=15, pady=12)

        columns = (
            "id",
            "pay_id",
            "booking_id",
            "customer",
            "room",
            "room_price",
            "service_price",
            "total",
            "date",
            "status"
        )

        table_container = tk.Frame(list_frame, bg="white")
        table_container.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.tree = ttk.Treeview(
            table_container,
            columns=columns,
            show="headings",
            height=12
        )

        headings = {
            "id": "Mã HĐ",
            "pay_id": "Mã thanh toán",
            "booking_id": "Mã booking",
            "customer": "Khách hàng",
            "room": "Phòng",
            "room_price": "Tiền phòng",
            "service_price": "Tiền dịch vụ",
            "total": "Tổng tiền",
            "date": "Ngày lập",
            "status": "Trạng thái"
        }

        widths = {
            "id": 65,
            "pay_id": 90,
            "booking_id": 90,
            "customer": 145,
            "room": 65,
            "room_price": 110,
            "service_price": 115,
            "total": 120,
            "date": 145,
            "status": 145
        }

        for col in columns:
            self.tree.heading(col, text=headings[col])
            self.tree.column(
                col,
                width=widths[col],
                minwidth=60,
                anchor="center"
            )

        scrollbar_y = ttk.Scrollbar(
            table_container,
            orient="vertical",
            command=self.tree.yview
        )

        scrollbar_x = ttk.Scrollbar(
            table_container,
            orient="horizontal",
            command=self.tree.xview
        )

        self.tree.configure(
            yscrollcommand=scrollbar_y.set,
            xscrollcommand=scrollbar_x.set
        )

        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        scrollbar_x.grid(row=1, column=0, sticky="ew")

        table_container.rowconfigure(0, weight=1)
        table_container.columnconfigure(0, weight=1)

        self.tree.bind(
            "<<TreeviewSelect>>",
            self.on_select
        )

    # ================= LOAD DATA =================
    def load_invoices(self):
        connection = get_connection()

        if connection is None:
            messagebox.showerror(
                "Lỗi kết nối",
                "Không thể kết nối đến MySQL."
            )
            return

        cursor = None

        try:
            cursor = connection.cursor(dictionary=True)

            sql = """
                SELECT
                    h.id AS invoice_id,
                    h.pay_id,
                    p.booking_id,
                    k.ho_ten AS customer_name,
                    ph.so_phong,
                    h.tien_phong,
                    h.tien_dich_vu,
                    h.tong_tien,
                    h.ngay_lap,
                    p.method,
                    p.status
                FROM hoadon h
                JOIN pay p ON h.pay_id = p.id
                JOIN booking b ON p.booking_id = b.id
                JOIN khach k ON b.khach_id = k.id
                JOIN phong ph ON b.phong_id = ph.id
                WHERE 1 = 1
            """

            params = []

            keyword = self.search_var.get().strip()

            if keyword:
                sql += """
                    AND (
                        CAST(h.id AS CHAR) LIKE %s
                        OR CAST(h.pay_id AS CHAR) LIKE %s
                        OR CAST(p.booking_id AS CHAR) LIKE %s
                        OR k.ho_ten LIKE %s
                        OR CAST(ph.so_phong AS CHAR) LIKE %s
                    )
                """

                search_value = f"%{keyword}%"
                params.extend([search_value] * 5)

            selected_status = self.status_var.get()

            if selected_status != "Tất cả":
                sql += " AND p.status = %s"
                params.append(selected_status)

            sql += " ORDER BY h.id DESC"

            cursor.execute(sql, params)
            rows = cursor.fetchall()

            for item in self.tree.get_children():
                self.tree.delete(item)

            self.invoices.clear()

            for row in rows:
                invoice_id = row["invoice_id"]
                self.invoices[invoice_id] = row

                self.tree.insert(
                    "",
                    "end",
                    iid=str(invoice_id),
                    values=(
                        invoice_id,
                        row["pay_id"],
                        row["booking_id"],
                        row["customer_name"],
                        row["so_phong"],
                        self.format_money(row["tien_phong"]),
                        self.format_money(row["tien_dich_vu"]),
                        self.format_money(row["tong_tien"]),
                        row["ngay_lap"],
                        row["status"]
                    )
                )

        except Exception as e:
            messagebox.showerror(
                "Lỗi",
                f"Không thể tải danh sách hóa đơn:\n{e}"
            )

        finally:
            if cursor:
                cursor.close()
            connection.close()

    # ================= SELECT INVOICE =================
    def on_select(self, event=None):
        selected = self.tree.selection()

        if not selected:
            return

        invoice_id = int(selected[0])
        row = self.invoices.get(invoice_id)

        if not row:
            return

        self.selected_invoice = row

        values = {
            "id": row["invoice_id"],
            "pay_id": row["pay_id"],
            "booking_id": row["booking_id"],
            "customer": row["customer_name"],
            "room": row["so_phong"],
            "room_price": self.format_money(row["tien_phong"]),
            "service_price": self.format_money(row["tien_dich_vu"]),
            "total": self.format_money(row["tong_tien"]),
            "date": row["ngay_lap"],
            "method": row["method"],
            "status": row["status"]
        }

        for key, value in values.items():
            self.detail_vars[key].set(str(value))

    # ================= PREVIEW INVOICE =================
    def preview_invoice(self):
        if not self.selected_invoice:
            messagebox.showwarning(
                "Thông báo",
                "Vui lòng chọn một hóa đơn trong danh sách."
            )
            return

        row = self.selected_invoice

        window = tk.Toplevel(self.frame)
        window.title(f"Hóa đơn #{row['invoice_id']}")
        window.geometry("520x620")
        window.configure(bg="white")
        window.transient(self.frame.winfo_toplevel())

        tk.Label(
            window,
            text="H HOTEL",
            font=("Arial", 25, "bold"),
            fg="#D6A84F",
            bg="white"
        ).pack(pady=(25, 5))

        tk.Label(
            window,
            text="HÓA ĐƠN THANH TOÁN",
            font=("Arial", 17, "bold"),
            fg="#10233F",
            bg="white"
        ).pack(pady=5)

        tk.Label(
            window,
            text=f"Mã hóa đơn: #{row['invoice_id']}",
            font=("Arial", 11),
            bg="white"
        ).pack(pady=5)

        tk.Label(
            window,
            text=f"Ngày lập: {row['ngay_lap']}",
            font=("Arial", 10),
            bg="white"
        ).pack(pady=3)

        tk.Frame(
            window,
            bg="#D6A84F",
            height=2
        ).pack(fill="x", padx=30, pady=15)

        receipt = tk.Frame(window, bg="white")
        receipt.pack(fill="x", padx=40)

        details = [
            ("Mã thanh toán", row["pay_id"]),
            ("Mã booking", row["booking_id"]),
            ("Khách hàng", row["customer_name"]),
            ("Số phòng", row["so_phong"]),
            ("Phương thức", row["method"]),
            ("Trạng thái", row["status"])
        ]

        for label, value in details:
            line = tk.Frame(receipt, bg="white")
            line.pack(fill="x", pady=7)

            tk.Label(
                line,
                text=label,
                font=("Arial", 10),
                bg="white",
                fg="#64748B"
            ).pack(side="left")

            tk.Label(
                line,
                text=str(value),
                font=("Arial", 10, "bold"),
                bg="white",
                fg="#10233F"
            ).pack(side="right")

        tk.Frame(
            window,
            bg="#DCE2EA",
            height=1
        ).pack(fill="x", padx=30, pady=15)

        amounts = [
            ("Tiền phòng", row["tien_phong"]),
            ("Tiền dịch vụ", row["tien_dich_vu"])
        ]

        for label, amount in amounts:
            line = tk.Frame(window, bg="white")
            line.pack(fill="x", padx=40, pady=6)

            tk.Label(
                line,
                text=label,
                font=("Arial", 11),
                bg="white"
            ).pack(side="left")

            tk.Label(
                line,
                text=self.format_money(amount),
                font=("Arial", 11),
                bg="white"
            ).pack(side="right")

        tk.Frame(
            window,
            bg="#DCE2EA",
            height=1
        ).pack(fill="x", padx=30, pady=15)

        total_frame = tk.Frame(window, bg="white")
        total_frame.pack(fill="x", padx=40, pady=5)

        tk.Label(
            total_frame,
            text="TỔNG THANH TOÁN",
            font=("Arial", 12, "bold"),
            bg="white",
            fg="#10233F"
        ).pack(side="left")

        tk.Label(
            total_frame,
            text=self.format_money(row["tong_tien"]),
            font=("Arial", 14, "bold"),
            bg="white",
            fg="#B8862D"
        ).pack(side="right")

        tk.Label(
            window,
            text="Cảm ơn quý khách đã sử dụng dịch vụ!",
            font=("Arial", 10, "italic"),
            fg="#8190A5",
            bg="white"
        ).pack(pady=25)

        tk.Button(
            window,
            text="ĐÓNG",
            font=("Arial", 10, "bold"),
            bg="#10233F",
            fg="white",
            relief="flat",
            cursor="hand2",
            command=window.destroy
        ).pack(ipadx=25, ipady=8, pady=10)

    # ================= CLEAR =================
    def clear_selection(self):
        self.tree.selection_remove(self.tree.selection())
        self.selected_invoice = None

        for var in self.detail_vars.values():
            var.set("")

    # ================= REFRESH =================
    def refresh(self):
        self.search_var.set("")
        self.status_var.set("Tất cả")
        self.clear_selection()
        self.load_invoices()

    # ================= FORMAT MONEY =================
    @staticmethod
    def format_money(value):
        if value is None:
            value = 0

        return f"{float(value):,.0f} đ"
