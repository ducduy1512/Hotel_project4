"""Tkinter service management page for the 8-table HOTEL ERD.

The single `dichvu` table stores two kinds of rows:
- Room defaults: booking_id IS NULL, attached to one room.
- Booking usage: booking_id IS NOT NULL, attached to one booking.

This page exposes both relationships separately so users can test:
Phong (1) -- (N) DichVu
Booking (1) -- (N) DichVu
"""

from decimal import Decimal, InvalidOperation
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
        self.green = "#19734A"

        self.rooms = []
        self.bookings = []
        self.booking_services = []

        self.rooms_by_display = {}
        self.bookings_by_display = {}
        self.room_defaults_by_id = {}
        self.room_default_rows = []
        self.booking_services_by_id = {}

        self.selected_default_id = None
        self.selected_booking_service_id = None

        self.build_ui()
        self.load_rooms()
        self.load_bookings()
        self.load_booking_services()

    # ------------------------------------------------------------------
    # Common UI helpers
    # ------------------------------------------------------------------
    def _make_button(self, parent, text, command, bg=None, fg=None, padx=14):
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=bg or self.navy,
            fg=fg or self.white,
            activebackground=bg or self.navy,
            activeforeground=fg or self.white,
            font=("Arial", 9, "bold"),
            relief="flat",
            padx=padx,
            pady=9,
            cursor="hand2",
        )

    def _make_entry(self, parent, row, column, label, width=28):
        tk.Label(
            parent,
            text=label,
            font=("Arial", 10, "bold"),
            fg=self.navy,
            bg=self.white,
        ).grid(row=row, column=column, sticky="w", padx=9, pady=(7, 3))
        entry = tk.Entry(parent, font=("Arial", 10), width=width)
        entry.grid(row=row + 1, column=column, sticky="ew", padx=9, pady=(0, 8))
        return entry

    def _make_tree(self, parent, columns, headings, widths, height=8):
        wrapper = tk.Frame(
            parent,
            bg=self.white,
            highlightbackground="#DDE3EA",
            highlightthickness=1,
        )
        wrapper.pack(fill="both", expand=True, padx=12, pady=(4, 12))

        tree = ttk.Treeview(wrapper, columns=columns, show="headings", height=height)
        for column in columns:
            tree.heading(column, text=headings[column])
            tree.column(column, width=widths[column], anchor="center")

        y_scroll = ttk.Scrollbar(wrapper, orient="vertical", command=tree.yview)
        x_scroll = ttk.Scrollbar(wrapper, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)

        tree.grid(row=0, column=0, sticky="nsew", padx=(10, 0), pady=(10, 0))
        y_scroll.grid(row=0, column=1, sticky="ns", padx=(0, 10), pady=(10, 0))
        x_scroll.grid(row=1, column=0, sticky="ew", padx=(10, 0), pady=(0, 10))
        wrapper.grid_rowconfigure(0, weight=1)
        wrapper.grid_columnconfigure(0, weight=1)
        return tree

    @staticmethod
    def _clear_tree(tree):
        for item in tree.get_children():
            tree.delete(item)

    @staticmethod
    def _format_money(value):
        try:
            amount = Decimal(str(value or 0))
            return f"{amount:,.0f} đ"
        except (InvalidOperation, ValueError, TypeError):
            return str(value)

    def _parse_form(self, name_entry, price_entry, quantity_entry):
        name = name_entry.get().strip()
        price_text = price_entry.get().strip().replace(",", "").replace(" ", "")
        quantity_text = quantity_entry.get().strip()

        if not name or not price_text or not quantity_text:
            messagebox.showwarning("Thiếu thông tin", "Vui lòng nhập tên, đơn giá và số lượng dịch vụ.")
            return None
        if len(name) > 100:
            messagebox.showwarning("Tên quá dài", "Tên dịch vụ tối đa 100 ký tự.")
            return None

        try:
            price = Decimal(price_text)
            quantity = int(quantity_text)
            if not price.is_finite() or price < 0 or price.as_tuple().exponent < -2:
                raise ValueError
            if quantity <= 0:
                raise ValueError
        except (InvalidOperation, ValueError):
            messagebox.showwarning(
                "Dữ liệu không hợp lệ",
                "Đơn giá phải >= 0 (tối đa 2 số thập phân) và số lượng phải là số nguyên dương.",
            )
            return None

        # Send the decimal as a string: json.dumps does not serialize Decimal.
        return {"ten": name, "don_gia": format(price, "f"), "so_luong": quantity}

    def _show_api_error(self, title, error):
        messagebox.showerror(title, str(error))

    # ------------------------------------------------------------------
    # Main page
    # ------------------------------------------------------------------
    def build_ui(self):
        tk.Label(
            self.parent,
            text="QUẢN LÝ DỊCH VỤ",
            font=("Arial", 24, "bold"),
            fg=self.navy,
            bg=self.background,
        ).pack(anchor="w", padx=30, pady=(20, 4))

        tk.Label(
            self.parent,
            text=(
                "Quản lý hai quan hệ của ERD: dịch vụ mặc định thuộc Phòng "
                "và dịch vụ phát sinh thuộc Booking. Cả hai đều lưu trong bảng dichvu."
            ),
            font=("Arial", 10),
            fg=self.gray,
            bg=self.background,
            wraplength=1100,
            justify="left",
        ).pack(anchor="w", padx=30, pady=(0, 12))

        self.notebook = ttk.Notebook(self.parent)
        self.notebook.pack(fill="both", expand=True, padx=30, pady=(0, 18))

        self.default_tab = tk.Frame(self.notebook, bg=self.background)
        self.booking_tab = tk.Frame(self.notebook, bg=self.background)
        self.notebook.add(self.default_tab, text="DỊCH VỤ MẶC ĐỊNH THEO PHÒNG")
        self.notebook.add(self.booking_tab, text="DỊCH VỤ PHÁT SINH THEO BOOKING")

        self._build_default_tab()
        self._build_booking_tab()

    # ------------------------------------------------------------------
    # Tab 1: room default services (booking_id IS NULL)
    # ------------------------------------------------------------------
    def _build_default_tab(self):
        selector = tk.Frame(self.default_tab, bg=self.white, highlightbackground="#DDE3EA", highlightthickness=1)
        selector.pack(fill="x", padx=12, pady=(12, 8))

        tk.Label(selector, text="Chọn phòng:", font=("Arial", 10, "bold"), bg=self.white, fg=self.navy).pack(
            side="left", padx=(14, 8), pady=12
        )
        self.room_var = tk.StringVar()
        self.room_combo = ttk.Combobox(selector, textvariable=self.room_var, state="readonly", width=42)
        self.room_combo.pack(side="left", padx=5, pady=9)
        self.room_combo.bind("<<ComboboxSelected>>", lambda _event: self.load_room_defaults())
        self._make_button(selector, "TẢI DỊCH VỤ PHÒNG", self.load_room_defaults, bg=self.navy).pack(
            side="left", padx=10, pady=5
        )
        tk.Label(selector, text="Tìm:", font=("Arial", 9, "bold"), bg=self.white, fg=self.navy).pack(
            side="left", padx=(14, 4), pady=10
        )
        self.default_search_entry = tk.Entry(selector, font=("Arial", 9), width=20)
        self.default_search_entry.pack(side="left", padx=4, pady=9)
        self.default_search_entry.bind("<KeyRelease>", lambda _event: self.render_room_defaults())

        tk.Label(
            self.default_tab,
            text=(
                "Dịch vụ ở tab này có booking_id = NULL. Khi tạo Booking cho phòng, "
                "trigger trg_booking_after_insert sẽ sao chép các dịch vụ này sang Booking mới."
            ),
            font=("Arial", 9),
            fg=self.gray,
            bg=self.background,
            wraplength=1100,
            justify="left",
        ).pack(anchor="w", padx=16, pady=(0, 5))

        form = tk.LabelFrame(
            self.default_tab,
            text=" THÔNG TIN DỊCH VỤ MẶC ĐỊNH ",
            font=("Arial", 10, "bold"),
            fg=self.navy,
            bg=self.white,
            padx=12,
            pady=8,
        )
        form.pack(fill="x", padx=12, pady=7)
        form.columnconfigure(0, weight=1)
        form.columnconfigure(1, weight=1)
        form.columnconfigure(2, weight=1)

        self.default_name_entry = self._make_entry(form, 0, 0, "Tên dịch vụ")
        self.default_price_entry = self._make_entry(form, 0, 1, "Đơn giá (VNĐ)")
        self.default_quantity_entry = self._make_entry(form, 0, 2, "Số lượng")

        actions = tk.Frame(self.default_tab, bg=self.background)
        actions.pack(fill="x", padx=12, pady=(2, 5))
        self._make_button(actions, "THÊM DỊCH VỤ MẶC ĐỊNH", self.add_default_service, bg=self.navy).pack(side="left", padx=(0, 7))
        self._make_button(actions, "CẬP NHẬT", self.update_default_service, bg=self.gold, fg=self.navy).pack(side="left", padx=7)
        self._make_button(actions, "XÓA", self.delete_default_service, bg=self.red).pack(side="left", padx=7)
        self._make_button(actions, "XÓA TRẮNG", self.clear_default_form, bg=self.gray).pack(side="left", padx=7)
        self._make_button(actions, "LÀM MỚI", self.load_room_defaults, bg=self.green).pack(side="left", padx=7)

        tk.Label(
            self.default_tab,
            text="DANH SÁCH DỊCH VỤ MẶC ĐỊNH CỦA PHÒNG ĐANG CHỌN",
            font=("Arial", 11, "bold"),
            fg=self.navy,
            bg=self.background,
        ).pack(anchor="w", padx=16, pady=(5, 0))

        self.default_tree = self._make_tree(
            self.default_tab,
            ("id", "ten", "don_gia", "so_luong", "phong_id"),
            {"id": "Mã DV", "ten": "Tên dịch vụ", "don_gia": "Đơn giá", "so_luong": "Số lượng", "phong_id": "Mã phòng"},
            {"id": 80, "ten": 300, "don_gia": 160, "so_luong": 110, "phong_id": 110},
        )
        self.default_tree.bind("<<TreeviewSelect>>", self.select_default_service)

    # ------------------------------------------------------------------
    # Tab 2: Booking services (booking_id IS NOT NULL)
    # ------------------------------------------------------------------
    def _build_booking_tab(self):
        selector = tk.Frame(self.booking_tab, bg=self.white, highlightbackground="#DDE3EA", highlightthickness=1)
        selector.pack(fill="x", padx=12, pady=(12, 8))

        tk.Label(selector, text="Booking áp dụng:", font=("Arial", 10, "bold"), bg=self.white, fg=self.navy).pack(
            side="left", padx=(14, 8), pady=12
        )
        self.booking_var = tk.StringVar()
        self.booking_combo = ttk.Combobox(selector, textvariable=self.booking_var, state="readonly", width=54)
        self.booking_combo.pack(side="left", padx=5, pady=9)
        self.booking_combo.bind("<<ComboboxSelected>>", self.on_booking_selected)
        self._make_button(selector, "TẢI BOOKING", self.load_bookings, bg=self.navy).pack(side="left", padx=10, pady=5)
        self._make_button(selector, "LÀM MỚI DỊCH VỤ", self.load_booking_services, bg=self.green).pack(side="left", padx=3, pady=5)
        tk.Label(selector, text="Tìm dịch vụ:", font=("Arial", 9, "bold"), bg=self.white, fg=self.navy).pack(
            side="left", padx=(10, 4), pady=10
        )
        self.booking_search_entry = tk.Entry(selector, font=("Arial", 9), width=18)
        self.booking_search_entry.pack(side="left", padx=4, pady=9)
        self.booking_search_entry.bind("<KeyRelease>", lambda _event: self.display_booking_services())

        self.booking_info_label = tk.Label(
            self.booking_tab,
            text="Chọn Booking để xem các dịch vụ đã ghi nhận.",
            font=("Arial", 9),
            fg=self.gray,
            bg=self.background,
            anchor="w",
        )
        self.booking_info_label.pack(fill="x", padx=16, pady=(0, 5))

        form = tk.LabelFrame(
            self.booking_tab,
            text=" THÔNG TIN DỊCH VỤ PHÁT SINH ",
            font=("Arial", 10, "bold"),
            fg=self.navy,
            bg=self.white,
            padx=12,
            pady=8,
        )
        form.pack(fill="x", padx=12, pady=7)
        form.columnconfigure(0, weight=1)
        form.columnconfigure(1, weight=1)
        form.columnconfigure(2, weight=1)

        self.booking_name_entry = self._make_entry(form, 0, 0, "Tên dịch vụ")
        self.booking_price_entry = self._make_entry(form, 0, 1, "Đơn giá (VNĐ)")
        self.booking_quantity_entry = self._make_entry(form, 0, 2, "Số lượng")

        actions = tk.Frame(self.booking_tab, bg=self.background)
        actions.pack(fill="x", padx=12, pady=(2, 5))
        self._make_button(actions, "THÊM DỊCH VỤ VÀO BOOKING", self.add_booking_service, bg=self.navy).pack(side="left", padx=(0, 7))
        self._make_button(actions, "CẬP NHẬT", self.update_booking_service, bg=self.gold, fg=self.navy).pack(side="left", padx=7)
        self._make_button(actions, "XÓA", self.delete_booking_service, bg=self.red).pack(side="left", padx=7)
        self._make_button(actions, "XÓA TRẮNG", self.clear_booking_form, bg=self.gray).pack(side="left", padx=7)

        tk.Label(
            self.booking_tab,
            text="DANH SÁCH DỊCH VỤ CỦA BOOKING ĐANG CHỌN",
            font=("Arial", 11, "bold"),
            fg=self.navy,
            bg=self.background,
        ).pack(anchor="w", padx=16, pady=(5, 0))

        self.booking_tree = self._make_tree(
            self.booking_tab,
            ("id", "ten", "don_gia", "so_luong", "thanh_tien", "phong", "trang_thai"),
            {
                "id": "Mã DV", "ten": "Tên dịch vụ", "don_gia": "Đơn giá",
                "so_luong": "Số lượng", "thanh_tien": "Thành tiền",
                "phong": "Phòng", "trang_thai": "Trạng thái Booking",
            },
            {"id": 70, "ten": 220, "don_gia": 125, "so_luong": 85, "thanh_tien": 140, "phong": 100, "trang_thai": 150},
        )
        self.booking_tree.bind("<<TreeviewSelect>>", self.select_booking_service)

    # ------------------------------------------------------------------
    # Load room / booking lookup data
    # ------------------------------------------------------------------
    def load_rooms(self):
        try:
            rows = api_client.get("/api/rooms/")
            if not isinstance(rows, list):
                raise APIError("API phòng không trả về danh sách hợp lệ.")

            self.rooms = rows
            self.rooms_by_display = {}
            options = []
            for room in rows:
                room_id = room.get("id")
                if room_id is None:
                    continue
                room_no = room.get("so_phong", "?")
                room_type = room.get("ten_loai_phong", "")
                display = f"Phòng {room_no} (ID: {room_id})"
                if room_type:
                    display += f" - {room_type}"
                options.append(display)
                self.rooms_by_display[display] = int(room_id)

            self.room_combo["values"] = options
            if options and self.room_var.get() not in self.rooms_by_display:
                self.room_var.set(options[0])
                self.load_room_defaults()
            elif not options:
                self.room_var.set("")
                self._clear_tree(self.default_tree)
        except (APIError, TypeError, ValueError) as error:
            self._show_api_error("Lỗi tải danh sách phòng", error)

    def load_bookings(self):
        try:
            rows = api_client.get("/api/bookings/")
            if not isinstance(rows, list):
                raise APIError("API Booking không trả về danh sách hợp lệ.")

            self.bookings = rows
            self.bookings_by_display = {}
            options = []
            for booking in rows:
                booking_id = booking.get("id", booking.get("booking_id"))
                if booking_id is None:
                    continue
                display = f"Booking #{booking_id}"
                if booking.get("so_phong"):
                    display += f" - Phòng {booking['so_phong']}"
                if booking.get("ho_ten"):
                    display += f" - {booking['ho_ten']}"
                status = booking.get("trang_thai", "")
                if status:
                    display += f" [{status}]"
                options.append(display)
                self.bookings_by_display[display] = booking

            self.booking_combo["values"] = options
            current = self.booking_var.get()
            if options and current not in self.bookings_by_display:
                self.booking_var.set(options[0])
            elif not options:
                self.booking_var.set("")
            self.display_booking_services()
        except (APIError, TypeError, ValueError) as error:
            self._show_api_error("Lỗi tải danh sách Booking", error)

    # ------------------------------------------------------------------
    # Room-default service operations
    # ------------------------------------------------------------------
    def _selected_room(self):
        display = self.room_var.get().strip()
        room_id = self.rooms_by_display.get(display)
        if room_id is None:
            messagebox.showwarning("Chưa chọn phòng", "Vui lòng chọn phòng cần quản lý dịch vụ mặc định.")
            return None
        return room_id

    def load_room_defaults(self):
        room_id = self._selected_room()
        self._clear_tree(self.default_tree)
        self.room_defaults_by_id = {}
        self.selected_default_id = None
        if room_id is None:
            return

        try:
            response = api_client.get(f"/api/services/rooms/{room_id}/options")
            rows = response.get("data", []) if isinstance(response, dict) else None
            if not isinstance(rows, list):
                raise APIError("API dịch vụ mặc định trả về dữ liệu không hợp lệ.")

            self.room_default_rows = rows
            self.room_defaults_by_id = {
                int(row.get("dichvu_id", row.get("id"))): row
                for row in rows
                if row.get("dichvu_id", row.get("id")) is not None
            }
            self.render_room_defaults()
            self.clear_default_form()
        except APIError as error:
            self._show_api_error("Không thể tải dịch vụ mặc định", error)

    def render_room_defaults(self):
        self._clear_tree(self.default_tree)
        room_id = self.rooms_by_display.get(self.room_var.get().strip())
        keyword = self.default_search_entry.get().strip().lower()
        for service_id, row in self.room_defaults_by_id.items():
            if keyword and keyword not in str(row.get("ten", "")).lower() and keyword not in str(service_id):
                continue
            self.default_tree.insert(
                "", "end", iid=str(service_id),
                values=(
                    service_id,
                    row.get("ten", ""),
                    self._format_money(row.get("don_gia")),
                    row.get("so_luong", ""),
                    room_id or row.get("phong_id", ""),
                ),
            )

    def select_default_service(self, _event=None):
        selection = self.default_tree.selection()
        if not selection:
            return
        service_id = int(selection[0])
        row = self.room_defaults_by_id.get(service_id)
        if row is None:
            return
        self.selected_default_id = service_id
        self._set_entries(
            self.default_name_entry, self.default_price_entry, self.default_quantity_entry,
            row.get("ten", ""), row.get("don_gia", ""), row.get("so_luong", ""),
        )

    def add_default_service(self):
        room_id = self._selected_room()
        if room_id is None:
            return
        payload = self._parse_form(self.default_name_entry, self.default_price_entry, self.default_quantity_entry)
        if payload is None:
            return
        payload.update({"phong_id": room_id, "booking_id": None})
        try:
            result = api_client.post("/api/services/", payload)
            messagebox.showinfo("Thành công", result.get("message", "Đã thêm dịch vụ mặc định cho phòng."))
            self.load_room_defaults()
        except APIError as error:
            self._show_api_error("Không thể thêm dịch vụ mặc định", error)

    def update_default_service(self):
        if self.selected_default_id is None:
            messagebox.showwarning("Chưa chọn dịch vụ", "Hãy chọn dịch vụ mặc định cần cập nhật trong bảng.")
            return
        room_id = self._selected_room()
        if room_id is None:
            return
        payload = self._parse_form(self.default_name_entry, self.default_price_entry, self.default_quantity_entry)
        if payload is None:
            return
        payload.update({"phong_id": room_id, "booking_id": None})
        try:
            result = api_client.put(f"/api/services/{self.selected_default_id}", payload)
            messagebox.showinfo("Thành công", result.get("message", "Đã cập nhật dịch vụ mặc định."))
            self.load_room_defaults()
        except APIError as error:
            self._show_api_error("Không thể cập nhật dịch vụ mặc định", error)

    def delete_default_service(self):
        if self.selected_default_id is None:
            messagebox.showwarning("Chưa chọn dịch vụ", "Hãy chọn dịch vụ mặc định cần xóa trong bảng.")
            return
        if not messagebox.askyesno(
            "Xác nhận xóa",
            "Xóa dịch vụ mặc định này khỏi phòng? Các Booking đã tạo trước đó không bị thay đổi.",
        ):
            return
        try:
            result = api_client.delete(f"/api/services/{self.selected_default_id}")
            messagebox.showinfo("Thành công", result.get("message", "Đã xóa dịch vụ mặc định."))
            self.load_room_defaults()
        except APIError as error:
            self._show_api_error("Không thể xóa dịch vụ mặc định", error)

    def clear_default_form(self):
        self.selected_default_id = None
        self._clear_entries(self.default_name_entry, self.default_price_entry, self.default_quantity_entry)
        for item in self.default_tree.selection():
            self.default_tree.selection_remove(item)

    # ------------------------------------------------------------------
    # Booking-service operations
    # ------------------------------------------------------------------
    def on_booking_selected(self, _event=None):
        # Clear the previous row selection whenever the active Booking changes.
        # This prevents update/delete actions from accidentally targeting a row
        # that belonged to the previously selected Booking.
        self.clear_booking_form()
        self.display_booking_services()

    def _selected_booking(self):
        display = self.booking_var.get().strip()
        booking = self.bookings_by_display.get(display)
        if booking is None:
            messagebox.showwarning("Chưa chọn Booking", "Vui lòng chọn Booking cần quản lý dịch vụ.")
            return None
        return booking

    def _booking_is_editable(self, booking):
        status = booking.get("trang_thai")
        if status in {"DA_HUY", "HOAN_THANH"}:
            messagebox.showwarning(
                "Booking không còn hiệu lực",
                "Không thể thêm hoặc sửa dịch vụ cho Booking đã hủy/hoàn thành.",
            )
            return False
        return True

    def load_booking_services(self):
        try:
            rows = api_client.get("/api/services/")
            if not isinstance(rows, list):
                raise APIError("API dịch vụ Booking không trả về danh sách hợp lệ.")
            self.booking_services = rows
            self.booking_services_by_id = {
                int(row["id"]): row
                for row in rows
                if row.get("id") is not None
            }
            self.display_booking_services()
        except (APIError, TypeError, ValueError, KeyError) as error:
            self._show_api_error("Lỗi tải dịch vụ theo Booking", error)

    def display_booking_services(self):
        self._clear_tree(self.booking_tree)
        display = self.booking_var.get().strip()
        booking = self.bookings_by_display.get(display)
        if booking is None:
            self.booking_info_label.config(text="Chọn Booking để xem các dịch vụ đã ghi nhận.")
            return

        booking_id = int(booking.get("id", booking.get("booking_id")))
        room_no = booking.get("so_phong", "?")
        status = booking.get("trang_thai", "")
        self.booking_info_label.config(
            text=f"Booking #{booking_id} | Phòng {room_no} | Khách: {booking.get('ho_ten', '—')} | Trạng thái: {status}",
        )

        keyword = ""
        if hasattr(self, "booking_search_entry"):
            keyword = self.booking_search_entry.get().strip().lower()

        for service_id, row in self.booking_services_by_id.items():
            if int(row.get("booking_id") or 0) != booking_id:
                continue
            if keyword and keyword not in str(row.get("ten", "")).lower() and keyword not in str(service_id):
                continue
            try:
                total = Decimal(str(row.get("don_gia", 0))) * int(row.get("so_luong", 0))
            except (InvalidOperation, ValueError, TypeError):
                total = Decimal("0")
            self.booking_tree.insert(
                "", "end", iid=str(service_id),
                values=(
                    service_id,
                    row.get("ten", ""),
                    self._format_money(row.get("don_gia")),
                    row.get("so_luong", ""),
                    self._format_money(total),
                    row.get("so_phong", room_no),
                    row.get("trang_thai_booking", status),
                ),
            )

    def select_booking_service(self, _event=None):
        selection = self.booking_tree.selection()
        if not selection:
            return
        service_id = int(selection[0])
        row = self.booking_services_by_id.get(service_id)
        if row is None:
            return
        self.selected_booking_service_id = service_id
        self._set_entries(
            self.booking_name_entry, self.booking_price_entry, self.booking_quantity_entry,
            row.get("ten", ""), row.get("don_gia", ""), row.get("so_luong", ""),
        )

    def add_booking_service(self):
        booking = self._selected_booking()
        if booking is None or not self._booking_is_editable(booking):
            return
        payload = self._parse_form(self.booking_name_entry, self.booking_price_entry, self.booking_quantity_entry)
        if payload is None:
            return
        payload.update({
            "booking_id": int(booking.get("id", booking.get("booking_id"))),
            "phong_id": int(booking["phong_id"]),
        })
        try:
            result = api_client.post("/api/services/", payload)
            messagebox.showinfo("Thành công", result.get("message", "Đã thêm dịch vụ vào Booking."))
            self.clear_booking_form()
            self.load_booking_services()
        except APIError as error:
            self._show_api_error("Không thể thêm dịch vụ vào Booking", error)

    def update_booking_service(self):
        if self.selected_booking_service_id is None:
            messagebox.showwarning("Chưa chọn dịch vụ", "Hãy chọn dịch vụ cần cập nhật trong bảng.")
            return
        booking = self._selected_booking()
        if booking is None or not self._booking_is_editable(booking):
            return
        payload = self._parse_form(self.booking_name_entry, self.booking_price_entry, self.booking_quantity_entry)
        if payload is None:
            return
        current_booking_id = int(booking.get("id", booking.get("booking_id")))
        selected_service = self.booking_services_by_id.get(self.selected_booking_service_id)
        if not selected_service or int(selected_service.get("booking_id") or 0) != current_booking_id:
            messagebox.showwarning("Sai Booking", "Dịch vụ đang chọn không thuộc Booking hiện tại. Hãy chọn lại dịch vụ.")
            self.clear_booking_form()
            return
        payload.update({
            "booking_id": current_booking_id,
            "phong_id": int(booking["phong_id"]),
        })
        try:
            result = api_client.put(f"/api/services/{self.selected_booking_service_id}", payload)
            messagebox.showinfo("Thành công", result.get("message", "Đã cập nhật dịch vụ Booking."))
            self.clear_booking_form()
            self.load_booking_services()
        except APIError as error:
            self._show_api_error("Không thể cập nhật dịch vụ Booking", error)

    def delete_booking_service(self):
        if self.selected_booking_service_id is None:
            messagebox.showwarning("Chưa chọn dịch vụ", "Hãy chọn dịch vụ cần xóa trong bảng.")
            return
        booking = self._selected_booking()
        if booking is None:
            return
        if not self._booking_is_editable(booking):
            return
        current_booking_id = int(booking.get("id", booking.get("booking_id")))
        selected_service = self.booking_services_by_id.get(self.selected_booking_service_id)
        if not selected_service or int(selected_service.get("booking_id") or 0) != current_booking_id:
            messagebox.showwarning("Sai Booking", "Dịch vụ đang chọn không thuộc Booking hiện tại. Hãy chọn lại dịch vụ.")
            self.clear_booking_form()
            return
        if not messagebox.askyesno("Xác nhận xóa", "Bạn có chắc chắn muốn xóa dịch vụ khỏi Booking này không?"):
            return
        try:
            result = api_client.delete(f"/api/services/{self.selected_booking_service_id}")
            messagebox.showinfo("Thành công", result.get("message", "Đã xóa dịch vụ Booking."))
            self.clear_booking_form()
            self.load_booking_services()
        except APIError as error:
            self._show_api_error("Không thể xóa dịch vụ Booking", error)

    def clear_booking_form(self):
        self.selected_booking_service_id = None
        self._clear_entries(self.booking_name_entry, self.booking_price_entry, self.booking_quantity_entry)
        for item in self.booking_tree.selection():
            self.booking_tree.selection_remove(item)

    # ------------------------------------------------------------------
    # Generic form helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _set_entries(name_entry, price_entry, quantity_entry, name, price, quantity):
        for entry, value in (
            (name_entry, name),
            (price_entry, price),
            (quantity_entry, quantity),
        ):
            entry.delete(0, tk.END)
            entry.insert(0, str(value if value is not None else ""))

    @staticmethod
    def _clear_entries(*entries):
        for entry in entries:
            entry.delete(0, tk.END)


# Backwards-compatible class name used by app.py.
__all__ = ["ServicesPage"]
