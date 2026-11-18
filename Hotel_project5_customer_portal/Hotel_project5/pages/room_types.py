
import tkinter as tk
from tkinter import ttk, messagebox

from api_client import api_client, APIError


class RoomTypesPage:
    def __init__(self, parent):
        self.parent = parent

        self.navy = "#101F35"
        self.gold = "#D5AD5B"
        self.white = "#FFFFFF"
        self.background = "#F4F6F9"
        self.gray = "#8793A5"

        self.selected_id = None
        self.room_types = []

        self.build_ui()
        self.load_room_types()

    # =====================================
    # GIAO DIỆN
    # =====================================

    def build_ui(self):
        tk.Label(
            self.parent,
            text="QUẢN LÝ LOẠI PHÒNG",
            font=("Arial", 24, "bold"),
            fg=self.navy,
            bg=self.background
        ).pack(anchor="w", padx=35, pady=(30, 5))

        tk.Label(
            self.parent,
            text="Quản lý thông tin, giá và sức chứa của từng loại phòng",
            font=("Arial", 11),
            fg=self.gray,
            bg=self.background
        ).pack(anchor="w", padx=35, pady=(0, 25))

        # Tìm kiếm
        search_frame = tk.Frame(
            self.parent,
            bg=self.white,
            highlightbackground="#DDE3EA",
            highlightthickness=1
        )
        search_frame.pack(fill="x", padx=35, pady=(0, 20))

        tk.Label(
            search_frame,
            text="Tìm loại phòng:",
            font=("Arial", 11, "bold"),
            bg=self.white,
            fg=self.navy
        ).pack(side="left", padx=(20, 10), pady=18)

        self.search_entry = tk.Entry(
            search_frame,
            font=("Arial", 11),
            width=30
        )
        self.search_entry.pack(side="left", padx=5, pady=15)

        self.search_entry.bind(
            "<KeyRelease>",
            lambda event: self.search_room_types()
        )

        tk.Button(
            search_frame,
            text="LÀM MỚI",
            command=self.reset_search,
            font=("Arial", 10, "bold"),
            bg=self.navy,
            fg=self.white,
            relief="flat",
            padx=20,
            pady=10,
            cursor="hand2"
        ).pack(side="left", padx=15)

        # Form thông tin
        form_frame = tk.LabelFrame(
            self.parent,
            text=" THÔNG TIN LOẠI PHÒNG ",
            font=("Arial", 12, "bold"),
            bg=self.white,
            fg=self.navy,
            padx=20,
            pady=20
        )
        form_frame.pack(fill="x", padx=35, pady=(0, 20))

        form_frame.columnconfigure(0, weight=1)
        form_frame.columnconfigure(1, weight=1)

        tk.Label(
            form_frame,
            text="Tên loại phòng",
            font=("Arial", 10, "bold"),
            bg=self.white,
            fg=self.navy
        ).grid(row=0, column=0, sticky="w", padx=10, pady=(0, 8))

        tk.Label(
            form_frame,
            text="Giá cơ bản (VNĐ)",
            font=("Arial", 10, "bold"),
            bg=self.white,
            fg=self.navy
        ).grid(row=0, column=1, sticky="w", padx=10, pady=(0, 8))

        self.name_entry = tk.Entry(
            form_frame,
            font=("Arial", 11)
        )
        self.name_entry.grid(
            row=1, column=0, sticky="ew",
            padx=10, pady=(0, 18), ipady=5
        )

        self.price_entry = tk.Entry(
            form_frame,
            font=("Arial", 11)
        )
        self.price_entry.grid(
            row=1, column=1, sticky="ew",
            padx=10, pady=(0, 18), ipady=5
        )

        tk.Label(
            form_frame,
            text="Sức chứa (người)",
            font=("Arial", 10, "bold"),
            bg=self.white,
            fg=self.navy
        ).grid(row=2, column=0, sticky="w", padx=10, pady=(0, 8))

        self.capacity_entry = tk.Entry(
            form_frame,
            font=("Arial", 11)
        )
        self.capacity_entry.grid(
            row=3, column=0, sticky="ew",
            padx=10, pady=(0, 18), ipady=5
        )

        # Các nút chức năng
        button_frame = tk.Frame(
            form_frame,
            bg=self.white
        )
        button_frame.grid(
            row=4, column=0, columnspan=2,
            sticky="w", padx=10, pady=(0, 5)
        )

        tk.Button(
            button_frame,
            text="THÊM LOẠI PHÒNG",
            command=self.add_room_type,
            bg="#218C65",
            fg=self.white,
            font=("Arial", 10, "bold"),
            relief="flat",
            padx=18,
            pady=11,
            cursor="hand2"
        ).pack(side="left", padx=(0, 10))

        tk.Button(
            button_frame,
            text="CẬP NHẬT",
            command=self.update_room_type,
            bg=self.navy,
            fg=self.white,
            font=("Arial", 10, "bold"),
            relief="flat",
            padx=18,
            pady=11,
            cursor="hand2"
        ).pack(side="left", padx=10)

        tk.Button(
            button_frame,
            text="XÓA LOẠI PHÒNG",
            command=self.delete_room_type,
            bg="#C0392B",
            fg=self.white,
            font=("Arial", 10, "bold"),
            relief="flat",
            padx=18,
            pady=11,
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
            pady=11,
            cursor="hand2"
        ).pack(side="left", padx=10)

        # Bảng danh sách
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
            text="DANH SÁCH LOẠI PHÒNG",
            font=("Arial", 13, "bold"),
            fg=self.navy,
            bg=self.white
        ).pack(anchor="w", padx=20, pady=15)

        columns = ("id", "ten", "gia", "suc_chua")

        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            height=12
        )

        self.tree.heading("id", text="Mã loại phòng")
        self.tree.heading("ten", text="Tên loại phòng")
        self.tree.heading("gia", text="Giá cơ bản")
        self.tree.heading("suc_chua", text="Sức chứa")

        self.tree.column("id", width=150, anchor="center")
        self.tree.column("ten", width=250, anchor="center")
        self.tree.column("gia", width=220, anchor="center")
        self.tree.column("suc_chua", width=180, anchor="center")

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
            self.select_room_type
        )

    # =====================================
    # LẤY DANH SÁCH TỪ FASTAPI
    # =====================================

    def load_room_types(self):
        try:
            response = api_client.get("/api/room-types/")

            if not isinstance(response, list):
                raise APIError(
                    "API không trả về danh sách loại phòng hợp lệ."
                )

            self.room_types = response

            self.display_room_types(self.room_types)

        except APIError as e:
            messagebox.showerror(
                "Lỗi API",
                str(e)
            )

    # =====================================
    # HIỂN THỊ DỮ LIỆU
    # =====================================

    def display_room_types(self, data):
        for item in self.tree.get_children():
            self.tree.delete(item)

        for room_type in data:
            self.tree.insert(
                "",
                "end",
                values=(
                    room_type["id"],
                    room_type["ten"],
                    f'{float(room_type["gia_co_ban"]):,.0f} đ',
                    room_type["suc_chua"]
                )
            )

    # =====================================
    # TÌM KIẾM LOẠI PHÒNG
    # =====================================

    def search_room_types(self):
        keyword = self.search_entry.get().strip().lower()

        filtered = [
            room_type
            for room_type in self.room_types
            if keyword in room_type["ten"].lower()
        ]

        self.display_room_types(filtered)

    # =====================================
    # LÀM MỚI TÌM KIẾM
    # =====================================

    def reset_search(self):
        self.search_entry.delete(0, tk.END)
        self.load_room_types()

    # =====================================
    # CHỌN LOẠI PHÒNG
    # =====================================

    def select_room_type(self, event):
        selected = self.tree.selection()

        if not selected:
            return

        values = self.tree.item(
            selected[0],
            "values"
        )

        self.selected_id = int(values[0])

        # Tìm dữ liệu gốc trong danh sách API
        room_type = next(
            (
                item for item in self.room_types
                if int(item["id"]) == self.selected_id
            ),
            None
        )

        if room_type is None:
            return

        self.clear_entries()

        self.name_entry.insert(
            0,
            room_type["ten"]
        )

        self.price_entry.insert(
            0,
            str(room_type["gia_co_ban"])
        )

        self.capacity_entry.insert(
            0,
            str(room_type["suc_chua"])
        )

    # =====================================
    # KIỂM TRA DỮ LIỆU NHẬP
    # =====================================

    def validate_input(self):
        name = self.name_entry.get().strip()
        price = self.price_entry.get().strip()
        capacity = self.capacity_entry.get().strip()

        if not name or not price or not capacity:
            messagebox.showwarning(
                "Thiếu thông tin",
                "Vui lòng nhập đầy đủ thông tin loại phòng."
            )
            return None

        try:
            price = float(price)
            capacity = int(capacity)

            if price <= 0 or capacity <= 0:
                raise ValueError

        except ValueError:
            messagebox.showwarning(
                "Dữ liệu không hợp lệ",
                "Giá cơ bản và sức chứa phải là số dương hợp lệ."
            )
            return None

        return {
            "ten": name,
            "gia_co_ban": price,
            "suc_chua": capacity
        }

    # =====================================
    # THÊM LOẠI PHÒNG QUA API
    # =====================================

    def add_room_type(self):
        data = self.validate_input()

        if data is None:
            return

        try:
            response = api_client.post(
                "/api/room-types/",
                data
            )

            messagebox.showinfo(
                "Thành công",
                response.get(
                    "message",
                    "Thêm loại phòng thành công."
                )
            )

            self.clear_form()
            self.load_room_types()

        except APIError as e:
            messagebox.showerror(
                "Lỗi thêm loại phòng",
                str(e)
            )

    # =====================================
    # CẬP NHẬT LOẠI PHÒNG QUA API
    # =====================================

    def update_room_type(self):
        if self.selected_id is None:
            messagebox.showwarning(
                "Chưa chọn dữ liệu",
                "Vui lòng chọn loại phòng cần cập nhật."
            )
            return

        data = self.validate_input()

        if data is None:
            return

        try:
            response = api_client.put(
                f"/api/room-types/{self.selected_id}",
                data
            )

            messagebox.showinfo(
                "Thành công",
                response.get(
                    "message",
                    "Cập nhật loại phòng thành công."
                )
            )

            self.clear_form()
            self.load_room_types()

        except APIError as e:
            messagebox.showerror(
                "Lỗi cập nhật",
                str(e)
            )

    # =====================================
    # XÓA LOẠI PHÒNG QUA API
    # =====================================

    def delete_room_type(self):
        if self.selected_id is None:
            messagebox.showwarning(
                "Chưa chọn dữ liệu",
                "Vui lòng chọn loại phòng cần xóa."
            )
            return

        confirm = messagebox.askyesno(
            "Xác nhận xóa",
            "Bạn có chắc chắn muốn xóa loại phòng này không?"
        )

        if not confirm:
            return

        try:
            response = api_client.delete(
                f"/api/room-types/{self.selected_id}"
            )

            messagebox.showinfo(
                "Thành công",
                response.get(
                    "message",
                    "Xóa loại phòng thành công."
                )
            )

            self.clear_form()
            self.load_room_types()

        except APIError as e:
            messagebox.showerror(
                "Không thể xóa",
                str(e)
            )

    # =====================================
    # XÓA NỘI DUNG CÁC Ô NHẬP
    # =====================================

    def clear_entries(self):
        self.name_entry.delete(0, tk.END)
        self.price_entry.delete(0, tk.END)
        self.capacity_entry.delete(0, tk.END)

    # =====================================
    # XÓA TRẮNG BIỂU MẪU
    # =====================================

    def clear_form(self):
        self.selected_id = None

        self.clear_entries()

        for item in self.tree.selection():
            self.tree.selection_remove(item)
