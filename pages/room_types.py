
import tkinter as tk
from tkinter import ttk, messagebox

from database import get_connection


class RoomTypesPage:
    def __init__(self, parent):
        self.parent = parent

        self.navy = "#101F35"
        self.gold = "#D5AD5B"
        self.white = "#FFFFFF"
        self.background = "#F4F6F9"
        self.gray = "#8793A5"

        self.selected_id = None

        self.build_ui()
        self.load_room_types()

    def build_ui(self):
        # Tiêu đề
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

        # Khu vực tìm kiếm
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

        # Khu vực nhập thông tin
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
        button_frame = tk.Frame(form_frame, bg=self.white)
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

        # Danh sách loại phòng
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
        self.tree.configure(yscrollcommand=scrollbar.set)

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

    # Lấy dữ liệu từ MySQL
    def load_room_types(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        connection = get_connection()

        if connection is None:
            messagebox.showerror(
                "Lỗi kết nối",
                "Không thể kết nối đến cơ sở dữ liệu MySQL."
            )
            return

        cursor = None

        try:
            cursor = connection.cursor()

            cursor.execute("""
                SELECT id, ten, gia_co_ban, suc_chua
                FROM loaiphong
                ORDER BY id
            """)

            rows = cursor.fetchall()

            for row in rows:
                self.tree.insert(
                    "",
                    "end",
                    values=(
                        row[0],
                        row[1],
                        f"{float(row[2]):,.0f} đ",
                        row[3]
                    )
                )

        except Exception as e:
            messagebox.showerror("Lỗi", str(e))

        finally:
            if cursor:
                cursor.close()
            connection.close()

    # Tìm kiếm loại phòng
    def search_room_types(self):
        keyword = self.search_entry.get().strip()

        for item in self.tree.get_children():
            self.tree.delete(item)

        connection = get_connection()

        if connection is None:
            messagebox.showerror("Lỗi", "Không thể kết nối MySQL.")
            return

        cursor = None

        try:
            cursor = connection.cursor()

            cursor.execute("""
                SELECT id, ten, gia_co_ban, suc_chua
                FROM loaiphong
                WHERE ten LIKE %s
                ORDER BY id
            """, (f"%{keyword}%",))

            for row in cursor.fetchall():
                self.tree.insert(
                    "",
                    "end",
                    values=(
                        row[0],
                        row[1],
                        f"{float(row[2]):,.0f} đ",
                        row[3]
                    )
                )

        except Exception as e:
            messagebox.showerror("Lỗi", str(e))

        finally:
            if cursor:
                cursor.close()
            connection.close()

    # Làm mới tìm kiếm
    def reset_search(self):
        self.search_entry.delete(0, tk.END)
        self.load_room_types()

    # Chọn loại phòng trong bảng
    def select_room_type(self, event):
        selected = self.tree.selection()

        if not selected:
            return

        values = self.tree.item(selected[0], "values")

        self.selected_id = int(values[0])

        self.clear_entries()

        self.name_entry.insert(0, values[1])

        # Lấy giá trị số thực từ database
        connection = get_connection()

        if connection is None:
            messagebox.showerror("Lỗi", "Không thể kết nối MySQL.")
            return

        cursor = None

        try:
            cursor = connection.cursor()
            cursor.execute(
                "SELECT gia_co_ban FROM loaiphong WHERE id = %s",
                (self.selected_id,)
            )
            result = cursor.fetchone()

            if result:
                self.price_entry.insert(0, str(result[0]))

            self.capacity_entry.insert(0, str(values[3]))

        except Exception as e:
            messagebox.showerror("Lỗi", str(e))

        finally:
            if cursor:
                cursor.close()
            connection.close()

    # Kiểm tra dữ liệu nhập
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

        return name, price, capacity

    # Thêm loại phòng
    def add_room_type(self):
        data = self.validate_input()

        if data is None:
            return

        name, price, capacity = data

        connection = get_connection()

        if connection is None:
            messagebox.showerror("Lỗi", "Không thể kết nối MySQL.")
            return

        cursor = None

        try:
            cursor = connection.cursor()

            cursor.execute("""
                INSERT INTO loaiphong (ten, gia_co_ban, suc_chua)
                VALUES (%s, %s, %s)
            """, (name, price, capacity))

            connection.commit()

            messagebox.showinfo(
                "Thành công",
                "Thêm loại phòng thành công."
            )

            self.clear_form()
            self.load_room_types()

        except Exception as e:
            connection.rollback()
            messagebox.showerror("Lỗi", str(e))

        finally:
            if cursor:
                cursor.close()
            connection.close()

    # Cập nhật loại phòng
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

        name, price, capacity = data

        connection = get_connection()

        if connection is None:
            messagebox.showerror("Lỗi", "Không thể kết nối MySQL.")
            return

        cursor = None

        try:
            cursor = connection.cursor()

            cursor.execute("""
                UPDATE loaiphong
                SET ten = %s,
                    gia_co_ban = %s,
                    suc_chua = %s
                WHERE id = %s
            """, (name, price, capacity, self.selected_id))

            connection.commit()

            messagebox.showinfo(
                "Thành công",
                "Cập nhật loại phòng thành công."
            )

            self.clear_form()
            self.load_room_types()

        except Exception as e:
            connection.rollback()
            messagebox.showerror("Lỗi", str(e))

        finally:
            if cursor:
                cursor.close()
            connection.close()

    # Xóa loại phòng
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

        connection = get_connection()

        if connection is None:
            messagebox.showerror("Lỗi", "Không thể kết nối MySQL.")
            return

        cursor = None

        try:
            cursor = connection.cursor()

            cursor.execute(
                "DELETE FROM loaiphong WHERE id = %s",
                (self.selected_id,)
            )

            connection.commit()

            messagebox.showinfo(
                "Thành công",
                "Xóa loại phòng thành công."
            )

            self.clear_form()
            self.load_room_types()

        except Exception as e:
            connection.rollback()
            messagebox.showerror(
                "Không thể xóa",
                "Loại phòng có thể đang được sử dụng bởi các phòng hiện có.\n\n"
                + str(e)
            )

        finally:
            if cursor:
                cursor.close()
            connection.close()

    # Xóa nội dung các ô nhập
    def clear_entries(self):
        self.name_entry.delete(0, tk.END)
        self.price_entry.delete(0, tk.END)
        self.capacity_entry.delete(0, tk.END)

    # Xóa trắng biểu mẫu
    def clear_form(self):
        self.selected_id = None
        self.clear_entries()

        for item in self.tree.selection():
            self.tree.selection_remove(item)
