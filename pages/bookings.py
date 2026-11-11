
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

from database import get_connection


class BookingsPage:
    def __init__(self, parent):
        self.parent = parent

        self.navy = "#101F35"
        self.gold = "#D5AD5B"
        self.white = "#FFFFFF"
        self.background = "#F4F6F9"
        self.gray = "#8793A5"

        self.selected_id = None
        self.customer_map = {}
        self.room_map = {}

        self.build_ui()
        self.load_combos()
        self.load_bookings()

    def build_ui(self):
        # Tiêu đề
        tk.Label(
            self.parent,
            text="QUẢN LÝ ĐẶT PHÒNG",
            font=("Arial", 24, "bold"),
            fg=self.navy,
            bg=self.background
        ).pack(anchor="w", padx=35, pady=(30, 5))

        tk.Label(
            self.parent,
            text="Quản lý thông tin đặt phòng và lịch lưu trú của khách hàng",
            font=("Arial", 11),
            fg=self.gray,
            bg=self.background
        ).pack(anchor="w", padx=35, pady=(0, 20))

        # Tìm kiếm và lọc
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
            width=25
        )
        self.search_entry.pack(side="left", padx=5, pady=12)
        self.search_entry.bind(
            "<KeyRelease>",
            lambda event: self.load_bookings()
        )

        tk.Label(
            search_frame,
            text="Trạng thái:",
            font=("Arial", 10, "bold"),
            bg=self.white,
            fg=self.navy
        ).pack(side="left", padx=(15, 8))

        self.status_filter = ttk.Combobox(
            search_frame,
            values=[
                "Tất cả",
                "CHO_XAC_NHAN",
                "DA_XAC_NHAN",
                "DA_HUY",
                "HOAN_THANH"
            ],
            state="readonly",
            width=20,
            font=("Arial", 10)
        )
        self.status_filter.set("Tất cả")
        self.status_filter.pack(side="left", padx=5, pady=12)
        self.status_filter.bind(
            "<<ComboboxSelected>>",
            lambda event: self.load_bookings()
        )

        tk.Button(
            search_frame,
            text="LÀM MỚI",
            command=self.refresh_page,
            font=("Arial", 10, "bold"),
            bg=self.navy,
            fg=self.white,
            relief="flat",
            padx=18,
            pady=9,
            cursor="hand2"
        ).pack(side="left", padx=15)

        # Biểu mẫu đặt phòng
        form_frame = tk.LabelFrame(
            self.parent,
            text=" THÔNG TIN ĐẶT PHÒNG ",
            font=("Arial", 12, "bold"),
            bg=self.white,
            fg=self.navy,
            padx=15,
            pady=15
        )
        form_frame.pack(fill="x", padx=35, pady=(0, 18))

        for col in range(4):
            form_frame.columnconfigure(col, weight=1)

        labels = [
            "Khách hàng",
            "Phòng",
            "Ngày nhận (YYYY-MM-DD)",
            "Ngày trả (YYYY-MM-DD)"
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

        self.customer_combo = ttk.Combobox(
            form_frame,
            state="readonly",
            font=("Arial", 10)
        )
        self.customer_combo.grid(
            row=1, column=0,
            sticky="ew", padx=8, pady=(0, 15), ipady=4
        )

        self.room_combo = ttk.Combobox(
            form_frame,
            state="readonly",
            font=("Arial", 10)
        )
        self.room_combo.grid(
            row=1, column=1,
            sticky="ew", padx=8, pady=(0, 15), ipady=4
        )

        self.checkin_entry = tk.Entry(
            form_frame,
            font=("Arial", 10)
        )
        self.checkin_entry.grid(
            row=1, column=2,
            sticky="ew", padx=8, pady=(0, 15), ipady=5
        )

        self.checkout_entry = tk.Entry(
            form_frame,
            font=("Arial", 10)
        )
        self.checkout_entry.grid(
            row=1, column=3,
            sticky="ew", padx=8, pady=(0, 15), ipady=5
        )

        # Nút chức năng
        button_frame = tk.Frame(form_frame, bg=self.white)
        button_frame.grid(
            row=2, column=0,
            columnspan=4, sticky="w", padx=8
        )

        tk.Button(
            button_frame,
            text="TẠO ĐẶT PHÒNG",
            command=self.add_booking,
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
            text="HỦY ĐẶT PHÒNG",
            command=self.cancel_booking,
            bg="#C0392B",
            fg=self.white,
            font=("Arial", 10, "bold"),
            relief="flat",
            padx=18,
            pady=10,
            cursor="hand2"
        ).pack(side="left", padx=10)

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

        # Danh sách booking
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
            text="DANH SÁCH ĐẶT PHÒNG",
            font=("Arial", 13, "bold"),
            fg=self.navy,
            bg=self.white
        ).pack(anchor="w", padx=18, pady=12)

        columns = (
            "id", "customer", "room",
            "checkin", "checkout", "status"
        )

        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings"
        )

        headings = {
            "id": "Mã booking",
            "customer": "Khách hàng",
            "room": "Số phòng",
            "checkin": "Ngày nhận",
            "checkout": "Ngày trả",
            "status": "Trạng thái"
        }

        widths = {
            "id": 90,
            "customer": 220,
            "room": 100,
            "checkin": 130,
            "checkout": 130,
            "status": 170
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
            padx=(12, 0),
            pady=(0, 0)
        )

        scrollbar_y.pack(side="right", fill="y")
        scrollbar_x.pack(side="bottom", fill="x")

        self.tree.bind(
            "<<TreeviewSelect>>",
            self.select_booking
        )

    # Tải danh sách khách hàng và phòng vào Combobox
    def load_combos(self):
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

            cursor.execute("""
                SELECT id, ho_ten
                FROM khach
                ORDER BY ho_ten
            """)

            self.customer_map = {}

            for customer_id, name in cursor.fetchall():
                display = f"{customer_id} - {name}"
                self.customer_map[display] = customer_id

            self.customer_combo["values"] = list(
                self.customer_map.keys()
            )

            cursor.execute("""
                SELECT p.id, p.so_phong, lp.ten
                FROM phong p
                JOIN loaiphong lp ON p.loai_phong_id = lp.id
                WHERE p.trang_thai <> 'BAO_TRI'
                ORDER BY p.so_phong
            """)

            self.room_map = {}

            for room_id, room_number, room_type in cursor.fetchall():
                display = f"{room_number} - {room_type}"
                self.room_map[display] = room_id

            self.room_combo["values"] = list(
                self.room_map.keys()
            )

        except Exception as e:
            messagebox.showerror("Lỗi", str(e))

        finally:
            if cursor:
                cursor.close()
            connection.close()

    # Tải danh sách đặt phòng
    def load_bookings(self):
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
                    b.id,
                    k.ho_ten,
                    p.so_phong,
                    b.ngay_nhan,
                    b.ngay_tra,
                    b.trang_thai
                FROM booking b
                JOIN khach k ON b.khach_id = k.id
                JOIN phong p ON b.phong_id = p.id
                WHERE (
                    k.ho_ten LIKE %s
                    OR p.so_phong LIKE %s
                    OR CAST(b.id AS CHAR) LIKE %s
                )
            """

            params = [
                f"%{keyword}%",
                f"%{keyword}%",
                f"%{keyword}%"
            ]

            if status != "Tất cả":
                sql += " AND b.trang_thai = %s"
                params.append(status)

            sql += " ORDER BY b.id DESC"

            cursor.execute(sql, tuple(params))

            for row in cursor.fetchall():
                self.tree.insert(
                    "",
                    "end",
                    values=(
                        row[0],
                        row[1],
                        row[2],
                        row[3],
                        row[4],
                        row[5]
                    )
                )

        except Exception as e:
            messagebox.showerror("Lỗi", str(e))

        finally:
            if cursor:
                cursor.close()
            connection.close()

    # Chọn booking trong bảng
    def select_booking(self, event):
        selected = self.tree.selection()

        if not selected:
            return

        values = self.tree.item(selected[0], "values")
        self.selected_id = int(values[0])

        self.clear_inputs()

        self.checkin_entry.insert(0, str(values[3]))
        self.checkout_entry.insert(0, str(values[4]))

        # Hiển thị khách hàng và phòng tương ứng
        for display, customer_id in self.customer_map.items():
            if display.startswith(str(customer_id) + " - "):
                if display.endswith(str(values[1])):
                    self.customer_combo.set(display)
                    break

        for display in self.room_map:
            if display.split(" - ", 1)[0] == str(values[2]):
                self.room_combo.set(display)
                break

    # Kiểm tra ngày nhập
    def validate_dates(self):
        checkin = self.checkin_entry.get().strip()
        checkout = self.checkout_entry.get().strip()

        try:
            date_in = datetime.strptime(
                checkin, "%Y-%m-%d"
            ).date()

            date_out = datetime.strptime(
                checkout, "%Y-%m-%d"
            ).date()

            if date_out <= date_in:
                raise ValueError(
                    "Ngày trả phải sau ngày nhận."
                )

            return checkin, checkout

        except ValueError as e:
            messagebox.showwarning(
                "Ngày không hợp lệ",
                str(e) if str(e) else
                "Vui lòng nhập ngày theo định dạng YYYY-MM-DD."
            )
            return None

    # Tạo booking
    def add_booking(self):
        customer_display = self.customer_combo.get()
        room_display = self.room_combo.get()

        if customer_display not in self.customer_map:
            messagebox.showwarning(
                "Thiếu thông tin",
                "Vui lòng chọn khách hàng."
            )
            return

        if room_display not in self.room_map:
            messagebox.showwarning(
                "Thiếu thông tin",
                "Vui lòng chọn phòng."
            )
            return

        dates = self.validate_dates()

        if dates is None:
            return

        checkin, checkout = dates

        customer_id = self.customer_map[customer_display]
        room_id = self.room_map[room_display]

        confirm = messagebox.askyesno(
            "Xác nhận",
            "Bạn có muốn tạo booking này không?"
        )

        if not confirm:
            return

        connection = get_connection()

        if connection is None:
            messagebox.showerror("Lỗi", "Không thể kết nối MySQL.")
            return

        cursor = None

        try:
            cursor = connection.cursor()

            # Trigger trong MySQL sẽ kiểm tra lịch phòng bị trùng.
            cursor.execute("""
                INSERT INTO booking (
                    phong_id,
                    khach_id,
                    ngay_nhan,
                    ngay_tra,
                    trang_thai
                )
                VALUES (%s, %s, %s, %s, 'CHO_XAC_NHAN')
            """, (
                room_id,
                customer_id,
                checkin,
                checkout
            ))

            connection.commit()

            messagebox.showinfo(
                "Thành công",
                f"Tạo booking thành công!\nMã booking: {cursor.lastrowid}"
            )

            self.clear_form()
            self.load_bookings()
            self.load_combos()

        except Exception as e:
            connection.rollback()
            messagebox.showerror(
                "Không thể tạo booking",
                "Có thể phòng đã được đặt trong khoảng thời gian này "
                "hoặc dữ liệu không hợp lệ.\n\n"
                + str(e)
            )

        finally:
            if cursor:
                cursor.close()
            connection.close()

    # Hủy booking
    def cancel_booking(self):
        if self.selected_id is None:
            messagebox.showwarning(
                "Chưa chọn booking",
                "Vui lòng chọn booking cần hủy trong danh sách."
            )
            return

        confirm = messagebox.askyesno(
            "Xác nhận hủy",
            f"Bạn có chắc chắn muốn hủy booking "
            f"{self.selected_id} không?"
        )

        if not confirm:
            return

        connection = get_connection()

        if connection is None:
            messagebox.showerror("Lỗi", "Không thể kết nối MySQL.")
            return

        cursor = None

        try:
            cursor = connection.cursor()

            cursor.execute(
                "CALL sp_huy_booking(%s)",
                (self.selected_id,)
            )

            # Đọc các result set nếu procedure trả về
            while cursor.nextset():
                pass

            connection.commit()

            messagebox.showinfo(
                "Thành công",
                "Đã hủy booking."
            )

            self.clear_form()
            self.load_bookings()

        except Exception as e:
            connection.rollback()
            messagebox.showerror(
                "Không thể hủy booking",
                str(e)
            )

        finally:
            if cursor:
                cursor.close()
            connection.close()

    # Xóa nội dung biểu mẫu
    def clear_inputs(self):
        self.customer_combo.set("")
        self.room_combo.set("")
        self.checkin_entry.delete(0, tk.END)
        self.checkout_entry.delete(0, tk.END)

    def clear_form(self):
        self.selected_id = None
        self.clear_inputs()

        for item in self.tree.selection():
            self.tree.selection_remove(item)

    # Làm mới toàn bộ
    def refresh_page(self):
        self.search_entry.delete(0, tk.END)
        self.status_filter.set("Tất cả")
        self.clear_form()
        self.load_combos()
        self.load_bookings()
