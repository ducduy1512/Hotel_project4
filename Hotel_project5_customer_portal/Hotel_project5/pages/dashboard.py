
import tkinter as tk
from tkinter import ttk, messagebox

from api_client import api_client, APIError


class DashboardPage:
    def __init__(self, parent):
        self.parent = parent

        self.frame = ttk.Frame(parent)
        self.frame.pack(fill="both", expand=True, padx=20, pady=20)

        self.create_widgets()
        self.load_dashboard()

    def create_widgets(self):
        title = ttk.Label(
            self.frame,
            text="TỔNG QUAN QUẢN LÝ KHÁCH SẠN",
            font=("Arial", 20, "bold")
        )
        title.pack(pady=(0, 5))

        subtitle = ttk.Label(
            self.frame,
            text="Theo dõi tình hình hoạt động của khách sạn",
            font=("Arial", 10)
        )
        subtitle.pack(pady=(0, 20))

        # Khu vực các thẻ thống kê
        cards_frame = ttk.Frame(self.frame)
        cards_frame.pack(fill="x", pady=10)

        self.stat_labels = {}

        cards = [
            ("rooms", "TỔNG SỐ PHÒNG", "0"),
            ("available", "PHÒNG SẴN SÀNG", "0"),
            ("customers", "KHÁCH HÀNG", "0"),
            ("bookings", "TỔNG BOOKING", "0"),
            ("payments", "TỔNG THANH TOÁN", "0"),
            ("revenue", "DOANH THU", "0 VNĐ")
        ]

        for index, (key, heading, initial) in enumerate(cards):
            row = index // 3
            column = index % 3

            card = ttk.LabelFrame(
                cards_frame,
                text=heading,
                padding=15
            )
            card.grid(
                row=row,
                column=column,
                padx=8,
                pady=8,
                sticky="nsew"
            )

            value_label = ttk.Label(
                card,
                text=initial,
                font=("Arial", 18, "bold")
            )
            value_label.pack(pady=10)

            self.stat_labels[key] = value_label
            cards_frame.columnconfigure(column, weight=1)

        # Thông tin bổ sung
        info_frame = ttk.LabelFrame(
            self.frame,
            text="Tình hình thanh toán",
            padding=15
        )
        info_frame.pack(fill="x", pady=20)

        self.success_payment_label = ttk.Label(
            info_frame,
            text="Thanh toán thành công: 0",
            font=("Arial", 11, "bold")
        )
        self.success_payment_label.pack(anchor="w", pady=5)

        self.pending_payment_label = ttk.Label(
            info_frame,
            text="Đang chờ thanh toán: 0",
            font=("Arial", 11, "bold")
        )
        self.pending_payment_label.pack(anchor="w", pady=5)

        # Nút cập nhật
        button_frame = ttk.Frame(self.frame)
        button_frame.pack(fill="x", pady=10)

        ttk.Button(
            button_frame,
            text="CẬP NHẬT DỮ LIỆU",
            command=self.load_dashboard
        ).pack(side="left", padx=5)

        self.status_label = ttk.Label(
            button_frame,
            text="",
            foreground="gray"
        )
        self.status_label.pack(side="left", padx=15)

    @staticmethod
    def extract_list(response):
        if isinstance(response, list):
            return response

        if isinstance(response, dict):
            for key in (
                    "data",
                    "items",
                    "results",
                    "payments",
                    "services",
                    "invoices"
            ):
                value = response.get(key)

                if isinstance(value, list):
                    return value

        return []

    @staticmethod
    def get_status(item, keys):
        for key in keys:
            value = item.get(key)
            if value is not None:
                return str(value).upper()
        return ""

    @staticmethod
    def get_amount(item):
        try:
            return float(item.get("so_tien", 0) or 0)
        except (ValueError, TypeError):
            return 0

    @staticmethod
    def format_money(value):
        return f"{value:,.0f} VNĐ"

    def load_dashboard(self):
        errors = []

        # 1. Lấy danh sách phòng
        try:
            rooms_response = api_client.get("/api/rooms/")
            rooms = self.extract_list(rooms_response)

            total_rooms = len(rooms)

            available_rooms = sum(
                1 for room in rooms
                if self.get_status(
                    room, ["trang_thai", "status"]
                ) == "SAN_SANG"
            )

            self.stat_labels["rooms"].config(
                text=str(total_rooms)
            )

            self.stat_labels["available"].config(
                text=str(available_rooms)
            )

        except APIError as error:
            errors.append("Phòng: " + str(error))

        # 2. Lấy danh sách khách hàng
        try:
            customers_response = api_client.get(
                "/api/customers/"
            )
            customers = self.extract_list(customers_response)

            self.stat_labels["customers"].config(
                text=str(len(customers))
            )

        except APIError as error:
            errors.append("Khách hàng: " + str(error))

        # 3. Lấy danh sách booking
        try:
            bookings_response = api_client.get(
                "/api/bookings/"
            )
            bookings = self.extract_list(bookings_response)

            self.stat_labels["bookings"].config(
                text=str(len(bookings))
            )

        except APIError as error:
            errors.append("Booking: " + str(error))

        # 4. Lấy danh sách thanh toán
        try:
            payments_response = api_client.get(
                "/api/payments/"
            )
            payments = self.extract_list(payments_response)

            total_payments = len(payments)

            successful_payments = [
                payment for payment in payments
                if self.get_status(
                    payment, ["status", "trang_thai"]
                ) == "THANH_CONG"
            ]

            pending_payments = [
                payment for payment in payments
                if self.get_status(
                    payment, ["status", "trang_thai"]
                ) == "CHO_THANH_TOAN"
            ]

            revenue = sum(
                self.get_amount(payment)
                for payment in successful_payments
            )

            self.stat_labels["payments"].config(
                text=str(total_payments)
            )

            self.stat_labels["revenue"].config(
                text=self.format_money(revenue)
            )

            self.success_payment_label.config(
                text=(
                    "Thanh toán thành công: "
                    + str(len(successful_payments))
                )
            )

            self.pending_payment_label.config(
                text=(
                    "Đang chờ thanh toán: "
                    + str(len(pending_payments))
                )
            )

        except APIError as error:
            errors.append("Thanh toán: " + str(error))

        if errors:
            self.status_label.config(
                text="Một số dữ liệu chưa tải được."
            )

            messagebox.showwarning(
                "Cảnh báo dữ liệu",
                "Không thể tải đầy đủ dữ liệu Dashboard:\n\n"
                + "\n".join(errors)
            )
        else:
            self.status_label.config(
                text="Dữ liệu đã được cập nhật thành công."
            )
