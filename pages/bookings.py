
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

from api_client import api_client, APIError


class BookingsPage:
    def __init__(self, parent):
        self.parent = parent
        self.selected_id = None

        self.bookings = []
        self.customers = []
        self.rooms = []

        self.customer_map = {}
        self.room_map = {}

        self.navy = "#101F35"
        self.gold = "#D5AD5B"
        self.white = "#FFFFFF"
        self.background = "#F4F6F9"
        self.gray = "#8793A5"

        self.build_ui()
        self.load_reference_data()
        self.load_bookings()

    # =====================================================
    # GIAO DIỆN
    # =====================================================
    def build_ui(self):
        tk.Label(
            self.parent,
            text="QUẢN LÝ ĐẶT PHÒNG",
            font=("Arial", 24, "bold"),
            fg=self.navy,
            bg=self.background
        ).pack(anchor="w", padx=30, pady=(20, 5))

        tk.Label(
            self.parent,
            text="Tạo, cập nhật, tra cứu và hủy đặt phòng",
            font=("Arial", 11),
            fg=self.gray,
            bg=self.background
        ).pack(anchor="w", padx=30, pady=(0, 15))

        # ---------------- FORM ----------------
        form = tk.LabelFrame(
            self.parent,
            text=" THÔNG TIN ĐẶT PHÒNG ",
            font=("Arial", 11, "bold"),
            bg=self.white,
            fg=self.navy,
            padx=15,
            pady=12
        )
        form.pack(fill="x", padx=30, pady=(0, 15))

        for col in range(4):
            form.columnconfigure(col, weight=1)

        self.customer_var = tk.StringVar()
        self.room_var = tk.StringVar()
        self.checkin_var = tk.StringVar()
        self.checkout_var = tk.StringVar()
        self.status_var = tk.StringVar(value="CHO_XAC_NHAN")

        tk.Label(
            form, text="Khách hàng",
            bg=self.white, fg=self.navy
        ).grid(row=0, column=0, sticky="w", padx=8, pady=7)

        self.customer_combo = ttk.Combobox(
            form,
            textvariable=self.customer_var,
            state="readonly",
            width=28
        )
        self.customer_combo.grid(
            row=0, column=1, sticky="ew", padx=8, pady=7
        )

        tk.Label(
            form, text="Phòng",
            bg=self.white, fg=self.navy
        ).grid(row=0, column=2, sticky="w", padx=8, pady=7)

        self.room_combo = ttk.Combobox(
            form,
            textvariable=self.room_var,
            state="readonly",
            width=25
        )
        self.room_combo.grid(
            row=0, column=3, sticky="ew", padx=8, pady=7
        )

        tk.Label(
            form, text="Ngày nhận (YYYY-MM-DD)",
            bg=self.white, fg=self.navy
        ).grid(row=1, column=0, sticky="w", padx=8, pady=7)

        tk.Entry(
            form,
            textvariable=self.checkin_var,
            font=("Arial", 10)
        ).grid(row=1, column=1, sticky="ew", padx=8, pady=7)

        tk.Label(
            form, text="Ngày trả (YYYY-MM-DD)",
            bg=self.white, fg=self.navy
        ).grid(row=1, column=2, sticky="w", padx=8, pady=7)

        tk.Entry(
            form,
            textvariable=self.checkout_var,
            font=("Arial", 10)
        ).grid(row=1, column=3, sticky="ew", padx=8, pady=7)

        tk.Label(
            form, text="Trạng thái",
            bg=self.white, fg=self.navy
        ).grid(row=2, column=0, sticky="w", padx=8, pady=7)

        self.status_combo = ttk.Combobox(
            form,
            textvariable=self.status_var,
            values=[
                "CHO_XAC_NHAN",
                "DA_XAC_NHAN",
                "DA_HUY",
                "HOAN_THANH"
            ],
            state="readonly"
        )
        self.status_combo.grid(
            row=2, column=1, sticky="ew", padx=8, pady=7
        )

        # ---------------- BUTTONS ----------------
        button_frame = tk.Frame(
            self.parent,
            bg=self.background
        )
        button_frame.pack(fill="x", padx=30, pady=(0, 15))

        buttons = [
            ("KIỂM TRA PHÒNG TRỐNG", self.check_available_rooms, self.navy),
            ("THÊM BOOKING", self.add_booking, "#247A4B"),
            ("CẬP NHẬT", self.update_booking, "#2367A5"),
            ("HỦY BOOKING", self.cancel_booking, "#C0392B"),
            ("LÀM MỚI", self.clear_form, self.gray)
        ]

        for label, command, color in buttons:
            tk.Button(
                button_frame,
                text=label,
                command=command,
                bg=color,
                fg=self.white,
                font=("Arial", 9, "bold"),
                relief="flat",
                padx=12,
                pady=10,
                cursor="hand2"
            ).pack(side="left", padx=(0, 8))

        # ---------------- SEARCH ----------------
        search_frame = tk.Frame(
            self.parent,
            bg=self.white,
            highlightbackground="#DDE3EA",
            highlightthickness=1
        )
        search_frame.pack(fill="x", padx=30, pady=(0, 12))

        tk.Label(
            search_frame,
            text="Tìm kiếm:",
            bg=self.white,
            fg=self.navy,
            font=("Arial", 10, "bold")
        ).pack(side="left", padx=(15, 8), pady=12)

        self.search_entry = tk.Entry(
            search_frame,
            font=("Arial", 10),
            width=30
        )
        self.search_entry.pack(side="left", padx=5, pady=10)

        tk.Button(
            search_frame,
            text="TÌM",
            command=self.search_bookings,
            bg=self.navy,
            fg=self.white,
            relief="flat",
            padx=15,
            pady=7
        ).pack(side="left", padx=5)

        tk.Button(
            search_frame,
            text="HIỂN THỊ TẤT CẢ",
            command=self.load_bookings,
            bg=self.gray,
            fg=self.white,
            relief="flat",
            padx=15,
            pady=7
        ).pack(side="left", padx=5)

        # ---------------- TABLE ----------------
        table_frame = tk.Frame(
            self.parent,
            bg=self.white,
            highlightbackground="#DDE3EA",
            highlightthickness=1
        )
        table_frame.pack(
            fill="both",
            expand=True,
            padx=30,
            pady=(0, 15)
        )

        columns = (
            "id",
            "customer",
            "cccd",
            "room",
            "checkin",
            "checkout",
            "status"
        )

        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            height=10
        )

        headings = {
            "id": "Mã booking",
            "customer": "Khách hàng",
            "cccd": "CCCD",
            "room": "Số phòng",
            "checkin": "Ngày nhận",
            "checkout": "Ngày trả",
            "status": "Trạng thái"
        }

        widths = {
            "id": 85,
            "customer": 170,
            "cccd": 130,
            "room": 100,
            "checkin": 120,
            "checkout": 120,
            "status": 145
        }

        for col in columns:
            self.tree.heading(col, text=headings[col])
            self.tree.column(
                col,
                width=widths[col],
                anchor="center"
            )

        y_scroll = ttk.Scrollbar(
            table_frame,
            orient="vertical",
            command=self.tree.yview
        )

        x_scroll = ttk.Scrollbar(
            table_frame,
            orient="horizontal",
            command=self.tree.xview
        )

        self.tree.configure(
            yscrollcommand=y_scroll.set,
            xscrollcommand=x_scroll.set
        )

        self.tree.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(10, 0),
            pady=10
        )

        y_scroll.pack(side="right", fill="y", pady=10)
        x_scroll.pack(side="bottom", fill="x", padx=10)

        self.tree.bind(
            "<<TreeviewSelect>>",
            self.select_booking
        )

        self.status_label = tk.Label(
            self.parent,
            text="Sẵn sàng",
            font=("Arial", 10, "bold"),
            fg="#247A4B",
            bg=self.background,
            anchor="w"
        )
        self.status_label.pack(
            fill="x",
            padx=30,
            pady=(0, 10)
        )

    # =====================================================
    # HÀM TIỆN ÍCH
    # =====================================================
    def set_status(self, message, color="#247A4B"):
        self.status_label.config(
            text=message,
            fg=color
        )

    def extract_list(self, response):
        """
        Hỗ trợ API trả về:
        - Danh sách trực tiếp
        - {"data": [...]}
        - {"bookings": [...]}
        """
        if isinstance(response, list):
            return response

        if isinstance(response, dict):
            for key in ("data", "bookings", "rooms", "customers"):
                if isinstance(response.get(key), list):
                    return response[key]

        raise APIError("API không trả về danh sách dữ liệu hợp lệ.")

    def get_value(self, row, *keys, default=""):
        for key in keys:
            if row.get(key) is not None:
                return row[key]
        return default

    # =====================================================
    # TẢI KHÁCH HÀNG VÀ PHÒNG
    # =====================================================
    def load_reference_data(self):
        try:
            customer_response = api_client.get("/api/customers/")
            room_response = api_client.get("/api/rooms/")

            self.customers = self.extract_list(customer_response)
            self.rooms = self.extract_list(room_response)

            self.customer_map.clear()
            self.room_map.clear()

            customer_values = []

            for customer in self.customers:
                customer_id = self.get_value(
                    customer, "id", "khach_id"
                )

                if customer_id == "":
                    continue

                name = self.get_value(
                    customer, "ho_ten", "ten", default="Chưa có tên"
                )

                cccd = self.get_value(customer, "cccd")

                display = f"{customer_id} - {name} - {cccd}"

                self.customer_map[display] = int(customer_id)
                customer_values.append(display)

            room_values = []

            for room in self.rooms:
                room_id = self.get_value(
                    room, "id", "phong_id"
                )

                if room_id == "":
                    continue

                room_number = self.get_value(
                    room, "so_phong", default=str(room_id)
                )

                room_status = self.get_value(
                    room, "trang_thai"
                )

                display = f"{room_id} - Phòng {room_number} - {room_status}"

                self.room_map[display] = int(room_id)
                room_values.append(display)

            self.customer_combo["values"] = customer_values
            self.room_combo["values"] = room_values

        except (APIError, KeyError, TypeError, ValueError) as e:
            messagebox.showerror(
                "Lỗi tải dữ liệu",
                str(e)
            )

    # =====================================================
    # TẢI DANH SÁCH BOOKING
    # =====================================================
    def load_bookings(self):
        try:
            response = api_client.get("/api/bookings/")
            self.bookings = self.extract_list(response)

            self.display_bookings(self.bookings)

            self.set_status(
                f"Đã tải {len(self.bookings)} booking."
            )

        except (APIError, KeyError, TypeError, ValueError) as e:
            messagebox.showerror(
                "Lỗi tải booking",
                str(e)
            )
            self.set_status(str(e), "#C0392B")

    def display_bookings(self, rows):
        for item in self.tree.get_children():
            self.tree.delete(item)

        for row in rows:
            booking_id = self.get_value(
                row, "id", "booking_id"
            )

            customer_name = self.get_value(
                row, "ho_ten", "ten_khach", "khach_hang"
            )

            cccd = self.get_value(row, "cccd")

            room_number = self.get_value(
                row, "so_phong", "ten_phong", "phong_id"
            )

            checkin = self.get_value(
                row, "ngay_nhan", "checkin"
            )

            checkout = self.get_value(
                row, "ngay_tra", "checkout"
            )

            status = self.get_value(row, "trang_thai")

            self.tree.insert(
                "",
                "end",
                values=(
                    booking_id,
                    customer_name,
                    cccd,
                    room_number,
                    str(checkin)[:10],
                    str(checkout)[:10],
                    status
                )
            )

    # =====================================================
    # KIỂM TRA PHÒNG TRỐNG
    # =====================================================
    def check_available_rooms(self):
        dates = self.validate_dates()

        if dates is None:
            return

        checkin, checkout = dates

        try:
            response = api_client.get(
                "/api/bookings/available-rooms",
                params={
                    "ngay_nhan": checkin,
                    "ngay_tra": checkout
                }
            )

            available_rooms = self.extract_list(response)

            if not available_rooms:
                messagebox.showinfo(
                    "Kết quả",
                    "Không có phòng trống trong khoảng ngày đã chọn."
                )
                return

            displays = []
            new_map = {}

            for room in available_rooms:
                room_id = self.get_value(
                    room, "id", "phong_id"
                )

                room_number = self.get_value(
                    room, "so_phong", default=str(room_id)
                )

                display = f"{room_id} - Phòng {room_number}"

                new_map[display] = int(room_id)
                displays.append(display)

            self.room_map.update(new_map)
            self.room_combo["values"] = displays

            if displays:
                self.room_var.set(displays[0])

            messagebox.showinfo(
                "Phòng trống",
                f"Tìm thấy {len(displays)} phòng còn trống."
            )

            self.set_status(
                f"Tìm thấy {len(displays)} phòng trống."
            )

        except (APIError, KeyError, TypeError, ValueError) as e:
            messagebox.showerror(
                "Không thể kiểm tra phòng",
                str(e)
            )

    # =====================================================
    # KIỂM TRA NGÀY
    # =====================================================
    def validate_dates(self):
        checkin = self.checkin_var.get().strip()
        checkout = self.checkout_var.get().strip()

        if not checkin or not checkout:
            messagebox.showwarning(
                "Thiếu thông tin",
                "Vui lòng nhập ngày nhận và ngày trả."
            )
            return None

        try:
            date_in = datetime.strptime(checkin, "%Y-%m-%d").date()
            date_out = datetime.strptime(checkout, "%Y-%m-%d").date()

            if date_out <= date_in:
                raise ValueError

        except ValueError:
            messagebox.showwarning(
                "Ngày không hợp lệ",
                "Ngày phải theo định dạng YYYY-MM-DD và ngày trả phải sau ngày nhận."
            )
            return None

        return checkin, checkout

    # =====================================================
    # LẤY DỮ LIỆU FORM
    # =====================================================
    def get_form_data(self):
        customer_display = self.customer_var.get()
        room_display = self.room_var.get()

        if customer_display not in self.customer_map:
            messagebox.showwarning(
                "Thiếu khách hàng",
                "Vui lòng chọn khách hàng."
            )
            return None

        if room_display not in self.room_map:
            messagebox.showwarning(
                "Thiếu phòng",
                "Vui lòng chọn phòng."
            )
            return None

        dates = self.validate_dates()

        if dates is None:
            return None

        checkin, checkout = dates

        return {
            "phong_id": self.room_map[room_display],
            "khach_id": self.customer_map[customer_display],
            "ngay_nhan": checkin,
            "ngay_tra": checkout
        }

    # =====================================================
    # THÊM BOOKING
    # =====================================================
    def add_booking(self):
        payload = self.get_form_data()

        if payload is None:
            return

        try:
            result = api_client.post(
                "/api/bookings/",
                payload
            )

            messagebox.showinfo(
                "Thành công",
                result.get(
                    "message",
                    "Tạo booking thành công."
                )
            )

            self.clear_form()
            self.load_bookings()
            self.load_reference_data()

        except APIError as e:
            messagebox.showerror(
                "Không thể tạo booking",
                str(e)
            )

    # =====================================================
    # CHỌN BOOKING TRÊN BẢNG
    # =====================================================
    def select_booking(self, event=None):
        selected = self.tree.selection()

        if not selected:
            return

        values = self.tree.item(
            selected[0],
            "values"
        )

        if not values:
            return

        self.selected_id = int(values[0])

        booking = None

        for row in self.bookings:
            row_id = self.get_value(
                row, "id", "booking_id"
            )

            if str(row_id) == str(self.selected_id):
                booking = row
                break

        if booking is None:
            return

        customer_id = self.get_value(
            booking, "khach_id"
        )

        room_id = self.get_value(
            booking, "phong_id"
        )

        self.customer_var.set(
            self.find_display(self.customer_map, customer_id)
        )

        self.room_var.set(
            self.find_display(self.room_map, room_id)
        )

        self.checkin_var.set(
            str(self.get_value(
                booking, "ngay_nhan", "checkin"
            ))[:10]
        )

        self.checkout_var.set(
            str(self.get_value(
                booking, "ngay_tra", "checkout"
            ))[:10]
        )

        self.status_var.set(
            self.get_value(
                booking, "trang_thai",
                default="CHO_XAC_NHAN"
            )
        )

    def find_display(self, mapping, target_id):
        if target_id == "":
            return ""

        for display, value in mapping.items():
            if str(value) == str(target_id):
                return display

        return ""

    # =====================================================
    # CẬP NHẬT BOOKING
    # =====================================================
    def update_booking(self):
        if self.selected_id is None:
            messagebox.showwarning(
                "Chưa chọn booking",
                "Vui lòng chọn booking cần cập nhật trên bảng."
            )
            return

        payload = self.get_form_data()

        if payload is None:
            return

        try:
            result = api_client.put(
                f"/api/bookings/{self.selected_id}",
                payload
            )

            messagebox.showinfo(
                "Thành công",
                result.get(
                    "message",
                    "Cập nhật booking thành công."
                )
            )

            self.clear_form()
            self.load_bookings()
            self.load_reference_data()

        except APIError as e:
            messagebox.showerror(
                "Không thể cập nhật booking",
                str(e)
            )

    # =====================================================
    # HỦY BOOKING
    # =====================================================
    def cancel_booking(self):
        if self.selected_id is None:
            messagebox.showwarning(
                "Chưa chọn booking",
                "Vui lòng chọn booking cần hủy."
            )
            return

        confirm = messagebox.askyesno(
            "Xác nhận hủy",
            f"Bạn có chắc chắn muốn hủy booking #{self.selected_id} không?"
        )

        if not confirm:
            return

        try:
            result = api_client.delete(
                f"/api/bookings/{self.selected_id}"
            )

            messagebox.showinfo(
                "Thành công",
                result.get(
                    "message",
                    "Đã gửi yêu cầu hủy booking."
                )
            )

            self.clear_form()
            self.load_bookings()
            self.load_reference_data()

        except APIError as e:
            messagebox.showerror(
                "Không thể hủy booking",
                str(e)
            )

    # =====================================================
    # TÌM KIẾM BOOKING
    # =====================================================
    def search_bookings(self):
        keyword = self.search_entry.get().strip().lower()

        if not keyword:
            self.display_bookings(self.bookings)
            return

        filtered = []

        for row in self.bookings:
            searchable = " ".join(
                str(value)
                for value in row.values()
                if value is not None
            ).lower()

            if keyword in searchable:
                filtered.append(row)

        self.display_bookings(filtered)

        self.set_status(
            f"Tìm thấy {len(filtered)} booking."
        )

    # =====================================================
    # XÓA FORM
    # =====================================================
    def clear_form(self):
        self.selected_id = None

        self.customer_var.set("")
        self.room_var.set("")
        self.checkin_var.set("")
        self.checkout_var.set("")
        self.status_var.set("CHO_XAC_NHAN")

        for item in self.tree.selection():
            self.tree.selection_remove(item)

        self.set_status("Đã làm mới biểu mẫu.")
