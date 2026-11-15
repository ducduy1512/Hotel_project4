
import tkinter as tk
from tkinter import ttk, messagebox

from api_client import api_client, APIError


class ServicesPage:
    def __init__(self, parent):
        self.parent = parent

        self.navy = "#101F35"
        self.gold = "#D5AD5B"
        self.white = "#FFFFFF"
        self.background = "#F4F6F9"
        self.gray = "#8793A5"
        self.red = "#C0392B"

        self.selected_id = None
        self.services = []
        self.services_by_id = {}
        self.bookings = []
        self.bookings_by_display = {}

        self.build_ui()
        self.load_bookings()
        self.load_services()

    # ==================================================
    # GIAO DIỆN
    # ==================================================
    def build_ui(self):
        tk.Label(
            self.parent,
            text="QUẢN LÝ DỊCH VỤ",
            font=("Arial", 24, "bold"),
            fg=self.navy,
            bg=self.background
        ).pack(anchor="w", padx=35, pady=(25, 5))

        tk.Label(
            self.parent,
            text="Quản lý dịch vụ phát sinh trong từng booking",
            font=("Arial", 11),
            fg=self.gray,
            bg=self.background
        ).pack(anchor="w", padx=35, pady=(0, 20))

        # ===== TÌM KIẾM =====
        search_frame = tk.Frame(
            self.parent,
            bg=self.white,
            highlightbackground="#DDE3EA",
            highlightthickness=1
        )
        search_frame.pack(fill="x", padx=35, pady=(0, 15))

        tk.Label(
            search_frame,
            text="Tìm kiếm dịch vụ:",
            font=("Arial", 11, "bold"),
            bg=self.white,
            fg=self.navy
        ).pack(side="left", padx=(18, 10), pady=15)

        self.search_entry = tk.Entry(
            search_frame,
            font=("Arial", 11),
            width=30
        )
        self.search_entry.pack(side="left", padx=5, pady=12)

        self.search_entry.bind(
            "<KeyRelease>",
            lambda event: self.search_services()
        )

        tk.Button(
            search_frame,
            text="LÀM MỚI",
            command=self.reset_search,
            bg=self.navy,
            fg=self.white,
            font=("Arial", 9, "bold"),
            relief="flat",
            padx=18,
            pady=9,
            cursor="hand2"
        ).pack(side="left", padx=12)

        # ===== FORM =====
        form_frame = tk.LabelFrame(
            self.parent,
            text=" THÔNG TIN DỊCH VỤ ",
            font=("Arial", 11, "bold"),
            fg=self.navy,
            bg=self.white,
            padx=20,
            pady=15
        )
        form_frame.pack(fill="x", padx=35, pady=(0, 15))

        form_frame.columnconfigure(0, weight=1)
        form_frame.columnconfigure(1, weight=1)

        # Tên dịch vụ
        tk.Label(
            form_frame,
            text="Tên dịch vụ",
            font=("Arial", 10, "bold"),
            fg=self.navy,
            bg=self.white
        ).grid(row=0, column=0, sticky="w", padx=10, pady=7)

        self.name_entry = tk.Entry(
            form_frame,
            font=("Arial", 10)
        )
        self.name_entry.grid(
            row=1, column=0, sticky="ew",
            padx=10, pady=(0, 10)
        )

        # Đơn giá
        tk.Label(
            form_frame,
            text="Đơn giá (VNĐ)",
            font=("Arial", 10, "bold"),
            fg=self.navy,
            bg=self.white
        ).grid(row=0, column=1, sticky="w", padx=10, pady=7)

        self.price_entry = tk.Entry(
            form_frame,
            font=("Arial", 10)
        )
        self.price_entry.grid(
            row=1, column=1, sticky="ew",
            padx=10, pady=(0, 10)
        )

        # Số lượng
        tk.Label(
            form_frame,
            text="Số lượng",
            font=("Arial", 10, "bold"),
            fg=self.navy,
            bg=self.white
        ).grid(row=2, column=0, sticky="w", padx=10, pady=7)

        self.quantity_entry = tk.Entry(
            form_frame,
            font=("Arial", 10)
        )
        self.quantity_entry.grid(
            row=3, column=0, sticky="ew",
            padx=10, pady=(0, 10)
        )

        # Booking
        tk.Label(
            form_frame,
            text="Booking áp dụng",
            font=("Arial", 10, "bold"),
            fg=self.navy,
            bg=self.white
        ).grid(row=2, column=1, sticky="w", padx=10, pady=7)

        self.booking_var = tk.StringVar()

        self.booking_combo = ttk.Combobox(
            form_frame,
            textvariable=self.booking_var,
            state="readonly",
            font=("Arial", 10)
        )
        self.booking_combo.grid(
            row=3, column=1, sticky="ew",
            padx=10, pady=(0, 10)
        )

        # ===== BUTTONS =====
        button_frame = tk.Frame(
            self.parent,
            bg=self.background
        )
        button_frame.pack(fill="x", padx=35, pady=(0, 15))

        tk.Button(
            button_frame,
            text="THÊM DỊCH VỤ",
            command=self.add_service,
            bg=self.navy,
            fg=self.white,
            font=("Arial", 9, "bold"),
            relief="flat",
            padx=17,
            pady=10,
            cursor="hand2"
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            button_frame,
            text="CẬP NHẬT",
            command=self.update_service,
            bg=self.gold,
            fg=self.navy,
            font=("Arial", 9, "bold"),
            relief="flat",
            padx=20,
            pady=10,
            cursor="hand2"
        ).pack(side="left", padx=8)

        tk.Button(
            button_frame,
            text="XÓA",
            command=self.delete_service,
            bg=self.red,
            fg=self.white,
            font=("Arial", 9, "bold"),
            relief="flat",
            padx=25,
            pady=10,
            cursor="hand2"
        ).pack(side="left", padx=8)

        tk.Button(
            button_frame,
            text="XÓA TRẮNG",
            command=self.clear_form,
            bg=self.gray,
            fg=self.white,
            font=("Arial", 9, "bold"),
            relief="flat",
            padx=18,
            pady=10,
            cursor="hand2"
        ).pack(side="left", padx=8)

        # ===== TABLE =====
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
            pady=(0, 20)
        )

        tk.Label(
            table_frame,
            text="DANH SÁCH DỊCH VỤ",
            font=("Arial", 12, "bold"),
            fg=self.navy,
            bg=self.white
        ).pack(anchor="w", padx=18, pady=12)

        columns = (
            "id",
            "ten",
            "don_gia",
            "so_luong",
            "booking_id"
        )

        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            height=9
        )

        headings = {
            "id": "Mã dịch vụ",
            "ten": "Tên dịch vụ",
            "don_gia": "Đơn giá",
            "so_luong": "Số lượng",
            "booking_id": "Mã booking"
        }

        widths = {
            "id": 100,
            "ten": 220,
            "don_gia": 160,
            "so_luong": 120,
            "booking_id": 140
        }

        for column in columns:
            self.tree.heading(
                column,
                text=headings[column]
            )
            self.tree.column(
                column,
                width=widths[column],
                anchor="center"
            )

        scrollbar = ttk.Scrollbar(
            table_frame,
            orient="vertical",
            command=self.tree.yview
        )

        self.tree.configure(
            yscrollcommand=scrollbar.set
        )

        self.tree.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(15, 0),
            pady=(0, 15)
        )

        scrollbar.pack(
            side="right",
            fill="y",
            padx=(0, 15),
            pady=(0, 15)
        )

        self.tree.bind(
            "<<TreeviewSelect>>",
            self.select_service
        )

    # ==================================================
    # TẢI BOOKING TỪ API
    # ==================================================
    def load_bookings(self):
        try:
            rows = api_client.get("/api/bookings/")

            if not isinstance(rows, list):
                raise APIError(
                    "API booking không trả về danh sách hợp lệ."
                )

            self.bookings = rows
            self.bookings_by_display = {}

            options = []

            for booking in rows:
                booking_id = booking.get(
                    "id",
                    booking.get("booking_id")
                )

                if booking_id is None:
                    continue

                display = f"Booking ID: {booking_id}"

                customer_name = booking.get("ho_ten")

                if customer_name:
                    display += f" - {customer_name}"

                options.append(display)
                self.bookings_by_display[display] = int(booking_id)

            self.booking_combo["values"] = options

        except (APIError, KeyError, TypeError, ValueError) as e:
            messagebox.showerror(
                "Lỗi tải booking",
                str(e)
            )

    # ==================================================
    # TẢI DỊCH VỤ TỪ API
    # ==================================================

    def load_services(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        try:
            response = api_client.get("/api/services/")

            # API thực tế trả về {"services": [...]}.
            if isinstance(response, dict):
                rows = response.get("services", [])
            elif isinstance(response, list):
                rows = response
            else:
                rows = []

            if not isinstance(rows, list):
                raise APIError(
                    "Dữ liệu services từ API không đúng định dạng."
                )

            self.services = rows
            self.services_by_id = {
                int(row["id"]): row
                for row in rows
                if row.get("id") is not None
            }

            self.display_services(rows)

        except (APIError, KeyError, TypeError, ValueError) as error:
            messagebox.showerror(
                "Lỗi tải dịch vụ",
                str(error)
            )

    # ==================================================
    # HIỂN THỊ DỮ LIỆU
    # ==================================================
    def display_services(self, rows):
        for item in self.tree.get_children():
            self.tree.delete(item)

        for row in rows:
            self.tree.insert(
                "",
                "end",
                values=(
                    row.get("id", ""),
                    row.get("ten", ""),
                    f"{float(row.get('don_gia', 0)):,.0f} đ",
                    row.get("so_luong", ""),
                    row.get("booking_id", "")
                )
            )

    # ==================================================
    # TÌM KIẾM
    # ==================================================
    def search_services(self):
        keyword = self.search_entry.get().strip().lower()

        filtered_rows = [
            row for row in self.services
            if keyword in str(row.get("ten", "")).lower()
            or keyword in str(row.get("id", "")).lower()
            or keyword in str(row.get("booking_id", "")).lower()
        ]

        self.display_services(filtered_rows)

    def reset_search(self):
        self.search_entry.delete(0, tk.END)
        self.load_services()

    # ==================================================
    # CHỌN DỊCH VỤ
    # ==================================================
    def select_service(self, event=None):
        selected = self.tree.selection()

        if not selected:
            return

        values = self.tree.item(
            selected[0],
            "values"
        )

        self.selected_id = int(values[0])

        service = self.services_by_id.get(
            self.selected_id
        )

        if service is None:
            messagebox.showerror(
                "Lỗi dữ liệu",
                "Không tìm thấy dịch vụ đã chọn."
            )
            return

        self.name_entry.delete(0, tk.END)
        self.name_entry.insert(0, service.get("ten", ""))

        self.price_entry.delete(0, tk.END)
        self.price_entry.insert(
            0,
            str(service.get("don_gia", ""))
        )

        self.quantity_entry.delete(0, tk.END)
        self.quantity_entry.insert(
            0,
            str(service.get("so_luong", ""))
        )

        booking_id = str(service.get("booking_id", ""))

        self.booking_var.set("")

        for display, current_id in self.bookings_by_display.items():
            if str(current_id) == booking_id:
                self.booking_var.set(display)
                break

    # ==================================================
    # KIỂM TRA DỮ LIỆU
    # ==================================================
    def validate_input(self):
        name = self.name_entry.get().strip()
        price = self.price_entry.get().strip()
        quantity = self.quantity_entry.get().strip()
        booking_display = self.booking_var.get().strip()

        if not name or not price or not quantity or not booking_display:
            messagebox.showwarning(
                "Thiếu thông tin",
                "Vui lòng nhập đầy đủ thông tin dịch vụ."
            )
            return None

        if booking_display not in self.bookings_by_display:
            messagebox.showwarning(
                "Booking không hợp lệ",
                "Vui lòng chọn booking từ danh sách."
            )
            return None

        try:
            price_value = float(price)
            quantity_value = int(quantity)

            if price_value <= 0 or quantity_value <= 0:
                raise ValueError

        except ValueError:
            messagebox.showwarning(
                "Dữ liệu không hợp lệ",
                "Đơn giá và số lượng phải là số dương hợp lệ."
            )
            return None

        return {
            "ten": name,
            "don_gia": price_value,
            "so_luong": quantity_value,
            "booking_id": self.bookings_by_display[booking_display]
        }

    # ==================================================
    # THÊM DỊCH VỤ
    # ==================================================
    def add_service(self):
        payload = self.validate_input()

        if payload is None:
            return

        try:
            result = api_client.post(
                "/api/services/",
                payload
            )

            messagebox.showinfo(
                "Thành công",
                result.get(
                    "message",
                    "Thêm dịch vụ thành công."
                )
            )

            self.clear_form()
            self.load_services()

        except APIError as e:
            messagebox.showerror(
                "Không thể thêm dịch vụ",
                str(e)
            )

    # ==================================================
    # CẬP NHẬT DỊCH VỤ
    # ==================================================
    def update_service(self):
        if self.selected_id is None:
            messagebox.showwarning(
                "Chưa chọn dữ liệu",
                "Vui lòng chọn dịch vụ cần cập nhật."
            )
            return

        payload = self.validate_input()

        if payload is None:
            return

        try:
            result = api_client.put(
                f"/api/services/{self.selected_id}",
                payload
            )

            messagebox.showinfo(
                "Thành công",
                result.get(
                    "message",
                    "Cập nhật dịch vụ thành công."
                )
            )

            self.clear_form()
            self.load_services()

        except APIError as e:
            messagebox.showerror(
                "Không thể cập nhật",
                str(e)
            )

    # ==================================================
    # XÓA DỊCH VỤ
    # ==================================================
    def delete_service(self):
        if self.selected_id is None:
            messagebox.showwarning(
                "Chưa chọn dữ liệu",
                "Vui lòng chọn dịch vụ cần xóa."
            )
            return

        confirm = messagebox.askyesno(
            "Xác nhận xóa",
            "Bạn có chắc chắn muốn xóa dịch vụ này không?"
        )

        if not confirm:
            return

        try:
            result = api_client.delete(
                f"/api/services/{self.selected_id}"
            )

            messagebox.showinfo(
                "Thành công",
                result.get(
                    "message",
                    "Xóa dịch vụ thành công."
                )
            )

            self.clear_form()
            self.load_services()

        except APIError as e:
            messagebox.showerror(
                "Không thể xóa dịch vụ",
                str(e)
            )

    # ==================================================
    # XÓA TRẮNG FORM
    # ==================================================
    def clear_form(self):
        self.selected_id = None

        self.name_entry.delete(0, tk.END)
        self.price_entry.delete(0, tk.END)
        self.quantity_entry.delete(0, tk.END)

        self.booking_var.set("")

        for item in self.tree.selection():
            self.tree.selection_remove(item)
