
import tkinter as tk
from tkinter import ttk, messagebox
from database import get_connection


# ==============================
# MÀU SẮC GIAO DIỆN
# ==============================

NAVY = "#101D32"
NAVY_LIGHT = "#1B2D49"
GOLD = "#C9A45C"
WHITE = "#FFFFFF"
BACKGROUND = "#F4F6F9"
TEXT = "#263449"
MUTED = "#8993A2"


class Dashboard:

    def __init__(self, parent):

        self.parent = parent

        self.frame = tk.Frame(
            parent,
            bg=BACKGROUND
        )

        self.frame.pack(
            fill="both",
            expand=True
        )

        self.create_interface()
        self.load_data()

    # ==============================
    # TẠO GIAO DIỆN
    # ==============================

    def create_interface(self):

        # Tiêu đề
        header = tk.Frame(
            self.frame,
            bg=BACKGROUND
        )
        header.pack(
            fill="x",
            padx=30,
            pady=(25, 15)
        )

        tk.Label(
            header,
            text="TỔNG QUAN",
            font=("Arial", 22, "bold"),
            fg=NAVY,
            bg=BACKGROUND
        ).pack(anchor="w")

        tk.Label(
            header,
            text="Tổng quan hoạt động khách sạn",
            font=("Arial", 11),
            fg=MUTED,
            bg=BACKGROUND
        ).pack(anchor="w", pady=5)

        # Khu vực thẻ thống kê
        self.stats_frame = tk.Frame(
            self.frame,
            bg=BACKGROUND
        )

        self.stats_frame.pack(
            fill="x",
            padx=25,
            pady=10
        )

        self.stat_values = {}

        cards = [
            ("customers", "KHÁCH HÀNG"),
            ("rooms", "TỔNG SỐ PHÒNG"),
            ("bookings", "ĐẶT PHÒNG"),
            ("revenue", "DOANH THU")
        ]

        for index, (key, title) in enumerate(cards):

            card = tk.Frame(
                self.stats_frame,
                bg=WHITE,
                highlightbackground="#E5E9EF",
                highlightthickness=1
            )

            card.grid(
                row=0,
                column=index,
                padx=7,
                sticky="nsew"
            )

            self.stats_frame.grid_columnconfigure(
                index,
                weight=1
            )

            tk.Label(
                card,
                text=title,
                font=("Arial", 10, "bold"),
                fg=MUTED,
                bg=WHITE
            ).pack(
                anchor="w",
                padx=18,
                pady=(18, 8)
            )

            value_label = tk.Label(
                card,
                text="0",
                font=("Arial", 23, "bold"),
                fg=GOLD,
                bg=WHITE
            )

            value_label.pack(
                anchor="w",
                padx=18,
                pady=(0, 18)
            )

            self.stat_values[key] = value_label

        # Khu vực thông tin
        content = tk.Frame(
            self.frame,
            bg=BACKGROUND
        )

        content.pack(
            fill="both",
            expand=True,
            padx=30,
            pady=20
        )

        # Trạng thái phòng
        room_panel = tk.Frame(
            content,
            bg=WHITE,
            highlightbackground="#E5E9EF",
            highlightthickness=1
        )

        room_panel.pack(
            side="left",
            fill="y",
            padx=(0, 10)
        )

        tk.Label(
            room_panel,
            text="TRẠNG THÁI PHÒNG",
            font=("Arial", 12, "bold"),
            fg=NAVY,
            bg=WHITE
        ).pack(
            anchor="w",
            padx=18,
            pady=18
        )

        self.room_text = tk.Text(
            room_panel,
            width=27,
            height=12,
            font=("Arial", 11),
            bg=WHITE,
            fg=TEXT,
            relief="flat",
            state="disabled"
        )

        self.room_text.pack(
            padx=15,
            pady=(0, 15)
        )

        # Danh sách booking
        booking_panel = tk.Frame(
            content,
            bg=WHITE,
            highlightbackground="#E5E9EF",
            highlightthickness=1
        )

        booking_panel.pack(
            side="left",
            fill="both",
            expand=True
        )

        tk.Label(
            booking_panel,
            text="ĐẶT PHÒNG GẦN ĐÂY",
            font=("Arial", 12, "bold"),
            fg=NAVY,
            bg=WHITE
        ).pack(
            anchor="w",
            padx=18,
            pady=18
        )

        columns = (
            "id",
            "customer",
            "room",
            "checkin",
            "checkout",
            "status"
        )

        self.booking_table = ttk.Treeview(
            booking_panel,
            columns=columns,
            show="headings",
            height=10
        )

        headings = {
            "id": "Mã",
            "customer": "Khách hàng",
            "room": "Phòng",
            "checkin": "Ngày nhận",
            "checkout": "Ngày trả",
            "status": "Trạng thái"
        }

        widths = {
            "id": 55,
            "customer": 145,
            "room": 65,
            "checkin": 95,
            "checkout": 95,
            "status": 125
        }

        for column in columns:

            self.booking_table.heading(
                column,
                text=headings[column]
            )

            self.booking_table.column(
                column,
                width=widths[column],
                anchor="center"
            )

        self.booking_table.pack(
            fill="both",
            expand=True,
            padx=12,
            pady=(0, 15)
        )

        # Nút làm mới
        refresh_button = tk.Button(
            header,
            text="LÀM MỚI DỮ LIỆU",
            font=("Arial", 10, "bold"),
            bg=NAVY,
            fg=WHITE,
            activebackground=GOLD,
            activeforeground=WHITE,
            relief="flat",
            padx=15,
            pady=9,
            cursor="hand2",
            command=self.load_data
        )

        refresh_button.pack(
            side="right",
            anchor="e"
        )

    # ==============================
    # LẤY DỮ LIỆU TỪ MYSQL
    # ==============================

    def load_data(self):

        connection = get_connection()

        if connection is None:
            messagebox.showerror(
                "Lỗi kết nối",
                "Không thể kết nối MySQL!"
            )
            return

        cursor = connection.cursor(
            dictionary=True
        )

        try:

            # Tổng khách hàng
            cursor.execute("""
                SELECT COUNT(*) AS total
                FROM khach
            """)

            customers = cursor.fetchone()["total"]

            # Tổng số phòng
            cursor.execute("""
                SELECT COUNT(*) AS total
                FROM phong
            """)

            rooms = cursor.fetchone()["total"]

            # Tổng booking
            cursor.execute("""
                SELECT COUNT(*) AS total
                FROM booking
            """)

            bookings = cursor.fetchone()["total"]

            # Doanh thu
            cursor.execute("""
                SELECT COALESCE(SUM(h.tong_tien), 0) AS revenue
                FROM hoadon h
                JOIN pay p ON h.pay_id = p.id
                WHERE p.status = 'THANH_CONG'
            """)

            revenue = cursor.fetchone()["revenue"]

            # Hiển thị số liệu
            self.stat_values["customers"].config(
                text=f"{customers:,}"
            )

            self.stat_values["rooms"].config(
                text=f"{rooms:,}"
            )

            self.stat_values["bookings"].config(
                text=f"{bookings:,}"
            )

            self.stat_values["revenue"].config(
                text=f"{float(revenue):,.0f} đ"
            )

            # Thống kê trạng thái phòng
            cursor.execute("""
                SELECT trang_thai, COUNT(*) AS total
                FROM phong
                GROUP BY trang_thai
            """)

            room_statistics = cursor.fetchall()

            self.room_text.config(state="normal")
            self.room_text.delete("1.0", tk.END)

            for item in room_statistics:

                self.room_text.insert(
                    tk.END,
                    f"{item['trang_thai']}: "
                    f"{item['total']} phòng\n\n"
                )

            self.room_text.config(state="disabled")

            # Booking gần đây
            cursor.execute("""
                SELECT
                    b.id,
                    k.ho_ten,
                    p.so_phong,
                    b.ngay_nhan,
                    b.ngay_tra,
                    b.trang_thai
                FROM booking b
                JOIN khach k ON b.khach_id = k.id
                JOIN phong p ON b.phong_id = p.id
                ORDER BY b.id DESC
                LIMIT 5
            """)

            recent_bookings = cursor.fetchall()

            # Xóa dữ liệu cũ
            for item in self.booking_table.get_children():
                self.booking_table.delete(item)

            # Hiển thị dữ liệu mới
            for booking in recent_bookings:

                self.booking_table.insert(
                    "",
                    tk.END,
                    values=(
                        booking["id"],
                        booking["ho_ten"],
                        booking["so_phong"],
                        booking["ngay_nhan"],
                        booking["ngay_tra"],
                        booking["trang_thai"]
                    )
                )

        except Exception as e:

            messagebox.showerror(
                "Lỗi Dashboard",
                str(e)
            )

        finally:

            cursor.close()
            connection.close()
