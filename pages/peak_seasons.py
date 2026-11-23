
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from decimal import Decimal

from api_client import api_client, APIError


class PeakSeasonsPage:
    def __init__(self, parent):
        self.parent = parent

        self.navy = "#101F35"
        self.gold = "#D5AD5B"
        self.white = "#FFFFFF"
        self.background = "#F4F6F9"
        self.gray = "#8793A5"
        self.red = "#C0392B"

        self.selected_id = None
        self.seasons = []
        self.seasons_by_id = {}
        self.rooms = []
        self.rooms_by_number = {}

        self.build_ui()
        self.load_rooms()
        self.load_peak_seasons()

    # ==================================================
    # GIAO DIỆN
    # ==================================================
    def build_ui(self):
        tk.Label(
            self.parent,
            text="QUẢN LÝ MÙA CAO ĐIỂM",
            font=("Arial", 24, "bold"),
            fg=self.navy,
            bg=self.background
        ).pack(anchor="w", padx=35, pady=(25, 5))

        tk.Label(
            self.parent,
            text="Thiết lập một mùa cao điểm cho nhiều phòng, mỗi phòng có tỷ lệ phụ thu riêng",
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
            text="Tìm kiếm:",
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
            lambda event: self.search_peak_seasons()
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
            text=" THÔNG TIN MÙA CAO ĐIỂM ",
            font=("Arial", 11, "bold"),
            fg=self.navy,
            bg=self.white,
            padx=20,
            pady=15
        )
        form_frame.pack(fill="x", padx=35, pady=(0, 15))

        form_frame.columnconfigure(0, weight=1)
        form_frame.columnconfigure(1, weight=1)

        # Phòng
        tk.Label(
            form_frame,
            text="Phòng áp dụng",
            font=("Arial", 10, "bold"),
            fg=self.navy,
            bg=self.white
        ).grid(row=0, column=0, sticky="w", padx=10, pady=7)

        self.room_var = tk.StringVar()

        self.room_combo = ttk.Combobox(
            form_frame,
            textvariable=self.room_var,
            state="readonly",
            font=("Arial", 10),
            width=30
        )
        self.room_combo.grid(
            row=1, column=0, sticky="ew",
            padx=10, pady=(0, 10)
        )
        self.room_combo.bind("<<ComboboxSelected>>", self.update_rate_from_room_type)

        # Ngày bắt đầu
        tk.Label(
            form_frame,
            text="Ngày bắt đầu (YYYY-MM-DD)",
            font=("Arial", 10, "bold"),
            fg=self.navy,
            bg=self.white
        ).grid(row=0, column=1, sticky="w", padx=10, pady=7)

        self.start_entry = tk.Entry(
            form_frame,
            font=("Arial", 10)
        )
        self.start_entry.grid(
            row=1, column=1, sticky="ew",
            padx=10, pady=(0, 10)
        )

        # Ngày kết thúc
        tk.Label(
            form_frame,
            text="Ngày kết thúc (YYYY-MM-DD)",
            font=("Arial", 10, "bold"),
            fg=self.navy,
            bg=self.white
        ).grid(row=2, column=0, sticky="w", padx=10, pady=7)

        self.end_entry = tk.Entry(
            form_frame,
            font=("Arial", 10)
        )
        self.end_entry.grid(
            row=3, column=0, sticky="ew",
            padx=10, pady=(0, 10)
        )

        # Hệ số phụ thu mùa cao điểm
        tk.Label(
            form_frame,
            text="Hệ số phụ thu (0.1–0.6)",
            font=("Arial", 10, "bold"),
            fg=self.navy,
            bg=self.white
        ).grid(row=2, column=1, sticky="w", padx=10, pady=7)

        self.factor_entry = ttk.Combobox(
            form_frame,
            font=("Arial", 10),
            state="readonly",
            values=("0.6", "0.5", "0.4", "0.35", "0.3", "0.25", "0.2", "0.1")
        )
        self.factor_entry.grid(
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
            text="THÊM MÙA CAO ĐIỂM",
            command=self.add_peak_season,
            bg=self.navy,
            fg=self.white,
            font=("Arial", 9, "bold"),
            relief="flat",
            padx=15,
            pady=10,
            cursor="hand2"
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            button_frame,
            text="CẬP NHẬT",
            command=self.update_peak_season,
            bg=self.gold,
            fg=self.navy,
            font=("Arial", 9, "bold"),
            relief="flat",
            padx=18,
            pady=10,
            cursor="hand2"
        ).pack(side="left", padx=8)

        tk.Button(
            button_frame,
            text="XÓA",
            command=self.delete_peak_season,
            bg=self.red,
            fg=self.white,
            font=("Arial", 9, "bold"),
            relief="flat",
            padx=22,
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
            text="DANH SÁCH MÙA CAO ĐIỂM",
            font=("Arial", 12, "bold"),
            fg=self.navy,
            bg=self.white
        ).pack(anchor="w", padx=18, pady=12)

        columns = (
            "id",
            "phong_id",
            "so_phong",
            "tu_ngay",
            "den_ngay",
            "he_so_gia"
        )

        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            height=9
        )

        headings = {
            "id": "Mã mùa",
            "phong_id": "Mã phòng",
            "so_phong": "Số phòng",
            "tu_ngay": "Ngày bắt đầu",
            "den_ngay": "Ngày kết thúc",
            "he_so_gia": "Hệ số phụ thu"
        }

        widths = {
            "id": 80,
            "phong_id": 90,
            "so_phong": 110,
            "tu_ngay": 150,
            "den_ngay": 150,
            "he_so_gia": 110
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
            self.select_peak_season
        )

    # ==================================================
    # TẢI DANH SÁCH PHÒNG TỪ API
    # ==================================================
    def load_rooms(self):
        try:
            rows = api_client.get("/api/rooms/")

            if not isinstance(rows, list):
                raise APIError(
                    "API phòng không trả về danh sách hợp lệ."
                )

            self.rooms = rows
            self.rooms_by_number = {}

            room_options = []

            for room in rows:
                room_id = int(room["id"])
                room_number = str(room["so_phong"])

                display_name = f"{room_number} - {room.get('ten_loai_phong', '')} - ID: {room_id}"

                room_options.append(display_name)
                self.rooms_by_number[display_name] = room_id

            self.room_combo["values"] = room_options

        except (APIError, KeyError, TypeError, ValueError) as e:
            messagebox.showerror(
                "Lỗi tải danh sách phòng",
                str(e)
            )

    def update_rate_from_room_type(self, event=None):
        selected = self.room_var.get().strip()
        room_id = self.rooms_by_number.get(selected)
        room = next((r for r in self.rooms if int(r.get("id", -1)) == int(room_id or -1)), None)
        if not room:
            return
        rates = {"standard": "0.20", "deluxe": "0.25", "vip": "0.30", "family": "0.35"}
        rate = rates.get(str(room.get("ten_loai_phong", "")).strip().casefold())
        if rate is None:
            messagebox.showerror("Chưa cấu hình", f"Chưa có tỷ lệ mùa cao điểm cho loại phòng {room.get('ten_loai_phong')}.")
            self.factor_entry.set("")
            return
        self.factor_entry.set(rate)

    # ==================================================
    # TẢI DANH SÁCH MÙA CAO ĐIỂM TỪ API
    # ==================================================
    def load_peak_seasons(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        try:
            rows = api_client.get("/api/peak-seasons/")

            if not isinstance(rows, list):
                raise APIError(
                    "API mùa cao điểm không trả về danh sách hợp lệ."
                )

            self.seasons = rows
            self.seasons_by_id = {
                int(row["id"]): row for row in rows
            }

            self.display_peak_seasons(rows)

        except (APIError, KeyError, TypeError, ValueError) as e:
            messagebox.showerror(
                "Lỗi tải mùa cao điểm",
                str(e)
            )

    # ==================================================
    # HIỂN THỊ DỮ LIỆU
    # ==================================================
    @staticmethod
    def format_surcharge_rate(value):
        try:
            rate = (Decimal(str(value)) * Decimal("100")).quantize(Decimal("1"))
            return f"{rate}%"
        except Exception:
            return str(value if value is not None else "")

    def display_peak_seasons(self, rows):
        for item in self.tree.get_children():
            self.tree.delete(item)

        for row in rows:
            room_id = row.get("phong_id", "")

            room_number = row.get("so_phong", "")

            if not room_number:
                for room in self.rooms:
                    if str(room.get("id")) == str(room_id):
                        room_number = room.get("so_phong", "")
                        break

            start_date = str(row.get("tu_ngay", ""))[:10]
            end_date = str(row.get("den_ngay", ""))[:10]

            self.tree.insert(
                "",
                "end",
                values=(
                    row.get("id", ""),
                    room_id,
                    room_number,
                    start_date,
                    end_date,
                    self.format_surcharge_rate(row.get("he_so_gia", ""))
                )
            )

    # ==================================================
    # TÌM KIẾM
    # ==================================================
    def search_peak_seasons(self):
        keyword = self.search_entry.get().strip().lower()

        filtered_rows = []

        for row in self.seasons:
            room_id = str(row.get("phong_id", ""))
            room_number = str(row.get("so_phong", ""))
            season_id = str(row.get("id", ""))

            if (
                keyword in room_id.lower()
                or keyword in room_number.lower()
                or keyword in season_id.lower()
            ):
                filtered_rows.append(row)

        self.display_peak_seasons(filtered_rows)

    def reset_search(self):
        self.search_entry.delete(0, tk.END)
        self.load_peak_seasons()

    # ==================================================
    # CHỌN MỘT MÙA CAO ĐIỂM
    # ==================================================
    def select_peak_season(self, event=None):
        selected = self.tree.selection()

        if not selected:
            return

        values = self.tree.item(
            selected[0],
            "values"
        )

        self.selected_id = int(values[0])

        season = self.seasons_by_id.get(
            self.selected_id
        )

        if season is None:
            messagebox.showerror(
                "Lỗi dữ liệu",
                "Không tìm thấy mùa cao điểm đã chọn."
            )
            return

        self.room_var.set("")

        room_id = str(season.get("phong_id", ""))

        for display_name, current_room_id in self.rooms_by_number.items():
            if str(current_room_id) == room_id:
                self.room_var.set(display_name)
                break

        self.start_entry.delete(0, tk.END)
        self.start_entry.insert(
            0,
            str(season.get("tu_ngay", ""))[:10]
        )

        self.end_entry.delete(0, tk.END)
        self.end_entry.insert(
            0,
            str(season.get("den_ngay", ""))[:10]
        )

        raw_factor = season.get("he_so_gia", "")
        try:
            self.factor_entry.set(f"{float(raw_factor):.2f}".rstrip("0").rstrip("."))
        except (TypeError, ValueError):
            self.factor_entry.set(str(raw_factor))

    # ==================================================
    # KIỂM TRA DỮ LIỆU
    # ==================================================
    def validate_input(self):
        room_display = self.room_var.get().strip()
        start_date = self.start_entry.get().strip()
        end_date = self.end_entry.get().strip()
        factor = self.factor_entry.get().strip()

        if not room_display or not start_date or not end_date:
            messagebox.showwarning(
                "Thiếu thông tin",
                "Vui lòng nhập đầy đủ thông tin mùa cao điểm."
            )
            return None

        if room_display not in self.rooms_by_number:
            messagebox.showwarning(
                "Phòng không hợp lệ",
                "Vui lòng chọn phòng từ danh sách."
            )
            return None

        try:
            start = datetime.strptime(
                start_date,
                "%Y-%m-%d"
            ).date()

            end = datetime.strptime(
                end_date,
                "%Y-%m-%d"
            ).date()

            if end <= start:
                messagebox.showwarning(
                    "Ngày không hợp lệ",
                    "Ngày kết thúc phải sau ngày bắt đầu."
                )
                return None

            selected_room = next((r for r in self.rooms if int(r.get("id", -1)) == int(self.rooms_by_number[room_display])), None)
            rates = {"standard": Decimal("0.20"), "deluxe": Decimal("0.25"),
                     "vip": Decimal("0.30"), "family": Decimal("0.35")}
            type_name = str((selected_room or {}).get("ten_loai_phong", "")).strip().casefold()
            if type_name not in rates:
                messagebox.showwarning("Loại phòng chưa hỗ trợ", f"Chưa cấu hình phụ thu cho loại phòng {(selected_room or {}).get('ten_loai_phong', '')}.")
                return None
            factor_value = float(rates[type_name])
            self.factor_entry.set(f"{factor_value:.2f}")

        except ValueError:
            messagebox.showwarning(
                "Dữ liệu không hợp lệ",
                "Ngày phải theo định dạng YYYY-MM-DD và hệ số phụ thu phải thuộc danh sách cho phép."
            )
            return None

        return {
            "phong_id": self.rooms_by_number[room_display],
            "tu_ngay": start_date,
            "den_ngay": end_date,
            "he_so_gia": factor_value
        }

    # ==================================================
    # THÊM MÙA CAO ĐIỂM
    # ==================================================
    def add_peak_season(self):
        payload = self.validate_input()

        if payload is None:
            return

        try:
            result = api_client.post(
                "/api/peak-seasons/",
                payload
            )

            messagebox.showinfo(
                "Thành công",
                result.get(
                    "message",
                    "Thêm mùa cao điểm thành công."
                )
            )

            self.clear_form()
            self.load_peak_seasons()

        except APIError as e:
            messagebox.showerror(
                "Không thể thêm mùa cao điểm",
                str(e)
            )

    # ==================================================
    # CẬP NHẬT MÙA CAO ĐIỂM
    # ==================================================
    def update_peak_season(self):
        if self.selected_id is None:
            messagebox.showwarning(
                "Chưa chọn dữ liệu",
                "Vui lòng chọn mùa cao điểm cần cập nhật."
            )
            return

        payload = self.validate_input()

        if payload is None:
            return

        try:
            result = api_client.put(
                f"/api/peak-seasons/{self.selected_id}",
                payload
            )

            messagebox.showinfo(
                "Thành công",
                result.get(
                    "message",
                    "Cập nhật mùa cao điểm thành công."
                )
            )

            self.clear_form()
            self.load_peak_seasons()

        except APIError as e:
            messagebox.showerror(
                "Không thể cập nhật",
                str(e)
            )

    # ==================================================
    # XÓA MÙA CAO ĐIỂM
    # ==================================================
    def delete_peak_season(self):
        if self.selected_id is None:
            messagebox.showwarning(
                "Chưa chọn dữ liệu",
                "Vui lòng chọn mùa cao điểm cần xóa."
            )
            return

        confirm = messagebox.askyesno(
            "Xác nhận xóa",
            "Bạn có chắc chắn muốn xóa mùa cao điểm này không?"
        )

        if not confirm:
            return

        try:
            result = api_client.delete(
                f"/api/peak-seasons/{self.selected_id}"
            )

            messagebox.showinfo(
                "Thành công",
                result.get(
                    "message",
                    "Xóa mùa cao điểm thành công."
                )
            )

            self.clear_form()
            self.load_peak_seasons()

        except APIError as e:
            messagebox.showerror(
                "Không thể xóa",
                str(e)
            )

    # ==================================================
    # XÓA TRẮNG FORM
    # ==================================================
    def clear_form(self):
        self.selected_id = None

        self.room_var.set("")

        self.start_entry.delete(0, tk.END)
        self.end_entry.delete(0, tk.END)
        self.factor_entry.set("")

        for item in self.tree.selection():
            self.tree.selection_remove(item)
