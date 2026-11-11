
import tkinter as tk
from tkinter import ttk, messagebox
from database import get_connection


class RoomsPage:
    def __init__(self, parent):
        self.parent = parent
        self.selected_room_id = None
        self.room_type_map = {}

        self.colors = {
            "navy": "#101F35",
            "gold": "#D5AD5B",
            "white": "#FFFFFF",
            "background": "#F4F6F9",
            "text": "#263449",
            "gray": "#8793A5",
            "green": "#218C61",
            "red": "#C0392B"
        }

        self.status_values = [
            "SAN_SANG",
            "DANG_SU_DUNG",
            "BAO_TRI"
        ]

        self.build_ui()
        self.load_room_types()
        self.load_rooms()

    # =====================================
    # BUILD INTERFACE
    # =====================================
    def build_ui(self):
        self.main_frame = tk.Frame(
            self.parent,
            bg=self.colors["background"]
        )
        self.main_frame.pack(fill="both", expand=True)

        # HEADER
        header = tk.Frame(
            self.main_frame,
            bg=self.colors["background"]
        )
        header.pack(fill="x", padx=35, pady=(25, 15))

        tk.Label(
            header,
            text="QUẢN LÝ PHÒNG",
            font=("Arial", 23, "bold"),
            fg=self.colors["navy"],
            bg=self.colors["background"]
        ).pack(anchor="w")

        tk.Label(
            header,
            text="Quản lý danh sách phòng và tình trạng sử dụng",
            font=("Arial", 11),
            fg=self.colors["gray"],
            bg=self.colors["background"]
        ).pack(anchor="w", pady=(5, 0))

        # SEARCH AND FILTER
        search_frame = tk.Frame(
            self.main_frame,
            bg=self.colors["white"],
            highlightbackground="#E1E6ED",
            highlightthickness=1
        )
        search_frame.pack(fill="x", padx=35, pady=10)

        tk.Label(
            search_frame,
            text="Tìm phòng:",
            font=("Arial", 10, "bold"),
            bg=self.colors["white"],
            fg=self.colors["text"]
        ).pack(side="left", padx=(15, 8), pady=15)

        self.search_var = tk.StringVar()

        search_entry = ttk.Entry(
            search_frame,
            textvariable=self.search_var,
            width=25,
            font=("Arial", 10)
        )
        search_entry.pack(side="left", pady=15)
        search_entry.bind("<KeyRelease>", self.search_rooms)

        tk.Label(
            search_frame,
            text="Trạng thái:",
            font=("Arial", 10, "bold"),
            bg=self.colors["white"],
            fg=self.colors["text"]
        ).pack(side="left", padx=(20, 8))

        self.filter_status_var = tk.StringVar(value="Tất cả")

        self.filter_status = ttk.Combobox(
            search_frame,
            textvariable=self.filter_status_var,
            values=["Tất cả"] + self.status_values,
            state="readonly",
            width=18
        )
        self.filter_status.pack(side="left", pady=15)
        self.filter_status.bind(
            "<<ComboboxSelected>>",
            self.search_rooms
        )

        tk.Button(
            search_frame,
            text="LÀM MỚI",
            command=self.reset_search,
            bg=self.colors["navy"],
            fg="white",
            font=("Arial", 9, "bold"),
            relief="flat",
            padx=15,
            pady=8,
            cursor="hand2"
        ).pack(side="left", padx=15)

        # ROOM FORM
        form = tk.LabelFrame(
            self.main_frame,
            text="THÔNG TIN PHÒNG",
            font=("Arial", 11, "bold"),
            fg=self.colors["navy"],
            bg=self.colors["white"],
            padx=15,
            pady=12
        )
        form.pack(fill="x", padx=35, pady=10)

        self.room_number_var = tk.StringVar()
        self.room_type_var = tk.StringVar()
        self.status_var = tk.StringVar(value="SAN_SANG")

        # Room number
        tk.Label(
            form,
            text="Số phòng",
            font=("Arial", 10, "bold"),
            bg=self.colors["white"],
            fg=self.colors["text"]
        ).grid(row=0, column=0, sticky="w", padx=10, pady=5)

        ttk.Entry(
            form,
            textvariable=self.room_number_var,
            font=("Arial", 10),
            width=25
        ).grid(row=1, column=0, sticky="ew", padx=10, pady=5)

        # Room type
        tk.Label(
            form,
            text="Loại phòng",
            font=("Arial", 10, "bold"),
            bg=self.colors["white"],
            fg=self.colors["text"]
        ).grid(row=0, column=1, sticky="w", padx=10, pady=5)

        self.room_type_combo = ttk.Combobox(
            form,
            textvariable=self.room_type_var,
            state="readonly",
            width=25,
            font=("Arial", 10)
        )
        self.room_type_combo.grid(
            row=1, column=1, sticky="ew",
            padx=10, pady=5
        )

        # Status
        tk.Label(
            form,
            text="Trạng thái",
            font=("Arial", 10, "bold"),
            bg=self.colors["white"],
            fg=self.colors["text"]
        ).grid(row=0, column=2, sticky="w", padx=10, pady=5)

        self.status_combo = ttk.Combobox(
            form,
            textvariable=self.status_var,
            values=self.status_values,
            state="readonly",
            width=25,
            font=("Arial", 10)
        )
        self.status_combo.grid(
            row=1, column=2, sticky="ew",
            padx=10, pady=5
        )

        for i in range(3):
            form.grid_columnconfigure(i, weight=1)

        # BUTTONS
        button_frame = tk.Frame(
            form,
            bg=self.colors["white"]
        )
        button_frame.grid(
            row=2, column=0, columnspan=3,
            sticky="w", padx=10, pady=12
        )

        self.create_button(
            button_frame, "THÊM PHÒNG",
            self.add_room, self.colors["green"]
        )

        self.create_button(
            button_frame, "CẬP NHẬT",
            self.update_room, self.colors["navy"]
        )

        self.create_button(
            button_frame, "XÓA PHÒNG",
            self.delete_room, self.colors["red"]
        )

        self.create_button(
            button_frame, "XÓA TRẮNG",
            self.clear_form, self.colors["gray"]
        )

        # ROOM TABLE
        table_frame = tk.Frame(
            self.main_frame,
            bg=self.colors["white"],
            highlightbackground="#E1E6ED",
            highlightthickness=1
        )
        table_frame.pack(
            fill="both", expand=True,
            padx=35, pady=(10, 25)
        )

        tk.Label(
            table_frame,
            text="DANH SÁCH PHÒNG",
            font=("Arial", 12, "bold"),
            fg=self.colors["navy"],
            bg=self.colors["white"]
        ).pack(anchor="w", padx=15, pady=12)

        columns = (
            "id",
            "so_phong",
            "loai_phong",
            "gia",
            "suc_chua",
            "trang_thai",
            "loai_phong_id"
        )

        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            height=12
        )

        headings = {
            "id": "Mã phòng",
            "so_phong": "Số phòng",
            "loai_phong": "Loại phòng",
            "gia": "Giá cơ bản",
            "suc_chua": "Sức chứa",
            "trang_thai": "Trạng thái",
            "loai_phong_id": ""
        }

        for column, title in headings.items():
            self.tree.heading(column, text=title)

        self.tree.column("id", width=80, anchor="center")
        self.tree.column("so_phong", width=110, anchor="center")
        self.tree.column("loai_phong", width=180, anchor="center")
        self.tree.column("gia", width=150, anchor="center")
        self.tree.column("suc_chua", width=100, anchor="center")
        self.tree.column("trang_thai", width=180, anchor="center")
        self.tree.column(
            "loai_phong_id",
            width=0,
            stretch=False
        )

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
            self.select_room
        )

        style = ttk.Style()
        style.configure(
            "Treeview",
            rowheight=32,
            font=("Arial", 10)
        )
        style.configure(
            "Treeview.Heading",
            font=("Arial", 10, "bold")
        )

    # =====================================
    # BUTTON
    # =====================================
    def create_button(self, parent, text, command, color):
        tk.Button(
            parent,
            text=text,
            command=command,
            bg=color,
            fg="white",
            font=("Arial", 9, "bold"),
            relief="flat",
            padx=15,
            pady=9,
            cursor="hand2"
        ).pack(side="left", padx=(0, 10))

    # =====================================
    # LOAD ROOM TYPES
    # =====================================
    def load_room_types(self):
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
                SELECT id, ten
                FROM loaiphong
                ORDER BY id
            """)

            rows = cursor.fetchall()

            self.room_type_map = {
                f"{row[0]} - {row[1]}": row[0]
                for row in rows
            }

            self.room_type_combo["values"] = list(
                self.room_type_map.keys()
            )

        except Exception as e:
            messagebox.showerror("Lỗi", str(e))

        finally:
            if cursor:
                cursor.close()
            connection.close()

    # =====================================
    # LOAD ROOMS
    # =====================================
    def load_rooms(self, keyword=None, status="Tất cả"):
        for item in self.tree.get_children():
            self.tree.delete(item)

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
                    p.id,
                    p.so_phong,
                    lp.ten,
                    lp.gia_co_ban,
                    lp.suc_chua,
                    p.trang_thai,
                    p.loai_phong_id
                FROM phong p
                JOIN loaiphong lp
                    ON p.loai_phong_id = lp.id
                WHERE 1 = 1
            """

            params = []

            if keyword:
                sql += """
                    AND (
                        p.so_phong LIKE %s
                        OR lp.ten LIKE %s
                    )
                """
                params.extend([
                    f"%{keyword}%",
                    f"%{keyword}%"
                ])

            if status != "Tất cả":
                sql += " AND p.trang_thai = %s"
                params.append(status)

            sql += " ORDER BY p.so_phong"

            cursor.execute(sql, tuple(params))

            for row in cursor.fetchall():
                room_id, room_number, room_type, price, capacity, room_status, type_id = row

                self.tree.insert(
                    "",
                    "end",
                    values=(
                        room_id,
                        room_number,
                        room_type,
                        f"{float(price):,.0f} đ",
                        capacity,
                        room_status,
                        type_id
                    )
                )

        except Exception as e:
            messagebox.showerror("Lỗi tải danh sách phòng", str(e))

        finally:
            if cursor:
                cursor.close()
            connection.close()

    # =====================================
    # SEARCH AND FILTER
    # =====================================
    def search_rooms(self, event=None):
        keyword = self.search_var.get().strip()
        status = self.filter_status_var.get()

        self.load_rooms(
            keyword if keyword else None,
            status
        )

    def reset_search(self):
        self.search_var.set("")
        self.filter_status_var.set("Tất cả")
        self.load_rooms()

    # =====================================
    # SELECT ROOM
    # =====================================
    def select_room(self, event=None):
        selected = self.tree.selection()

        if not selected:
            return

        values = self.tree.item(selected[0], "values")

        self.selected_room_id = values[0]
        self.room_number_var.set(values[1])

        type_id = int(values[6])

        for display, room_type_id in self.room_type_map.items():
            if room_type_id == type_id:
                self.room_type_var.set(display)
                break

        self.status_var.set(values[5])

    # =====================================
    # VALIDATE
    # =====================================
    def validate_form(self):
        room_number = self.room_number_var.get().strip()
        room_type = self.room_type_var.get().strip()
        status = self.status_var.get().strip()

        if not room_number or not room_type or not status:
            messagebox.showwarning(
                "Thiếu thông tin",
                "Vui lòng nhập đầy đủ thông tin phòng."
            )
            return None

        if room_type not in self.room_type_map:
            messagebox.showwarning(
                "Loại phòng không hợp lệ",
                "Vui lòng chọn loại phòng trong danh sách."
            )
            return None

        return (
            room_number,
            self.room_type_map[room_type],
            status
        )

    # =====================================
    # ADD ROOM
    # =====================================
    def add_room(self):
        data = self.validate_form()

        if data is None:
            return

        connection = get_connection()

        if connection is None:
            messagebox.showerror("Lỗi", "Không thể kết nối MySQL.")
            return

        cursor = None

        try:
            cursor = connection.cursor()

            cursor.execute("""
                INSERT INTO phong (
                    so_phong,
                    loai_phong_id,
                    trang_thai
                )
                VALUES (%s, %s, %s)
            """, data)

            connection.commit()

            messagebox.showinfo(
                "Thành công",
                "Đã thêm phòng mới."
            )

            self.clear_form()
            self.load_rooms()

        except Exception as e:
            connection.rollback()
            messagebox.showerror(
                "Không thể thêm phòng",
                "Số phòng có thể đã tồn tại hoặc dữ liệu không hợp lệ.\n\n"
                + str(e)
            )

        finally:
            if cursor:
                cursor.close()
            connection.close()

    # =====================================
    # UPDATE ROOM
    # =====================================
    def update_room(self):
        if self.selected_room_id is None:
            messagebox.showwarning(
                "Chưa chọn phòng",
                "Vui lòng chọn phòng cần cập nhật."
            )
            return

        data = self.validate_form()

        if data is None:
            return

        connection = get_connection()

        if connection is None:
            messagebox.showerror("Lỗi", "Không thể kết nối MySQL.")
            return

        cursor = None

        try:
            cursor = connection.cursor()

            cursor.execute("""
                UPDATE phong
                SET so_phong = %s,
                    loai_phong_id = %s,
                    trang_thai = %s
                WHERE id = %s
            """, (*data, self.selected_room_id))

            connection.commit()

            messagebox.showinfo(
                "Thành công",
                "Đã cập nhật thông tin phòng."
            )

            self.clear_form()
            self.load_rooms()

        except Exception as e:
            connection.rollback()
            messagebox.showerror(
                "Lỗi cập nhật",
                "Không thể cập nhật phòng.\n\n" + str(e)
            )

        finally:
            if cursor:
                cursor.close()
            connection.close()

    # =====================================
    # DELETE ROOM
    # =====================================
    def delete_room(self):
        if self.selected_room_id is None:
            messagebox.showwarning(
                "Chưa chọn phòng",
                "Vui lòng chọn phòng cần xóa."
            )
            return

        confirm = messagebox.askyesno(
            "Xác nhận xóa",
            "Bạn có chắc chắn muốn xóa phòng này không?"
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
                "DELETE FROM phong WHERE id = %s",
                (self.selected_room_id,)
            )

            connection.commit()

            messagebox.showinfo(
                "Thành công",
                "Đã xóa phòng."
            )

            self.clear_form()
            self.load_rooms()

        except Exception as e:
            connection.rollback()
            messagebox.showerror(
                "Không thể xóa phòng",
                "Phòng có thể đang được liên kết với booking hoặc dữ liệu khác.\n"
                "Hãy kiểm tra các dữ liệu liên quan trước khi xóa.\n\n"
                + str(e)
            )

        finally:
            if cursor:
                cursor.close()
            connection.close()

    # =====================================
    # CLEAR FORM
    # =====================================
    def clear_form(self):
        self.selected_room_id = None
        self.room_number_var.set("")
        self.room_type_var.set("")
        self.status_var.set("SAN_SANG")

        self.tree.selection_remove(
            self.tree.selection()
        )
