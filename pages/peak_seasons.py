
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

from database import get_connection


class PeakSeasonsPage:
    def __init__(self, parent):
        self.parent = parent

        self.navy = "#101F35"
        self.gold = "#D5AD5B"
        self.white = "#FFFFFF"
        self.background = "#F4F6F9"
        self.gray = "#8793A5"

        self.selected_id = None
        self.room_map = {}

        self.build_ui()
        self.load_rooms()
        self.load_peak_seasons()

    def build_ui(self):
        # Tiêu đề
        tk.Label(
            self.parent,
            text="QUẢN LÝ MÙA CAO ĐIỂM",
            font=("Arial", 24, "bold"),
            fg=self.navy,
            bg=self.background
        ).pack(anchor="w", padx=35, pady=(30, 5))

        tk.Label(
            self.parent,
            text="Quản lý thời gian và hệ số giá phòng trong mùa cao điểm",
            font=("Arial", 11),
            fg=self.gray,
            bg=self.background
        ).pack(anchor="w", padx=35, pady=(0, 20))

        # Thanh tìm kiếm
        search_frame = tk.Frame(
            self.parent,
            bg=self.white,
            highlightbackground="#DDE3EA",
            highlightthickness=1
        )
        search_frame.pack(fill="x", padx=35, pady=(0, 18))

        tk.Label(
            search_frame,
            text="Tìm số phòng:",
            font=("Arial", 10, "bold"),
            bg=self.white,
            fg=self.navy
        ).pack(side="left", padx=(18, 8), pady=15)

        self.search_entry = tk.Entry(
            search_frame,
            font=("Arial", 10),
            width=25
        )
        self.search_entry.pack(side="left", padx=5, pady=12)
        self.search_entry.bind(
            "<KeyRelease>",
            lambda event: self.load_peak_seasons()
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

        # Biểu mẫu
        form_frame = tk.LabelFrame(
            self.parent,
            text=" THÔNG TIN MÙA CAO ĐIỂM ",
            font=("Arial", 12, "bold"),
            bg=self.white,
            fg=self.navy,
            padx=18,
            pady=18
        )
        form_frame.pack(fill="x", padx=35, pady=(0, 18))

        for col in range(4):
            form_frame.columnconfigure(col, weight=1)

        labels = [
            "Phòng",
            "Từ ngày (YYYY-MM-DD)",
            "Đến ngày (YYYY-MM-DD)",
            "Hệ số giá"
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
                sticky="w", padx=8, pady=(0, 8)
            )

        self.room_combo = ttk.Combobox(
            form_frame,
            state="readonly",
            font=("Arial", 10)
        )
        self.room_combo.grid(
            row=1, column=0,
            sticky="ew", padx=8, pady=(0, 16), ipady=4
        )

        self.start_entry = tk.Entry(
            form_frame,
            font=("Arial", 10)
        )
        self.start_entry.grid(
            row=1, column=1,
            sticky="ew", padx=8, pady=(0, 16), ipady=5
        )

        self.end_entry = tk.Entry(
            form_frame,
            font=("Arial", 10)
        )
        self.end_entry.grid(
            row=1, column=2,
            sticky="ew", padx=8, pady=(0, 16), ipady=5
        )

        self.multiplier_entry = tk.Entry(
            form_frame,
            font=("Arial", 10)
        )
        self.multiplier_entry.grid(
            row=1, column=3,
            sticky="ew", padx=8, pady=(0, 16), ipady=5
        )

        # Nút chức năng
        button_frame = tk.Frame(form_frame, bg=self.white)
        button_frame.grid(
            row=2, column=0,
            columnspan=4, sticky="w", padx=8
        )

        tk.Button(
            button_frame,
            text="THÊM MÙA CAO ĐIỂM",
            command=self.add_peak_season,
            bg="#218C65",
            fg=self.white,
            font=("Arial", 10, "bold"),
            relief="flat",
            padx=16,
            pady=10,
            cursor="hand2"
        ).pack(side="left", padx=(0, 10))

        tk.Button(
            button_frame,
            text="CẬP NHẬT",
            command=self.update_peak_season,
            bg=self.navy,
            fg=self.white,
            font=("Arial", 10, "bold"),
            relief="flat",
            padx=18,
            pady=10,
            cursor="hand2"
        ).pack(side="left", padx=10)

        tk.Button(
            button_frame,
            text="XÓA",
            command=self.delete_peak_season,
            bg="#C0392B",
            fg=self.white,
            font=("Arial", 10, "bold"),
            relief="flat",
            padx=25,
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

        # Bảng dữ liệu
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
            text="DANH SÁCH MÙA CAO ĐIỂM",
            font=("Arial", 13, "bold"),
            fg=self.navy,
            bg=self.white
        ).pack(anchor="w", padx=18, pady=12)

        columns = (
            "id", "room", "start", "end", "multiplier"
        )

        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings"
        )

        headings = {
            "id": "Mã",
            "room": "Số phòng",
            "start": "Từ ngày",
            "end": "Đến ngày",
            "multiplier": "Hệ số giá"
        }

        widths = {
            "id": 90,
            "room": 150,
            "start": 200,
            "end": 200,
            "multiplier": 180
        }

        for col in columns:
            self.tree.heading(col, text=headings[col])
            self.tree.column(
                col,
                width=widths[col],
                anchor="center"
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
            padx=(12, 0),
            pady=(0, 15)
        )

        scrollbar.pack(
            side="right",
            fill="y",
            padx=(0, 12),
            pady=(0, 15)
        )

        self.tree.bind(
            "<<TreeviewSelect>>",
            self.select_peak_season
        )

    # Tải danh sách phòng
    def load_rooms(self):
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
                SELECT id, so_phong
                FROM phong
                ORDER BY so_phong
            """)

            self.room_map = {}

            for room_id, room_number in cursor.fetchall():
                display = f"{room_number}"
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

    # Tải danh sách mùa cao điểm
    def load_peak_seasons(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        keyword = self.search_entry.get().strip()

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
                SELECT
                    m.id,
                    p.so_phong,
                    m.tu_ngay,
                    m.den_ngay,
                    m.he_so_gia
                FROM muacaodiem m
                JOIN phong p ON m.phong_id = p.id
                WHERE CAST(p.so_phong AS CHAR) LIKE %s
                ORDER BY m.tu_ngay DESC, m.id DESC
            """, (f"%{keyword}%",))

            for row in cursor.fetchall():
                self.tree.insert(
                    "",
                    "end",
                    values=(
                        row[0],
                        row[1],
                        row[2],
                        row[3],
                        row[4]
                    )
                )

        except Exception as e:
            messagebox.showerror("Lỗi", str(e))

        finally:
            if cursor:
                cursor.close()
            connection.close()

    # Chọn bản ghi trong bảng
    def select_peak_season(self, event):
        selected = self.tree.selection()

        if not selected:
            return

        values = self.tree.item(selected[0], "values")
        self.selected_id = int(values[0])

        self.clear_inputs()

        self.room_combo.set(str(values[1]))
        self.start_entry.insert(0, str(values[2]))
        self.end_entry.insert(0, str(values[3]))
        self.multiplier_entry.insert(0, str(values[4]))

    # Kiểm tra dữ liệu
    def validate_input(self):
        room_display = self.room_combo.get()
        start_date = self.start_entry.get().strip()
        end_date = self.end_entry.get().strip()
        multiplier_text = self.multiplier_entry.get().strip()

        if room_display not in self.room_map:
            messagebox.showwarning(
                "Thiếu thông tin",
                "Vui lòng chọn phòng."
            )
            return None

        try:
            date_start = datetime.strptime(
                start_date, "%Y-%m-%d"
            ).date()

            date_end = datetime.strptime(
                end_date, "%Y-%m-%d"
            ).date()

            if date_end <= date_start:
                messagebox.showwarning(
                    "Ngày không hợp lệ",
                    "Ngày kết thúc phải sau ngày bắt đầu."
                )
                return None

            multiplier = float(multiplier_text)

            if multiplier <= 0:
                raise ValueError

        except ValueError:
            messagebox.showwarning(
                "Dữ liệu không hợp lệ",
                "Ngày phải theo định dạng YYYY-MM-DD "
                "và hệ số giá phải là số lớn hơn 0."
            )
            return None

        room_id = self.room_map[room_display]

        return room_id, start_date, end_date, multiplier

    # Thêm mùa cao điểm
    def add_peak_season(self):
        data = self.validate_input()

        if data is None:
            return

        room_id, start_date, end_date, multiplier = data

        confirm = messagebox.askyesno(
            "Xác nhận",
            "Bạn có muốn thêm thời gian cao điểm này không?"
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

            cursor.execute("""
                INSERT INTO muacaodiem (
                    phong_id,
                    tu_ngay,
                    den_ngay,
                    he_so_gia
                )
                VALUES (%s, %s, %s, %s)
            """, (
                room_id,
                start_date,
                end_date,
                multiplier
            ))

            connection.commit()

            messagebox.showinfo(
                "Thành công",
                "Thêm mùa cao điểm thành công."
            )

            self.clear_form()
            self.load_peak_seasons()

        except Exception as e:
            connection.rollback()
            messagebox.showerror("Lỗi", str(e))

        finally:
            if cursor:
                cursor.close()
            connection.close()

    # Cập nhật mùa cao điểm
    def update_peak_season(self):
        if self.selected_id is None:
            messagebox.showwarning(
                "Chưa chọn dữ liệu",
                "Vui lòng chọn bản ghi cần cập nhật."
            )
            return

        data = self.validate_input()

        if data is None:
            return

        room_id, start_date, end_date, multiplier = data

        connection = get_connection()

        if connection is None:
            messagebox.showerror("Lỗi", "Không thể kết nối MySQL.")
            return

        cursor = None

        try:
            cursor = connection.cursor()

            cursor.execute("""
                UPDATE muacaodiem
                SET phong_id = %s,
                    tu_ngay = %s,
                    den_ngay = %s,
                    he_so_gia = %s
                WHERE id = %s
            """, (
                room_id,
                start_date,
                end_date,
                multiplier,
                self.selected_id
            ))

            connection.commit()

            messagebox.showinfo(
                "Thành công",
                "Cập nhật mùa cao điểm thành công."
            )

            self.clear_form()
            self.load_peak_seasons()

        except Exception as e:
            connection.rollback()
            messagebox.showerror("Lỗi", str(e))

        finally:
            if cursor:
                cursor.close()
            connection.close()

    # Xóa mùa cao điểm
    def delete_peak_season(self):
        if self.selected_id is None:
            messagebox.showwarning(
                "Chưa chọn dữ liệu",
                "Vui lòng chọn bản ghi cần xóa."
            )
            return

        confirm = messagebox.askyesno(
            "Xác nhận xóa",
            "Bạn có chắc chắn muốn xóa bản ghi này không?"
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
                "DELETE FROM muacaodiem WHERE id = %s",
                (self.selected_id,)
            )

            connection.commit()

            messagebox.showinfo(
                "Thành công",
                "Xóa bản ghi thành công."
            )

            self.clear_form()
            self.load_peak_seasons()

        except Exception as e:
            connection.rollback()
            messagebox.showerror("Lỗi", str(e))

        finally:
            if cursor:
                cursor.close()
            connection.close()

    # Xóa nội dung biểu mẫu
    def clear_inputs(self):
        self.room_combo.set("")
        self.start_entry.delete(0, tk.END)
        self.end_entry.delete(0, tk.END)
        self.multiplier_entry.delete(0, tk.END)

    def clear_form(self):
        self.selected_id = None
        self.clear_inputs()

        for item in self.tree.selection():
            self.tree.selection_remove(item)

    # Làm mới trang
    def refresh_page(self):
        self.search_entry.delete(0, tk.END)
        self.clear_form()
        self.load_rooms()
        self.load_peak_seasons()
