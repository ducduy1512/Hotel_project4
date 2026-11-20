import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date, timedelta
import base64
from urllib.request import Request, urlopen

from api_client import api_client, APIError


class CustomerPortalPage:
    """Workspace riêng cho CUSTOMER; dữ liệu được tải qua REST API."""

    BG = "#F3F4F6"
    NAVY = "#17324D"
    BLUE = "#2563EB"
    GREEN = "#15803D"

    def __init__(self, parent, user, on_logout=None):
        self.parent = parent
        self.user = user or {}
        self.on_logout = on_logout
        self.room_rows = {}
        self.booking_rows = {}
        self.invoice_rows = {}

        self.frame = tk.Frame(parent, bg=self.BG)
        self.frame.pack(fill="both", expand=True)
        self._build_header()
        self._build_tabs()
        self.refresh_bookings()
        self.refresh_invoices()

    def _build_header(self):
        header = tk.Frame(self.frame, bg=self.NAVY, height=92)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="HOTEL CUSTOMER PORTAL", bg=self.NAVY, fg="white",
                 font=("Arial", 19, "bold")).pack(anchor="w", padx=24, pady=(16, 2))
        tk.Label(header, text=f"Xin chào, {self.user.get('full_name') or self.user.get('username', 'Khách hàng')}  ·  Tài khoản CUSTOMER",
                 bg=self.NAVY, fg="#D8E5F2", font=("Arial", 10)).pack(anchor="w", padx=25)
        if self.on_logout:
            tk.Button(header, text="ĐĂNG XUẤT", command=self.on_logout,
                      bg="#B91C1C", fg="white", activebackground="#991B1B",
                      relief="flat", padx=15, pady=7, cursor="hand2").place(relx=0.97, rely=0.50, anchor="e")

    def _build_tabs(self):
        content = tk.Frame(self.frame, bg=self.BG, padx=18, pady=16)
        content.pack(fill="both", expand=True)
        style = ttk.Style()
        style.configure("Customer.TNotebook", background=self.BG, borderwidth=0)
        style.configure("Customer.TNotebook.Tab", padding=(18, 9), font=("Arial", 10, "bold"))
        self.tabs = ttk.Notebook(content, style="Customer.TNotebook")
        self.tabs.pack(fill="both", expand=True)

        self.rooms_tab = tk.Frame(self.tabs, bg="white", padx=16, pady=14)
        self.bookings_tab = tk.Frame(self.tabs, bg="white", padx=16, pady=14)
        self.invoices_tab = tk.Frame(self.tabs, bg="white", padx=16, pady=14)
        self.profile_tab = tk.Frame(self.tabs, bg="white", padx=16, pady=14)
        self.tabs.add(self.rooms_tab, text="Đặt phòng")
        self.tabs.add(self.bookings_tab, text="Booking của tôi")
        self.tabs.add(self.invoices_tab, text="Hóa đơn & thanh toán")
        self.tabs.add(self.profile_tab, text="Tài khoản")
        self._build_rooms_tab()
        self._build_bookings_tab()
        self._build_invoices_tab()
        self._build_profile_tab()

    @staticmethod
    def _tree(parent, columns, headings, widths=None):
        wrapper = tk.Frame(parent, bg="white")
        wrapper.pack(fill="both", expand=True, pady=(8, 4))
        tree = ttk.Treeview(wrapper, columns=columns, show="headings", height=13)
        for index, (column, heading) in enumerate(zip(columns, headings)):
            tree.heading(column, text=heading)
            tree.column(column, width=(widths[index] if widths else 130), anchor="center")
        yscroll = ttk.Scrollbar(wrapper, orient="vertical", command=tree.yview)
        xscroll = ttk.Scrollbar(wrapper, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        wrapper.rowconfigure(0, weight=1)
        wrapper.columnconfigure(0, weight=1)
        return tree

    @staticmethod
    def _money(value):
        try:
            return f"{float(value):,.0f} VNĐ"
        except (TypeError, ValueError):
            return str(value or 0)

    @staticmethod
    def _date(value):
        return str(value)[:10] if value else ""

    def _build_rooms_tab(self):
        tk.Label(self.rooms_tab, text="TÌM PHÒNG TRỐNG", bg="white", fg=self.NAVY,
                 font=("Arial", 18, "bold")).pack(anchor="w")
        tk.Label(self.rooms_tab, text="Chọn ngày nhận và ngày trả để xem phòng còn trống.",
                 bg="white", fg="#64748B").pack(anchor="w", pady=(3, 12))
        form = tk.Frame(self.rooms_tab, bg="white")
        form.pack(fill="x")
        tomorrow = date.today() + timedelta(days=1)
        self.checkin_var = tk.StringVar(value=tomorrow.isoformat())
        self.checkout_var = tk.StringVar(value=(tomorrow + timedelta(days=1)).isoformat())
        for label, var in (("Ngày nhận (YYYY-MM-DD)", self.checkin_var), ("Ngày trả (YYYY-MM-DD)", self.checkout_var)):
            group = tk.Frame(form, bg="white")
            group.pack(side="left", padx=(0, 14))
            tk.Label(group, text=label, bg="white", fg=self.NAVY, font=("Arial", 9, "bold")).pack(anchor="w")
            tk.Entry(group, textvariable=var, width=18, font=("Arial", 10)).pack(pady=(4, 0), ipady=5)
        tk.Button(form, text="TÌM PHÒNG", command=self.search_rooms, bg=self.BLUE, fg="white",
                  relief="flat", padx=16, pady=8, cursor="hand2").pack(side="left", pady=(17, 0))
        self.rooms_tree = self._tree(self.rooms_tab, ("room", "type", "price", "peak_fee", "capacity", "status"),
                                     ("Số phòng", "Loại phòng", "Tiền phòng cơ bản", "Phụ phí cao điểm", "Sức chứa", "Trạng thái"),
                                     (100, 150, 145, 150, 90, 115))
        tk.Button(self.rooms_tab, text="ĐẶT PHÒNG ĐANG CHỌN", command=self.book_selected_room,
                  bg=self.GREEN, fg="white", relief="flat", padx=16, pady=9, cursor="hand2").pack(anchor="e", pady=(6, 0))

    def _build_bookings_tab(self):
        tk.Label(self.bookings_tab, text="LỊCH SỬ ĐẶT PHÒNG", bg="white", fg=self.NAVY,
                 font=("Arial", 18, "bold")).pack(anchor="w")
        tk.Label(self.bookings_tab, text="Bạn chỉ xem và thao tác trên Booking thuộc tài khoản của mình.",
                 bg="white", fg="#64748B").pack(anchor="w", pady=(3, 8))
        self.bookings_tree = self._tree(self.bookings_tab,
            ("id", "room", "type", "checkin", "checkout", "nights", "room_fee", "peak_fee", "status", "paid"),
            ("Mã Booking", "Phòng", "Loại phòng", "Ngày nhận", "Ngày trả", "Số đêm", "Tiền phòng", "Phụ phí cao điểm", "Trạng thái", "Đã thanh toán"),
            (75, 60, 100, 90, 90, 55, 105, 140, 105, 110))
        actions = tk.Frame(self.bookings_tab, bg="white")
        actions.pack(fill="x", pady=(8, 0))
        tk.Button(actions, text="LÀM MỚI", command=self.refresh_bookings, bg="#475569", fg="white",
                  relief="flat", padx=12, pady=8).pack(side="left", padx=(0, 8))
        tk.Button(actions, text="CHI TIẾT", command=self.show_booking_detail, bg=self.BLUE, fg="white",
                  relief="flat", padx=12, pady=8).pack(side="left", padx=4)
        tk.Button(actions, text="HỦY BOOKING", command=self.cancel_selected_booking, bg="#B91C1C", fg="white",
                  relief="flat", padx=12, pady=8).pack(side="left", padx=4)
        tk.Label(actions, text="Phương thức:", bg="white").pack(side="left", padx=(18, 4))
        self.method_var = tk.StringVar(value="CHUYEN_KHOAN")
        ttk.Combobox(actions, textvariable=self.method_var, state="readonly", width=17,
                     values=("TIEN_MAT", "CHUYEN_KHOAN", "THE")).pack(side="left")
        tk.Button(actions, text="TẠO HÓA ĐƠN / YÊU CẦU THANH TOÁN", command=self.request_payment,
                  bg=self.GREEN, fg="white", relief="flat", padx=12, pady=8).pack(side="right")
        tk.Label(self.bookings_tab,
                 text="Chuyển khoản QR được đối soát tự động qua SePay khi hệ thống nhận webhook hợp lệ. Tiền mặt/thẻ vẫn cần nhân viên xác nhận.",
                 bg="white", fg="#475569", wraplength=930, justify="left").pack(anchor="w", pady=(9, 0))

    def _build_invoices_tab(self):
        tk.Label(self.invoices_tab, text="HÓA ĐƠN CỦA TÔI", bg="white", fg=self.NAVY,
                 font=("Arial", 18, "bold")).pack(anchor="w")
        tk.Label(self.invoices_tab, text="Danh sách chỉ gồm hóa đơn phát sinh từ Booking của tài khoản hiện tại.",
                 bg="white", fg="#64748B").pack(anchor="w", pady=(3, 8))
        self.invoices_tree = self._tree(self.invoices_tab,
            ("id", "booking", "room", "room_fee", "peak_fee", "service_fee", "total", "method", "status", "date"),
            ("Mã HĐ", "Booking", "Phòng", "Tiền phòng", "Phụ phí cao điểm", "Tiền dịch vụ", "Tổng tiền", "Phương thức", "Thanh toán", "Ngày lập"),
            (60, 65, 55, 100, 125, 100, 110, 90, 105, 90))
        tk.Button(self.invoices_tab, text="LÀM MỚI HÓA ĐƠN", command=self.refresh_invoices,
                  bg=self.BLUE, fg="white", relief="flat", padx=14, pady=8).pack(anchor="e", pady=(8, 0))

    def _build_profile_tab(self):
        tk.Label(self.profile_tab, text="THÔNG TIN TÀI KHOẢN", bg="white", fg=self.NAVY,
                 font=("Arial", 18, "bold")).pack(anchor="w", pady=(0, 14))
        info = [
            ("Tên đăng nhập", self.user.get("username")),
            ("Họ và tên", self.user.get("full_name") or self.user.get("ho_ten")),
            ("Mã khách hàng", self.user.get("khach_id")),
            ("CCCD", self.user.get("cccd")),
            ("Số điện thoại", self.user.get("sdt")),
            ("Vai trò", "CUSTOMER"),
        ]
        for label, value in info:
            row = tk.Frame(self.profile_tab, bg="#F8FAFC", padx=14, pady=12)
            row.pack(fill="x", pady=5)
            tk.Label(row, text=label, bg="#F8FAFC", fg="#64748B", width=20, anchor="w").pack(side="left")
            tk.Label(row, text=str(value or "Chưa cập nhật"), bg="#F8FAFC", fg=self.NAVY,
                     font=("Arial", 10, "bold")).pack(side="left")

    def search_rooms(self):
        try:
            result = api_client.get("/api/customer/available-rooms", params={
                "ngay_nhan": self.checkin_var.get().strip(),
                "ngay_tra": self.checkout_var.get().strip(),
            })
            rows = result.get("rooms", [])
            for item in self.rooms_tree.get_children():
                self.rooms_tree.delete(item)
            self.room_rows = {}
            for room in rows:
                room_id = int(room.get("phong_id", room.get("id")))
                self.room_rows[room_id] = room
                self.rooms_tree.insert("", "end", iid=str(room_id), values=(
                    room.get("so_phong"), room.get("loai_phong"), self._money(room.get("tien_phong_du_kien", room.get("gia_co_ban"))),
                    self._money(room.get("tien_phu_phi_mua_cao_diem", 0)), room.get("suc_chua"), room.get("trang_thai")))
            messagebox.showinfo("Tìm phòng", f"Tìm thấy {len(rows)} phòng phù hợp.", parent=self.frame)
        except APIError as exc:
            messagebox.showerror("Không thể tìm phòng", str(exc), parent=self.frame)
        except (ValueError, TypeError) as exc:
            messagebox.showerror("Ngày không hợp lệ", "Nhập ngày theo định dạng YYYY-MM-DD.", parent=self.frame)

    def book_selected_room(self):
        selected = self.rooms_tree.selection()
        if not selected:
            messagebox.showwarning("Chưa chọn phòng", "Hãy chọn một phòng trong danh sách.", parent=self.frame)
            return
        room = self.room_rows.get(int(selected[0]))
        if not room:
            return

        try:
            room_id = int(room.get("phong_id", room.get("id")))
            result = api_client.get(f"/api/customer/rooms/{room_id}/services")
            services = result.get("services", [])
        except APIError as exc:
            messagebox.showerror("Không tải được dịch vụ", str(exc), parent=self.frame)
            return

        dialog = tk.Toplevel(self.frame)
        dialog.title(f"Dịch vụ phòng {room.get('so_phong')}")
        dialog.geometry("720x650")
        dialog.minsize(650, 520)
        dialog.transient(self.frame.winfo_toplevel())
        dialog.grab_set()
        dialog.configure(bg="white")

        tk.Label(
            dialog, text=f"ĐẶT PHÒNG {room.get('so_phong')}",
            bg="white", fg=self.NAVY, font=("Arial", 16, "bold")
        ).pack(anchor="w", padx=20, pady=(18, 4))
        tk.Label(
            dialog,
            text=f"{self.checkin_var.get()}  →  {self.checkout_var.get()}",
            bg="white", fg="#64748B", font=("Arial", 10)
        ).pack(anchor="w", padx=20, pady=(0, 12))
        tk.Label(
            dialog,
            text="Dịch vụ mặc định được chọn sẵn. Bạn có thể bỏ chọn hoặc thay đổi số lượng.",
            bg="white", fg=self.NAVY, wraplength=680, justify="left"
        ).pack(anchor="w", padx=20, pady=(0, 8))

        try:
            price_preview = api_client.get(
                f"/api/customer/rooms/{room_id}/price-preview",
                params={"ngay_nhan": self.checkin_var.get().strip(),
                        "ngay_tra": self.checkout_var.get().strip()}
            )
            season_lines = [
                f"{night.get('ngay')}: phụ thu +{night.get('he_so_gia')} × {self._money(night.get('gia_co_ban'))} = {self._money(night.get('phi_mua_cao_diem'))}"
                for night in price_preview.get("chi_tiet_mua_cao_diem", [])
                if night.get("mua_cao_diem_id") is not None
            ]
            season_label = "CÓ ÁP DỤNG MÙA CAO ĐIỂM" if price_preview.get("ap_dung_mua_cao_diem") else "Không áp dụng mùa cao điểm"
            tk.Label(
                dialog,
                text=(f"Tiền phòng cơ bản: {self._money(price_preview.get('tien_phong_du_kien'))}  |  "
                      f"Phụ phí mùa cao điểm: {self._money(price_preview.get('tien_phu_phi_mua_cao_diem'))}  |  "
                      f"Tạm tính (chưa gồm dịch vụ): {self._money(price_preview.get('tong_tien_phong_va_phu_phi'))}  |  {season_label}"),
                bg="#FFF7ED", fg="#9A3412", font=("Arial", 10, "bold"),
                anchor="w", padx=10, pady=8
            ).pack(fill="x", padx=20, pady=(0, 5))
            if season_lines:
                tk.Label(dialog, text="Chi tiết đêm cao điểm: " + "; ".join(season_lines),
                         bg="white", fg="#9A3412", wraplength=680, justify="left"
                         ).pack(anchor="w", padx=20, pady=(0, 8))
        except APIError as exc:
            messagebox.showerror("Không tính được giá mùa cao điểm", str(exc), parent=dialog)
            dialog.destroy()
            return

        table = tk.Frame(dialog, bg="white")
        table.pack(fill="both", expand=True, padx=20)
        headers = tk.Frame(table, bg="#EAF0F6")
        headers.pack(fill="x")
        tk.Label(headers, text="Chọn", width=9, bg="#EAF0F6", anchor="w",
                 font=("Arial", 9, "bold")).pack(side="left", padx=6, pady=8)
        tk.Label(headers, text="Dịch vụ", width=31, bg="#EAF0F6", anchor="w",
                 font=("Arial", 9, "bold")).pack(side="left", padx=4)
        tk.Label(headers, text="Đơn giá", width=15, bg="#EAF0F6", anchor="e",
                 font=("Arial", 9, "bold")).pack(side="left", padx=4)
        tk.Label(headers, text="Số lượng", width=10, bg="#EAF0F6", anchor="center",
                 font=("Arial", 9, "bold")).pack(side="left", padx=4)

        rows = []
        if services:
            for service in services:
                line = tk.Frame(table, bg="white", highlightbackground="#E5E7EB",
                                highlightthickness=1)
                line.pack(fill="x", pady=2)
                selected_var = tk.BooleanVar(value=True)
                quantity_var = tk.StringVar(value=str(service.get("so_luong", 1)))
                tk.Checkbutton(line, variable=selected_var, bg="white",
                               activebackground="white").pack(side="left", padx=(12, 18))
                tk.Label(line, text=service.get("ten", ""), bg="white",
                         anchor="w", width=30).pack(side="left", padx=4, pady=9)
                tk.Label(line, text=self._money(service.get("don_gia")),
                         bg="white", anchor="e", width=15).pack(side="left", padx=4)
                tk.Spinbox(line, from_=1, to=99, width=6, textvariable=quantity_var,
                           justify="center").pack(side="left", padx=12)
                rows.append((service, selected_var, quantity_var))
        else:
            tk.Label(table, text="Phòng này chưa có dịch vụ mặc định.",
                     bg="white", fg="#64748B").pack(anchor="w", pady=18)

        footer = tk.Frame(dialog, bg="white")
        footer.pack(fill="x", padx=20, pady=16)

        def confirm_booking():
            chosen = []
            try:
                for service, checked, quantity in rows:
                    if checked.get():
                        qty = int(quantity.get())
                        if qty <= 0:
                            raise ValueError
                        chosen.append({
                            "dichvu_id": int(service["dichvu_id"]),
                            "so_luong": qty,
                        })
            except (ValueError, TypeError, KeyError):
                messagebox.showerror("Số lượng không hợp lệ",
                                     "Số lượng dịch vụ phải là số nguyên lớn hơn 0.",
                                     parent=dialog)
                return

            if not messagebox.askyesno(
                "Xác nhận đặt phòng",
                f"Đặt phòng {room.get('so_phong')} từ {self.checkin_var.get()} đến "
                f"{self.checkout_var.get()} với {len(chosen)} dịch vụ đã chọn?",
                parent=dialog
            ):
                return

            try:
                created = api_client.post("/api/customer/bookings", {
                    "phong_id": room_id,
                    "ngay_nhan": self.checkin_var.get().strip(),
                    "ngay_tra": self.checkout_var.get().strip(),
                    "dich_vu": chosen,
                })
                dialog.destroy()
                rates = []
                for night in created.get("chi_tiet_mua_cao_diem") or []:
                    if night.get("mua_cao_diem_id") is not None:
                        rate = str(night.get("he_so_gia", "")).rstrip("0").rstrip(".")
                        if rate and rate not in rates:
                            rates.append(rate)
                messagebox.showinfo(
                    "Đặt phòng thành công",
                    f"{created.get('message')}\nMã Booking: {created.get('booking_id')}\n"
                    f"Tiền phòng cơ bản: {self._money(created.get('tien_phong_du_kien'))}\n"
                    f"Phụ phí mùa cao điểm: {self._money(created.get('tien_phu_phi_mua_cao_diem'))}\n"
                    f"Tiền phòng + phụ phí: {self._money(created.get('tong_tien_phong_va_phu_phi'))}\n"
                    f"Hệ số phụ thu: {', '.join('+' + r for r in rates) if rates else 'Không áp dụng'}\n"
                    f"Số dịch vụ đã chọn: {len(created.get('dich_vu', []))}",
                    parent=self.frame
                )
                self.refresh_bookings()
                self.tabs.select(self.bookings_tab)
            except APIError as exc:
                messagebox.showerror("Không thể đặt phòng", str(exc), parent=dialog)

        tk.Button(
            footer, text="HỦY", command=dialog.destroy, bg="#E5E7EB",
            fg=self.NAVY, relief="flat", padx=18, pady=9
        ).pack(side="right", padx=(8, 0))
        tk.Button(
            footer, text="XÁC NHẬN ĐẶT PHÒNG", command=confirm_booking,
            bg=self.GREEN, fg="white", relief="flat", padx=18, pady=9
        ).pack(side="right")

    def _peak_fee_text(self, row):
        amount = self._money(row.get("tien_phu_phi_mua_cao_diem", 0))
        factors = []
        for night in row.get("chi_tiet_mua_cao_diem") or []:
            if night.get("mua_cao_diem_id") is not None:
                value = str(night.get("he_so_gia", "")).rstrip("0").rstrip(".")
                if value and value not in factors:
                    factors.append(value)
        return amount + (f" (+{', '.join(factors)})" if factors else "")

    def refresh_bookings(self):
        if not hasattr(self, "bookings_tree"):
            return
        try:
            result = api_client.get("/api/customer/bookings")
            rows = result.get("bookings", [])
            for item in self.bookings_tree.get_children():
                self.bookings_tree.delete(item)
            self.booking_rows = {}
            for row in rows:
                booking_id = int(row["booking_id"])
                self.booking_rows[booking_id] = row
                self.bookings_tree.insert("", "end", iid=str(booking_id), values=(
                    booking_id, row.get("so_phong"), row.get("loai_phong"), self._date(row.get("ngay_nhan")),
                    self._date(row.get("ngay_tra")), row.get("so_dem"),
                    self._money(row.get("tien_phong_du_kien")),
                    self._peak_fee_text(row),
                    row.get("trang_thai"), self._money(row.get("da_thanh_toan"))))
        except APIError as exc:
            messagebox.showerror("Lỗi tải Booking", str(exc), parent=self.frame)

    def _selected_booking_id(self):
        selected = self.bookings_tree.selection()
        if not selected:
            messagebox.showwarning("Chưa chọn Booking", "Hãy chọn Booking cần thao tác.", parent=self.frame)
            return None
        return int(selected[0])

    def show_booking_detail(self):
        booking_id = self._selected_booking_id()
        if booking_id is None:
            return
        try:
            detail = api_client.get(f"/api/customer/bookings/{booking_id}")
            lines = [f"Booking #{booking_id}", f"Phòng: {detail.get('so_phong')}",
                     f"Trạng thái: {detail.get('trang_thai')}",
                     f"Thời gian: {self._date(detail.get('ngay_nhan'))} - {self._date(detail.get('ngay_tra'))}",
                     f"Tiền phòng cơ bản: {self._money(detail.get('tien_phong_du_kien'))}",
                     f"Phụ phí mùa cao điểm: {self._money(detail.get('tien_phu_phi_mua_cao_diem'))}",
                     f"Áp dụng mùa cao điểm: {'Có' if detail.get('ap_dung_mua_cao_diem') else 'Không'}",
                     "", "CHI TIẾT GIÁ THEO ĐÊM:"]
            lines.extend([
                (f"• {night.get('ngay')}: phòng {self._money(night.get('tien_dem'))}; "
                 f"phụ thu +{night.get('he_so_gia')} = {self._money(night.get('phi_mua_cao_diem'))}")
                for night in (detail.get('chi_tiet_mua_cao_diem') or [])
            ] or ["• Không có dữ liệu chi tiết giá theo đêm"])
            lines.extend(["", "DỊCH VỤ:"])
            lines.extend([f"• {s.get('ten')} × {s.get('so_luong')}: {self._money(s.get('thanh_tien'))}" for s in detail.get("dich_vu", [])] or ["• Chưa có dịch vụ phát sinh"])
            lines.extend(["", "THANH TOÁN:"])
            lines.extend([
                f"• Pay #{p.get('pay_id')} - {p.get('status')} - {self._money(p.get('so_tien'))} | "
                f"Phụ phí mùa cao điểm: {self._money(p.get('tien_phu_phi_mua_cao_diem'))} "
                f"({'Có' if p.get('ap_dung_mua_cao_diem') else 'Không'})"
                for p in detail.get("thanh_toan", [])
            ] or ["• Chưa có giao dịch"])
            messagebox.showinfo("Chi tiết Booking", "\n".join(lines), parent=self.frame)
        except APIError as exc:
            messagebox.showerror("Lỗi", str(exc), parent=self.frame)

    def cancel_selected_booking(self):
        booking_id = self._selected_booking_id()
        if booking_id is None:
            return
        if not messagebox.askyesno("Xác nhận hủy", f"Bạn có chắc muốn hủy Booking #{booking_id}?", parent=self.frame):
            return
        try:
            result = api_client.post(f"/api/customer/bookings/{booking_id}/cancel", {})
            messagebox.showinfo("Hủy Booking", result.get("message", "Đã hủy Booking."), parent=self.frame)
            self.refresh_bookings()
        except APIError as exc:
            messagebox.showerror("Không thể hủy", str(exc), parent=self.frame)

    def request_payment(self):
        booking_id = self._selected_booking_id()
        if booking_id is None:
            return
        method = self.method_var.get().strip()
        confirmation = (
            f"Tạo hóa đơn cho Booking #{booking_id} bằng {method}?\n\n"
            + ("Sau khi tạo, ứng dụng sẽ hiển thị QR để chuyển khoản. Pay chỉ tự chuyển THÀNH CÔNG khi SePay xác thực tiền vào đúng số tiền và nội dung."
               if method == "CHUYEN_KHOAN" else
               "Giao dịch sẽ ở trạng thái CHỜ THANH TOÁN cho đến khi nhân viên xác nhận đã nhận tiền.")
        )
        if not messagebox.askyesno("Yêu cầu thanh toán", confirmation, parent=self.frame):
            return
        try:
            result = api_client.post(f"/api/customer/bookings/{booking_id}/payment", {"method": method})
            invoice = result.get("invoice", {})
            self.refresh_invoices()
            self.refresh_bookings()
            self.tabs.select(self.invoices_tab)
            if method == "CHUYEN_KHOAN" and result.get("qr_available", True):
                pay_id = invoice.get("pay_id")
                if pay_id:
                    self.show_qr_payment(int(pay_id))
                else:
                    messagebox.showwarning(
                        "Thiếu mã thanh toán",
                        "Hóa đơn đã được tạo nhưng API không trả về Pay ID nên chưa thể hiển thị QR. Hãy kiểm tra giao dịch trong trang quản trị.",
                        parent=self.frame,
                    )
            else:
                messagebox.showinfo(
                    "Đã tạo yêu cầu thanh toán",
                    f"{result.get('message')}\nMã hóa đơn: {invoice.get('hoa_don_id', 'N/A')}\nTổng tiền: {self._money(invoice.get('tong_tien'))}",
                    parent=self.frame,
                )
        except APIError as exc:
            messagebox.showerror("Không thể tạo hóa đơn", str(exc), parent=self.frame)

    def show_qr_payment(self, pay_id):
        """Display VietQR and poll the API; the customer cannot mark the payment as paid."""
        try:
            qr = api_client.get(f"/api/customer/payments/{pay_id}/qr")
        except APIError as exc:
            messagebox.showerror("Không thể tạo QR", str(exc), parent=self.frame)
            return

        if qr.get("already_paid") or qr.get("status") == "THANH_CONG":
            messagebox.showinfo("Thanh toán", "Giao dịch này đã được xác nhận thành công.", parent=self.frame)
            self.refresh_invoices()
            self.refresh_bookings()
            return

        window = tk.Toplevel(self.frame)
        window.title(f"Thanh toán QR - Pay #{pay_id}")
        window.geometry("560x750")
        window.resizable(False, False)
        window.transient(self.frame.winfo_toplevel())
        window.configure(bg="white")

        tk.Label(window, text="THANH TOÁN CHUYỂN KHOẢN QR", bg="white", fg=self.NAVY,
                 font=("Arial", 16, "bold")).pack(pady=(18, 4))
        tk.Label(window, text=f"Pay #{pay_id}  ·  Booking #{qr.get('booking_id')}", bg="white",
                 fg="#64748B", font=("Arial", 10)).pack(pady=(0, 10))

        image_label = tk.Label(window, bg="white")
        image_label.pack(pady=5)
        try:
            request = Request(qr["qr_url"], headers={"User-Agent": "HotelManagement/1.0"})
            with urlopen(request, timeout=20) as response:
                image_bytes = response.read()
            photo = tk.PhotoImage(data=base64.b64encode(image_bytes).decode("ascii"))
            scale = max(1, (max(photo.width(), photo.height()) + 319) // 320)
            if scale > 1:
                photo = photo.subsample(scale, scale)
            image_label.configure(image=photo)
            image_label.image = photo
        except Exception as exc:
            window.destroy()
            messagebox.showerror(
                "Không tải được ảnh QR",
                f"Không tải được mã QR từ VietQR: {exc}\n\nKiểm tra kết nối Internet rồi thử lại.",
                parent=self.frame,
            )
            return

        details = tk.Frame(window, bg="#F8FAFC", padx=16, pady=12)
        details.pack(fill="x", padx=28, pady=8)
        rows = [
            ("Ngân hàng", qr.get("bank_code")),
            ("Chủ tài khoản", qr.get("account_name")),
            ("Số tài khoản", qr.get("account_number")),
            ("Số tiền thanh toán", self._money(qr.get("amount"))),
            ("Mùa cao điểm", qr.get("peak_season_label", "KHÔNG")),
            ("Phụ thu mùa cao điểm", self._money(qr.get("peak_season_amount", 0))),
            ("Nội dung chuyển khoản", qr.get("payment_code")),
        ]
        for label, value in rows:
            line = tk.Frame(details, bg="#F8FAFC")
            line.pack(fill="x", pady=3)
            tk.Label(line, text=label, bg="#F8FAFC", fg="#64748B", anchor="w").pack(side="left")
            tk.Label(line, text=str(value or ""), bg="#F8FAFC", fg=self.NAVY,
                     font=("Arial", 9, "bold"), anchor="e", wraplength=280).pack(side="right")

        tk.Button(
            window, text="SAO CHÉP NỘI DUNG CHUYỂN KHOẢN",
            command=lambda: self._copy_payment_code(qr.get("payment_code", ""), window),
            bg="#E2E8F0", fg=self.NAVY, relief="flat", padx=12, pady=8,
        ).pack(pady=(5, 8))
        status_var = tk.StringVar(value="Đang chờ ngân hàng xác nhận giao dịch...")
        status_label = tk.Label(window, textvariable=status_var, bg="white", fg="#B45309",
                                font=("Arial", 10, "bold"), wraplength=480)
        status_label.pack(pady=(4, 8))
        tk.Label(window,
                 text=("Dùng chức năng Quét QR chuyển khoản trong ứng dụng ngân hàng. Camera/ứng dụng đọc QR thông thường có thể chỉ hiển thị chuỗi dữ liệu. "
                       "Vui lòng chuyển đúng số tiền và giữ nguyên nội dung. Không chuyển khoản vào tài khoản khác. Không đóng cửa sổ nếu muốn theo dõi tự động."),
                 bg="white", fg="#64748B", wraplength=480, justify="center").pack(padx=24, pady=(0, 10))
        tk.Button(window, text="ĐÓNG", command=window.destroy, bg="#475569", fg="white",
                  relief="flat", padx=24, pady=8).pack(pady=(0, 16))
        window.grab_set()

        def poll_payment_status():
            if not window.winfo_exists():
                return
            try:
                result = api_client.get(f"/api/customer/payments/{pay_id}/status")
                payment = result.get("payment", {})
                status = payment.get("status")
                if status == "THANH_CONG":
                    status_var.set("THANH TOÁN THÀNH CÔNG – hệ thống đã nhận và xác thực tiền vào.")
                    status_label.configure(fg="#15803D")
                    self.refresh_invoices()
                    self.refresh_bookings()
                    return
                if status in ("THAT_BAI", "HOAN_TIEN"):
                    status_var.set(f"Giao dịch hiện ở trạng thái {status}. Vui lòng liên hệ lễ tân.")
                    status_label.configure(fg="#B91C1C")
                    return
                status_var.set("Đang chờ ngân hàng xác nhận giao dịch... Trạng thái sẽ tự cập nhật.")
            except APIError:
                status_var.set("Chưa kết nối được để kiểm tra. Ứng dụng sẽ thử lại...")
            window.after(3000, poll_payment_status)

        window.after(1000, poll_payment_status)

    @staticmethod
    def _copy_payment_code(payment_code, parent):
        if not payment_code:
            return
        parent.clipboard_clear()
        parent.clipboard_append(payment_code)
        messagebox.showinfo("Đã sao chép", "Đã sao chép nội dung chuyển khoản.", parent=parent)

    def refresh_invoices(self):
        if not hasattr(self, "invoices_tree"):
            return
        try:
            result = api_client.get("/api/customer/invoices")
            rows = result.get("invoices", [])
            for item in self.invoices_tree.get_children():
                self.invoices_tree.delete(item)
            self.invoice_rows = {}
            for row in rows:
                invoice_id = int(row["hoa_don_id"])
                self.invoice_rows[invoice_id] = row
                self.invoices_tree.insert("", "end", iid=str(invoice_id), values=(
                    invoice_id, row.get("booking_id"), row.get("so_phong"), self._money(row.get("tien_phong")),
                    self._peak_fee_text(row),
                    self._money(row.get("tien_dich_vu")), self._money(row.get("tong_tien")), row.get("method"),
                    row.get("trang_thai_thanh_toan"), self._date(row.get("ngay_lap"))))
        except APIError as exc:
            messagebox.showerror("Lỗi tải hóa đơn", str(exc), parent=self.frame)
