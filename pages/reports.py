import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date

from api_client import api_client, APIError


class ReportsPage:

    def __init__(self, parent):
        self.parent = parent

        self.frame = ttk.Frame(parent)
        self.frame.pack(
            fill="both",
            expand=True,
            padx=15,
            pady=15
        )

        self.create_widgets()

        # Tự động tải báo cáo khi mở trang
        self.load_report()

    # =================================================
    # GIAO DIỆN
    # =================================================

    def create_widgets(self):

        title = ttk.Label(
            self.frame,
            text="THỐNG KÊ VÀ BÁO CÁO DOANH THU",
            font=("Arial", 18, "bold")
        )
        title.pack(pady=(0, 15))

        # ---------------------------------------------
        # BỘ LỌC NGÀY
        # ---------------------------------------------

        filter_frame = ttk.LabelFrame(
            self.frame,
            text="Điều kiện thống kê",
            padding=12
        )
        filter_frame.pack(fill="x", pady=5)

        ttk.Label(
            filter_frame,
            text="Từ ngày (YYYY-MM-DD):"
        ).grid(row=0, column=0, padx=5, pady=7)

        self.start_date_var = tk.StringVar(
            value=date.today().replace(day=1).isoformat()
        )

        ttk.Entry(
            filter_frame,
            textvariable=self.start_date_var,
            width=18
        ).grid(row=0, column=1, padx=5, pady=7)

        ttk.Label(
            filter_frame,
            text="Đến ngày (YYYY-MM-DD):"
        ).grid(row=0, column=2, padx=5, pady=7)

        self.end_date_var = tk.StringVar(
            value=date.today().isoformat()
        )

        ttk.Entry(
            filter_frame,
            textvariable=self.end_date_var,
            width=18
        ).grid(row=0, column=3, padx=5, pady=7)

        ttk.Button(
            filter_frame,
            text="Thống kê",
            command=self.load_report
        ).grid(row=0, column=4, padx=10, pady=7)

        ttk.Button(
            filter_frame,
            text="Hôm nay",
            command=self.today_report
        ).grid(row=0, column=5, padx=5, pady=7)

        ttk.Button(
            filter_frame,
            text="Làm mới",
            command=self.reset_report
        ).grid(row=0, column=6, padx=5, pady=7)

        # ---------------------------------------------
        # TỔNG QUAN DOANH THU
        # ---------------------------------------------

        summary_frame = ttk.LabelFrame(
            self.frame,
            text="Tổng quan doanh thu",
            padding=15
        )
        summary_frame.pack(fill="x", pady=12)

        self.revenue_label = self.create_summary_item(
            summary_frame,
            "Doanh thu thực thu",
            "0 VNĐ",
            0
        )

        self.payment_count_label = self.create_summary_item(
            summary_frame,
            "Số giao dịch",
            "0",
            1
        )

        self.success_count_label = self.create_summary_item(
            summary_frame,
            "Thanh toán thành công",
            "0",
            2
        )

        # ---------------------------------------------
        # BẢNG CHI TIẾT
        # ---------------------------------------------

        table_title = ttk.Label(
            self.frame,
            text="CHI TIẾT BÁO CÁO",
            font=("Arial", 12, "bold")
        )
        table_title.pack(anchor="w", pady=(10, 5))

        table_frame = ttk.Frame(self.frame)
        table_frame.pack(
            fill="both",
            expand=True
        )

        columns = (
            "booking_id",
            "so_phong",
            "ho_ten",
            "ngay_nhan",
            "ngay_tra",
            "tong_tien",
            "trang_thai"
        )

        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            height=14
        )

        headings = {
            "booking_id": "Booking ID",
            "so_phong": "Số phòng",
            "ho_ten": "Khách hàng",
            "ngay_nhan": "Ngày nhận",
            "ngay_tra": "Ngày trả",
            "tong_tien": "Doanh thu ròng",
            "trang_thai": "Trạng thái"
        }

        widths = {
            "booking_id": 90,
            "so_phong": 100,
            "ho_ten": 180,
            "ngay_nhan": 130,
            "ngay_tra": 130,
            "tong_tien": 150,
            "trang_thai": 180
        }

        for col in columns:
            self.tree.heading(
                col,
                text=headings[col]
            )

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
            self.frame,
            orient="horizontal",
            command=self.tree.xview
        )

        self.tree.configure(
            yscrollcommand=scrollbar_y.set,
            xscrollcommand=scrollbar_x.set
        )

        self.tree.pack(
            side="left",
            fill="both",
            expand=True
        )

        scrollbar_y.pack(
            side="right",
            fill="y"
        )

        scrollbar_x.pack(fill="x")

        # ---------------------------------------------
        # TRẠNG THÁI
        # ---------------------------------------------

        self.status_label = ttk.Label(
            self.frame,
            text="Chưa tải báo cáo.",
            foreground="gray"
        )

        self.status_label.pack(
            anchor="w",
            pady=8
        )

    # =================================================
    # TẠO Ô THỐNG KÊ
    # =================================================

    def create_summary_item(
        self,
        parent,
        title,
        value,
        column
    ):

        box = ttk.Frame(parent)

        box.grid(
            row=0,
            column=column,
            padx=20,
            pady=5,
            sticky="nsew"
        )

        ttk.Label(
            box,
            text=title,
            font=("Arial", 10)
        ).pack()

        value_label = ttk.Label(
            box,
            text=value,
            font=("Arial", 16, "bold")
        )

        value_label.pack(pady=5)

        parent.columnconfigure(
            column,
            weight=1
        )

        return value_label

    # =================================================
    # HÀM HỖ TRỢ
    # =================================================

    @staticmethod
    def format_money(value):

        try:
            return f"{float(value or 0):,.0f} VNĐ"

        except (ValueError, TypeError):
            return "0 VNĐ"

    @staticmethod
    def format_date(value):

        if value is None:
            return ""

        return str(value)[:10]

    @staticmethod
    def get_number(data, key):

        try:
            return float(data.get(key) or 0)

        except (ValueError, TypeError, AttributeError):
            return 0

    # =================================================
    # KIỂM TRA NGÀY
    # =================================================

    def validate_dates(self):

        start_text = self.start_date_var.get().strip()
        end_text = self.end_date_var.get().strip()

        try:
            start = date.fromisoformat(start_text)
            end = date.fromisoformat(end_text)

        except ValueError:
            raise ValueError(
                "Ngày không hợp lệ. "
                "Vui lòng nhập theo định dạng YYYY-MM-DD."
            )

        if start > end:
            raise ValueError(
                "Ngày bắt đầu không được lớn hơn ngày kết thúc."
            )

        return start_text, end_text

    # =================================================
    # TẢI BÁO CÁO TỪ API
    # =================================================

    def load_report(self):

        try:
            start_date, end_date = self.validate_dates()

            self.status_label.config(
                text="Đang tải dữ liệu báo cáo..."
            )

            self.frame.update_idletasks()

            response = api_client.get(
                "/api/reports/revenue",
                params={
                    "tu_ngay": start_date,
                    "den_ngay": end_date
                }
            )

            self.display_report(response)

        except ValueError as error:

            messagebox.showwarning(
                "Ngày không hợp lệ",
                str(error)
            )

        except APIError as error:

            self.status_label.config(
                text="Không thể tải báo cáo."
            )

            messagebox.showerror(
                "Lỗi tải báo cáo",
                str(error)
            )

    # =================================================
    # HIỂN THỊ BÁO CÁO
    # =================================================

    def display_report(self, response):

        if not isinstance(response, dict):

            messagebox.showerror(
                "Lỗi dữ liệu",
                "API trả về dữ liệu báo cáo không đúng định dạng."
            )
            return

        # ---------------------------------------------
        # 1. LẤY DỮ LIỆU THỐNG KÊ
        # ---------------------------------------------

        summary_list = response.get("data", [])

        if not isinstance(summary_list, list):
            summary_list = []

        summary = (
            summary_list[0]
            if summary_list and isinstance(summary_list[0], dict)
            else {}
        )

        total_success = self.get_number(
            summary,
            "tong_tien_thanh_cong"
        )

        total_refund = self.get_number(
            summary,
            "tong_tien_hoan"
        )

        actual_revenue = self.get_number(
            summary,
            "doanh_thu_thuc_thu"
        )

        success_count = self.get_number(
            summary,
            "so_giao_dich_thanh_cong"
        )

        refund_count = self.get_number(
            summary,
            "so_giao_dich_hoan_tien"
        )

        total_payment_count = (
            success_count + refund_count
        )

        # ---------------------------------------------
        # 2. CẬP NHẬT CÁC Ô TỔNG QUAN
        # ---------------------------------------------

        self.revenue_label.config(
            text=self.format_money(actual_revenue)
        )

        self.payment_count_label.config(
            text=f"{total_payment_count:,.0f}"
        )

        self.success_count_label.config(
            text=f"{success_count:,.0f}"
        )

        # ---------------------------------------------
        # 3. LẤY DANH SÁCH BOOKING CHI TIẾT
        # ---------------------------------------------

        details = response.get("details", [])

        if not isinstance(details, list):
            details = []

        # Xóa dữ liệu cũ
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Thêm dữ liệu mới
        for record in details:

            if not isinstance(record, dict):
                continue

            self.tree.insert(
                "",
                "end",
                values=(
                    record.get("booking_id", ""),
                    record.get("so_phong", ""),
                    record.get("ho_ten", ""),
                    self.format_date(
                        record.get("ngay_nhan")
                    ),
                    self.format_date(
                        record.get("ngay_tra")
                    ),
                    self.format_money(
                        record.get("tong_tien", 0)
                    ),
                    record.get("trang_thai", "")
                )
            )

        # ---------------------------------------------
        # 4. CẬP NHẬT TRẠNG THÁI
        # ---------------------------------------------

        self.status_label.config(
            text=(
                f"Đã tải báo cáo từ "
                f"{response.get('tu_ngay', '')} đến "
                f"{response.get('den_ngay', '')} | "
                f"{len(details)} booking | "
                f"Tiền thành công: {self.format_money(total_success)} | "
                f"Tiền hoàn: {self.format_money(total_refund)}"
            )
        )

    # =================================================
    # BÁO CÁO HÔM NAY
    # =================================================

    def today_report(self):

        today = date.today().isoformat()

        self.start_date_var.set(today)
        self.end_date_var.set(today)

        self.load_report()

    # =================================================
    # LÀM MỚI
    # =================================================

    def reset_report(self):

        self.start_date_var.set(
            date.today().replace(day=1).isoformat()
        )

        self.end_date_var.set(
            date.today().isoformat()
        )

        self.load_report()