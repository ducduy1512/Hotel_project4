
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from database import get_connection


class ReportsPage:
    def __init__(self, parent):
        self.parent = parent

        self.frame = tk.Frame(parent, bg="#F3F5F9")
        self.frame.pack(fill="both", expand=True)

        self.start_var = tk.StringVar(value="2026-11-01")
        self.end_var = tk.StringVar(value="2026-11-30")

        self.total_revenue_var = tk.StringVar(value="0 đ")
        self.total_bookings_var = tk.StringVar(value="0")
        self.total_customers_var = tk.StringVar(value="0")
        self.success_payments_var = tk.StringVar(value="0")

        self.build_ui()
        self.load_reports()

    # ==================================================
    # GIAO DIỆN
    # ==================================================
    def build_ui(self):

        # HEADER
        header = tk.Frame(self.frame, bg="#F3F5F9")
        header.pack(fill="x", padx=25, pady=(20, 10))

        tk.Label(
            header,
            text="QUẢN LÝ BÁO CÁO",
            font=("Arial", 23, "bold"),
            fg="#10233F",
            bg="#F3F5F9"
        ).pack(anchor="w")

        tk.Label(
            header,
            text="Thống kê doanh thu, đặt phòng và hiệu quả kinh doanh",
            font=("Arial", 11),
            fg="#8190A5",
            bg="#F3F5F9"
        ).pack(anchor="w", pady=(5, 0))

        # FILTER
        filter_frame = tk.Frame(
            self.frame,
            bg="white",
            highlightbackground="#DCE2EA",
            highlightthickness=1
        )
        filter_frame.pack(fill="x", padx=25, pady=10)

        tk.Label(
            filter_frame,
            text="Từ ngày:",
            font=("Arial", 10, "bold"),
            bg="white",
            fg="#10233F"
        ).pack(side="left", padx=(15, 5), pady=15)

        ttk.Entry(
            filter_frame,
            textvariable=self.start_var,
            width=15
        ).pack(side="left", padx=5)

        tk.Label(
            filter_frame,
            text="Đến ngày:",
            font=("Arial", 10, "bold"),
            bg="white",
            fg="#10233F"
        ).pack(side="left", padx=(15, 5))

        ttk.Entry(
            filter_frame,
            textvariable=self.end_var,
            width=15
        ).pack(side="left", padx=5)

        tk.Label(
            filter_frame,
            text="Định dạng: YYYY-MM-DD",
            font=("Arial", 9),
            fg="#8190A5",
            bg="white"
        ).pack(side="left", padx=8)

        tk.Button(
            filter_frame,
            text="THỐNG KÊ",
            font=("Arial", 10, "bold"),
            bg="#10233F",
            fg="white",
            relief="flat",
            cursor="hand2",
            command=self.load_reports
        ).pack(side="left", padx=15, ipadx=12, ipady=8)

        tk.Button(
            filter_frame,
            text="LÀM MỚI",
            font=("Arial", 10, "bold"),
            bg="#D6A84F",
            fg="#10233F",
            relief="flat",
            cursor="hand2",
            command=self.reset_filter
        ).pack(side="left", padx=5, ipadx=12, ipady=8)

        # KPI CARDS
        cards_frame = tk.Frame(self.frame, bg="#F3F5F9")
        cards_frame.pack(fill="x", padx=25, pady=10)

        cards = [
            ("TỔNG DOANH THU", self.total_revenue_var, "#D6A84F"),
            ("TỔNG BOOKING", self.total_bookings_var, "#2878B5"),
            ("KHÁCH HÀNG", self.total_customers_var, "#24966D"),
            ("THANH TOÁN THÀNH CÔNG", self.success_payments_var, "#7A65B5")
        ]

        for index, (title, variable, color) in enumerate(cards):
            card = tk.Frame(
                cards_frame,
                bg="white",
                highlightbackground="#DCE2EA",
                highlightthickness=1
            )
            card.grid(
                row=0,
                column=index,
                sticky="nsew",
                padx=5
            )

            tk.Label(
                card,
                text=title,
                font=("Arial", 9, "bold"),
                fg="#8190A5",
                bg="white"
            ).pack(anchor="w", padx=12, pady=(12, 5))

            tk.Label(
                card,
                textvariable=variable,
                font=("Arial", 17, "bold"),
                fg=color,
                bg="white"
            ).pack(anchor="w", padx=12, pady=(0, 12))

            cards_frame.columnconfigure(index, weight=1)

        # NOTEBOOK
        notebook_frame = tk.Frame(self.frame, bg="#F3F5F9")
        notebook_frame.pack(
            fill="both",
            expand=True,
            padx=25,
            pady=(5, 20)
        )

        self.notebook = ttk.Notebook(notebook_frame)
        self.notebook.pack(fill="both", expand=True)

        self.revenue_tab = tk.Frame(self.notebook, bg="white")
        self.booking_tab = tk.Frame(self.notebook, bg="white")
        self.customer_tab = tk.Frame(self.notebook, bg="white")
        self.room_tab = tk.Frame(self.notebook, bg="white")

        self.notebook.add(
            self.revenue_tab,
            text="Doanh thu theo tháng"
        )
        self.notebook.add(
            self.booking_tab,
            text="Thống kê đặt phòng"
        )
        self.notebook.add(
            self.customer_tab,
            text="Top khách hàng"
        )
        self.notebook.add(
            self.room_tab,
            text="Hiệu suất phòng"
        )

        # TABLES
        self.revenue_tree = self.create_table(
            self.revenue_tab,
            [
                ("month", "Tháng", 180),
                ("payments", "Số giao dịch", 180),
                ("revenue", "Doanh thu", 220)
            ]
        )

        self.booking_tree = self.create_table(
            self.booking_tab,
            [
                ("status", "Trạng thái booking", 250),
                ("quantity", "Số lượng", 180)
            ]
        )

        self.customer_tree = self.create_table(
            self.customer_tab,
            [
                ("id", "Mã khách", 100),
                ("name", "Khách hàng", 220),
                ("bookings", "Số booking", 150),
                ("spending", "Tổng chi tiêu", 220)
            ]
        )

        self.room_tree = self.create_table(
            self.room_tab,
            [
                ("room", "Số phòng", 130),
                ("type", "Loại phòng", 200),
                ("bookings", "Số lượt đặt", 150),
                ("revenue", "Doanh thu", 220)
            ]
        )

    # ==================================================
    # TẠO BẢNG
    # ==================================================
    def create_table(self, parent, columns):

        container = tk.Frame(parent, bg="white")
        container.pack(fill="both", expand=True, padx=12, pady=12)

        tree = ttk.Treeview(
            container,
            columns=[item[0] for item in columns],
            show="headings",
            height=15
        )

        for key, title, width in columns:
            tree.heading(key, text=title)
            tree.column(
                key,
                width=width,
                minwidth=80,
                anchor="center"
            )

        scrollbar_y = ttk.Scrollbar(
            container,
            orient="vertical",
            command=tree.yview
        )

        scrollbar_x = ttk.Scrollbar(
            container,
            orient="horizontal",
            command=tree.xview
        )

        tree.configure(
            yscrollcommand=scrollbar_y.set,
            xscrollcommand=scrollbar_x.set
        )

        tree.grid(row=0, column=0, sticky="nsew")
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        scrollbar_x.grid(row=1, column=0, sticky="ew")

        container.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)

        return tree

    # ==================================================
    # KIỂM TRA NGÀY
    # ==================================================
    def validate_dates(self):

        start = self.start_var.get().strip()
        end = self.end_var.get().strip()

        try:
            start_date = datetime.strptime(start, "%Y-%m-%d").date()
            end_date = datetime.strptime(end, "%Y-%m-%d").date()

            if start_date > end_date:
                messagebox.showwarning(
                    "Ngày không hợp lệ",
                    "Ngày bắt đầu không được lớn hơn ngày kết thúc."
                )
                return None

            return start_date, end_date

        except ValueError:
            messagebox.showwarning(
                "Ngày không hợp lệ",
                "Vui lòng nhập ngày theo định dạng YYYY-MM-DD."
            )
            return None

    # ==================================================
    # XÓA DỮ LIỆU BẢNG
    # ==================================================
    @staticmethod
    def clear_tree(tree):

        for item in tree.get_children():
            tree.delete(item)

    # ==================================================
    # TẢI BÁO CÁO
    # ==================================================
    def load_reports(self):

        dates = self.validate_dates()

        if dates is None:
            return

        start_date, end_date = dates

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

            self.clear_all_tables()

            # ------------------------------------------
            # 1. TỔNG DOANH THU
            # Chỉ tính hóa đơn có thanh toán thành công.
            # ------------------------------------------
            cursor.execute(
                """
                SELECT
                    COALESCE(SUM(h.tong_tien), 0) AS total_revenue
                FROM hoadon h
                JOIN pay p ON h.pay_id = p.id
                WHERE p.status = 'THANH_CONG'
                  AND DATE(p.ngay_thanh_toan)
                      BETWEEN %s AND %s
                """,
                (start_date, end_date)
            )

            revenue_result = cursor.fetchone()

            total_revenue = revenue_result["total_revenue"] or 0

            self.total_revenue_var.set(
                self.format_money(total_revenue)
            )

            # ------------------------------------------
            # 2. TỔNG BOOKING
            # ------------------------------------------
            cursor.execute(
                """
                SELECT COUNT(*) AS total_bookings
                FROM booking
                WHERE ngay_nhan BETWEEN %s AND %s
                """,
                (start_date, end_date)
            )

            booking_result = cursor.fetchone()

            self.total_bookings_var.set(
                str(booking_result["total_bookings"])
            )

            # ------------------------------------------
            # 3. SỐ KHÁCH HÀNG CÓ BOOKING
            # ------------------------------------------
            cursor.execute(
                """
                SELECT COUNT(DISTINCT khach_id) AS total_customers
                FROM booking
                WHERE ngay_nhan BETWEEN %s AND %s
                """
                ,
                (start_date, end_date)
            )

            customer_result = cursor.fetchone()

            self.total_customers_var.set(
                str(customer_result["total_customers"])
            )

            # ------------------------------------------
            # 4. SỐ THANH TOÁN THÀNH CÔNG
            # ------------------------------------------
            cursor.execute(
                """
                SELECT COUNT(*) AS total_payments
                FROM pay
                WHERE status = 'THANH_CONG'
                  AND DATE(ngay_thanh_toan)
                      BETWEEN %s AND %s
                """,
                (start_date, end_date)
            )

            payment_result = cursor.fetchone()

            self.success_payments_var.set(
                str(payment_result["total_payments"])
            )

            # ------------------------------------------
            # 5. DOANH THU THEO THÁNG
            # ------------------------------------------
            cursor.execute(
                """
                SELECT
                    DATE_FORMAT(p.ngay_thanh_toan, '%Y-%m') AS month,
                    COUNT(p.id) AS payments,
                    COALESCE(SUM(h.tong_tien), 0) AS revenue
                FROM pay p
                JOIN hoadon h ON h.pay_id = p.id
                WHERE p.status = 'THANH_CONG'
                  AND DATE(p.ngay_thanh_toan)
                      BETWEEN %s AND %s
                GROUP BY DATE_FORMAT(p.ngay_thanh_toan, '%Y-%m')
                ORDER BY month
                """,
                (start_date, end_date)
            )

            for row in cursor.fetchall():
                self.revenue_tree.insert(
                    "",
                    "end",
                    values=(
                        row["month"],
                        row["payments"],
                        self.format_money(row["revenue"])
                    )
                )

            # ------------------------------------------
            # 6. THỐNG KÊ TRẠNG THÁI BOOKING
            # ------------------------------------------
            cursor.execute(
                """
                SELECT
                    trang_thai AS status,
                    COUNT(*) AS quantity
                FROM booking
                WHERE ngay_nhan BETWEEN %s AND %s
                GROUP BY trang_thai
                ORDER BY quantity DESC
                """,
                (start_date, end_date)
            )

            for row in cursor.fetchall():
                self.booking_tree.insert(
                    "",
                    "end",
                    values=(
                        row["status"],
                        row["quantity"]
                    )
                )

            # ------------------------------------------
            # 7. TOP KHÁCH HÀNG
            # ------------------------------------------
            cursor.execute(
                """
                SELECT
                    k.id,
                    k.ho_ten AS name,
                    COUNT(DISTINCT b.id) AS bookings,
                    COALESCE(SUM(h.tong_tien), 0) AS spending
                FROM khach k
                JOIN booking b ON b.khach_id = k.id
                LEFT JOIN pay p
                    ON p.booking_id = b.id
                    AND p.status = 'THANH_CONG'
                LEFT JOIN hoadon h ON h.pay_id = p.id
                WHERE b.ngay_nhan BETWEEN %s AND %s
                GROUP BY k.id, k.ho_ten
                ORDER BY spending DESC
                LIMIT 10
                """,
                (start_date, end_date)
            )

            for row in cursor.fetchall():
                self.customer_tree.insert(
                    "",
                    "end",
                    values=(
                        row["id"],
                        row["name"],
                        row["bookings"],
                        self.format_money(row["spending"])
                    )
                )

            # ------------------------------------------
            # 8. HIỆU SUẤT PHÒNG
            # ------------------------------------------
            cursor.execute(
                """
                SELECT
                    ph.so_phong AS room,
                    lp.ten AS room_type,
                    COUNT(DISTINCT b.id) AS bookings,
                    COALESCE(SUM(
                        CASE
                            WHEN p.status = 'THANH_CONG'
                            THEN h.tong_tien
                            ELSE 0
                        END
                    ), 0) AS revenue
                FROM phong ph
                JOIN loaiphong lp
                    ON ph.loai_phong_id = lp.id
                LEFT JOIN booking b
                    ON b.phong_id = ph.id
                    AND b.ngay_nhan BETWEEN %s AND %s
                LEFT JOIN pay p
                    ON p.booking_id = b.id
                LEFT JOIN hoadon h
                    ON h.pay_id = p.id
                GROUP BY ph.id, ph.so_phong, lp.ten
                ORDER BY bookings DESC, ph.so_phong
                """,
                (start_date, end_date)
            )

            for row in cursor.fetchall():
                self.room_tree.insert(
                    "",
                    "end",
                    values=(
                        row["room"],
                        row["room_type"],
                        row["bookings"],
                        self.format_money(row["revenue"])
                    )
                )

        except Exception as e:
            messagebox.showerror(
                "Lỗi báo cáo",
                f"Không thể tải báo cáo:\n{e}"
            )

        finally:
            if cursor:
                cursor.close()

            connection.close()

    # ==================================================
    # XÓA TẤT CẢ BẢNG
    # ==================================================
    def clear_all_tables(self):

        self.clear_tree(self.revenue_tree)
        self.clear_tree(self.booking_tree)
        self.clear_tree(self.customer_tree)
        self.clear_tree(self.room_tree)

        self.total_revenue_var.set("0 đ")
        self.total_bookings_var.set("0")
        self.total_customers_var.set("0")
        self.success_payments_var.set("0")

    # ==================================================
    # LÀM MỚI
    # ==================================================
    def reset_filter(self):

        self.start_var.set("2026-11-01")
        self.end_var.set("2026-11-30")

        self.load_reports()

    # ==================================================
    # ĐỊNH DẠNG TIỀN
    # ==================================================
    @staticmethod
    def format_money(value):

        if value is None:
            value = 0

        return f"{float(value):,.0f} đ"
