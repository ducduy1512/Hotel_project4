
import tkinter as tk
from tkinter import ttk, messagebox

from database import get_connection


class ServicesPage:
    def __init__(self, parent):
        self.parent = parent

        self.navy = "#101F35"
        self.gold = "#D5AD5B"
        self.white = "#FFFFFF"
        self.background = "#F4F6F9"
        self.gray = "#8793A5"

        self.selected_id = None
        self.booking_map = {}

        self.build_ui()
        self.load_bookings()
        self.load_services()

    def build_ui(self):
        # Tiêu đề
        tk.Label(
            self.parent,
            text="QUẢN LÝ DỊCH VỤ",
            font=("Arial", 24, "bold"),
            fg=self.navy,
            bg=self.background
        ).pack(anchor="w", padx=35, pady=(30, 5))

        tk.Label(
            self.parent,
            text="Quản lý dịch vụ sử dụng trong từng lượt đặt phòng",
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
            text="Tìm dịch vụ:",
            font=("Arial", 10, "bold"),
            bg=self.white,
            fg=self.navy
        ).pack(side="left", padx=(18, 8), pady=15)

        self.search_entry = tk.Entry(
            search_frame,
            font=("Arial", 10),
            width=28
        )
        self.search_entry.pack(side="left", padx=5, pady=12)
        self.search_entry.bind(
            "<KeyRelease>",
            lambda event: self.load_services()
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

        # Biểu mẫu thông tin dịch vụ
        form_frame = tk.LabelFrame(
            self.parent,
            text=" THÔNG TIN DỊCH VỤ ",
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
            "Tên dịch vụ",
            "Đơn giá (VNĐ)",
            "Số lượng",
            "Booking liên quan"
        ]

        for col, label in enumerate(labels):
            tk.Label(
                form_frame,
                text=label,
                font=("Arial", 9, "bold"),
                bg=self.white,
                fg=self.navy
            ).grid(
                row=0,
                column=col,
                sticky="w",
                padx=8,
                pady=(0, 8)
            )

        self.name_entry = tk.Entry(
            form_frame,
            font=("Arial", 10)
        )
        self.name_entry.grid(
            row=1, column=0,
            sticky="ew", padx=8, pady=(0, 16), ipady=5
        )

        self.price_entry = tk.Entry(
            form_frame,
            font=("Arial", 10)
        )
        self.price_entry.grid(
            row=1, column=1,
            sticky="ew", padx=8, pady=(0, 16), ipady=5
        )

        self.quantity_entry = tk.Entry(
            form_frame,
            font=("Arial", 10)
        )
        self.quantity_entry.grid(
            row=1, column=2,
            sticky="ew", padx=8, pady=(0, 16), ipady=5
        )

        self.booking_combo = ttk.Combobox(
            form_frame,
            state="readonly",
            font=("Arial", 9)
        )
        self.booking_combo.grid(
            row=1, column=3,
            sticky="ew", padx=8, pady=(0, 16), ipady=5
        )

        # Các nút chức năng
        button_frame = tk.Frame(form_frame, bg=self.white)
        button_frame.grid(
            row=2, column=0,
            columnspan=4, sticky="w", padx=8
        )

        tk.Button(
            button_frame,
            text="THÊM DỊCH VỤ",
            command=self.add_service,
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
            text="CẬP NHẬT",
            command=self.update_service,
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
            text="XÓA DỊCH VỤ",
            command=self.delete_service,
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

        # Danh sách dịch vụ
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
            text="DANH SÁCH DỊCH VỤ",
            font=("Arial", 13, "bold"),
            fg=self.navy,
            bg=self.white
        ).pack(anchor="w", padx=18, pady=12)

        columns = (
            "id", "name", "price",
            "quantity", "booking", "total"
        )

        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings"
        )

        headings = {
            "id": "Mã dịch vụ",
            "name": "Tên dịch vụ",
            "price": "Đơn giá",
            "quantity": "Số lượng",
            "booking": "Mã booking",
            "total": "Thành tiền"
        }

        widths = {
            "id": 90,
            "name": 200,
            "price": 150,
            "quantity": 100,
            "booking": 120,
            "total": 170
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

        self.tree.configure(
            yscrollcommand=scrollbar_y.set
        )

        self.tree.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(12, 0),
            pady=(0, 15)
        )

        scrollbar_y.pack(
            side="right",
            fill="y",
            padx=(0, 12),
            pady=(0, 15)
        )

        self.tree.bind(
            "<<TreeviewSelect>>",
            self.select_service
        )

    # Tải danh sách booking vào Combobox
    def load_bookings(self):
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
                    b.id,
                    k.ho_ten,
                    p.so_phong
                FROM booking b
                JOIN khach k ON b.khach_id = k.id
                JOIN phong p ON b.phong_id = p.id
                ORDER BY b.id DESC
            """)

            self.booking_map = {}

            for booking_id, customer_name, room_number in cursor.fetchall():
                display = (
                    f"Booking {booking_id} - "
                    f"{customer_name} - Phòng {room_number}"
                )

                self.booking_map[display] = booking_id

            self.booking_combo["values"] = list(
                self.booking_map.keys()
            )

        except Exception as e:
            messagebox.showerror("Lỗi", str(e))

        finally:
            if cursor:
                cursor.close()
            connection.close()

    # Tải danh sách dịch vụ
    def load_services(self):
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
                    id,
                    ten,
                    don_gia,
                    so_luong,
                    booking_id
                FROM dichvu
                WHERE ten LIKE %s
                ORDER BY id DESC
            """, (f"%{keyword}%",))

            for row in cursor.fetchall():
                service_id, name, price, quantity, booking_id = row

                total = float(price) * int(quantity)

                self.tree.insert(
                    "",
                    "end",
                    values=(
                        service_id,
                        name,
                        f"{float(price):,.0f} đ",
                        quantity,
                        booking_id,
                        f"{total:,.0f} đ"
                    )
                )

        except Exception as e:
            messagebox.showerror("Lỗi", str(e))

        finally:
            if cursor:
                cursor.close()
            connection.close()

    # Chọn dịch vụ trong bảng
    def select_service(self, event):
        selected = self.tree.selection()

        if not selected:
            return

        values = self.tree.item(selected[0], "values")

        self.selected_id = int(values[0])

        self.clear_inputs()

        self.name_entry.insert(0, values[1])
        self.quantity_entry.insert(0, str(values[3]))

        # Lấy đơn giá gốc từ database
        connection = get_connection()

        if connection is None:
            messagebox.showerror("Lỗi", "Không thể kết nối MySQL.")
            return

        cursor = None

        try:
            cursor = connection.cursor()

            cursor.execute("""
                SELECT don_gia, booking_id
                FROM dichvu
                WHERE id = %s
            """, (self.selected_id,))

            result = cursor.fetchone()

            if result:
                self.price_entry.insert(0, str(result[0]))

                booking_id = result[1]

                for display, current_id in self.booking_map.items():
                    if current_id == booking_id:
                        self.booking_combo.set(display)
                        break

        except Exception as e:
            messagebox.showerror("Lỗi", str(e))

        finally:
            if cursor:
                cursor.close()
            connection.close()

    # Kiểm tra dữ liệu đầu vào
    def validate_input(self):
        name = self.name_entry.get().strip()
        price_text = self.price_entry.get().strip()
        quantity_text = self.quantity_entry.get().strip()
        booking_display = self.booking_combo.get()

        if not name or not price_text or not quantity_text:
            messagebox.showwarning(
                "Thiếu thông tin",
                "Vui lòng nhập đầy đủ tên dịch vụ, đơn giá và số lượng."
            )
            return None

        if booking_display not in self.booking_map:
            messagebox.showwarning(
                "Thiếu thông tin",
                "Vui lòng chọn booking liên quan."
            )
            return None

        try:
            price = float(price_text)
            quantity = int(quantity_text)

            if price <= 0 or quantity <= 0:
                raise ValueError

        except ValueError:
            messagebox.showwarning(
                "Dữ liệu không hợp lệ",
                "Đơn giá và số lượng phải là số dương hợp lệ."
            )
            return None

        booking_id = self.booking_map[booking_display]

        return name, price, quantity, booking_id

    # Thêm dịch vụ
    def add_service(self):
        data = self.validate_input()

        if data is None:
            return

        name, price, quantity, booking_id = data

        confirm = messagebox.askyesno(
            "Xác nhận",
            "Bạn có muốn thêm dịch vụ này không?"
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
                INSERT INTO dichvu (
                    ten,
                    don_gia,
                    so_luong,
                    booking_id
                )
                VALUES (%s, %s, %s, %s)
            """, (
                name,
                price,
                quantity,
                booking_id
            ))

            connection.commit()

            messagebox.showinfo(
                "Thành công",
                "Thêm dịch vụ thành công."
            )

            self.clear_form()
            self.load_services()

        except Exception as e:
            connection.rollback()
            messagebox.showerror("Lỗi", str(e))

        finally:
            if cursor:
                cursor.close()
            connection.close()

    # Cập nhật dịch vụ
    def update_service(self):
        if self.selected_id is None:
            messagebox.showwarning(
                "Chưa chọn dịch vụ",
                "Vui lòng chọn dịch vụ cần cập nhật."
            )
            return

        data = self.validate_input()

        if data is None:
            return

        name, price, quantity, booking_id = data

        connection = get_connection()

        if connection is None:
            messagebox.showerror("Lỗi", "Không thể kết nối MySQL.")
            return

        cursor = None

        try:
            cursor = connection.cursor()

            cursor.execute("""
                UPDATE dichvu
                SET ten = %s,
                    don_gia = %s,
                    so_luong = %s,
                    booking_id = %s
                WHERE id = %s
            """, (
                name,
                price,
                quantity,
                booking_id,
                self.selected_id
            ))

            connection.commit()

            messagebox.showinfo(
                "Thành công",
                "Cập nhật dịch vụ thành công."
            )

            self.clear_form()
            self.load_services()

        except Exception as e:
            connection.rollback()
            messagebox.showerror("Lỗi", str(e))

        finally:
            if cursor:
                cursor.close()
            connection.close()

    # Xóa dịch vụ
    def delete_service(self):
        if self.selected_id is None:
            messagebox.showwarning(
                "Chưa chọn dịch vụ",
                "Vui lòng chọn dịch vụ cần xóa."
            )
            return

        confirm = messagebox.askyesno(
            "Xác nhận xóa",
            "Bạn có chắc chắn muốn xóa dịch vụ này không?"
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
                "DELETE FROM dichvu WHERE id = %s",
                (self.selected_id,)
            )

            connection.commit()

            messagebox.showinfo(
                "Thành công",
                "Xóa dịch vụ thành công."
            )

            self.clear_form()
            self.load_services()

        except Exception as e:
            connection.rollback()
            messagebox.showerror("Lỗi", str(e))

        finally:
            if cursor:
                cursor.close()
            connection.close()

    # Xóa nội dung biểu mẫu
    def clear_inputs(self):
        self.name_entry.delete(0, tk.END)
        self.price_entry.delete(0, tk.END)
        self.quantity_entry.delete(0, tk.END)
        self.booking_combo.set("")

    def clear_form(self):
        self.selected_id = None
        self.clear_inputs()

        for item in self.tree.selection():
            self.tree.selection_remove(item)

    # Làm mới trang
    def refresh_page(self):
        self.search_entry.delete(0, tk.END)
        self.clear_form()
        self.load_bookings()
        self.load_services()
