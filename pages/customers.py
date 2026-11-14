
import tkinter as tk
from tkinter import ttk, messagebox

import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


# Địa chỉ API FastAPI
API_BASE_URL = "http://127.0.0.1:8000/api/customers"


class CustomersPage:
    def __init__(self, parent):
        self.parent = parent
        self.selected_customer_id = None
        self.all_customers = []

        self.colors = {
            "navy": "#101F35",
            "gold": "#D5AD5B",
            "white": "#FFFFFF",
            "background": "#F4F6F9",
            "text": "#263449",
            "gray": "#8793A5",
            "red": "#C0392B",
            "green": "#218C61"
        }

        self.build_ui()
        self.load_customers()

    # =====================================================
    # API REQUEST
    # =====================================================

    def api_request(self, method, endpoint="", data=None):
        url = API_BASE_URL + endpoint

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        body = None

        if data is not None:
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")

        request = Request(
            url=url,
            data=body,
            headers=headers,
            method=method
        )

        try:
            with urlopen(request, timeout=10) as response:
                response_body = response.read().decode("utf-8")

                if not response_body:
                    return {}

                return json.loads(response_body)

        except HTTPError as e:
            error_body = e.read().decode("utf-8")

            try:
                error_data = json.loads(error_body)
                detail = error_data.get("detail", error_body)
            except (json.JSONDecodeError, AttributeError):
                detail = error_body

            raise Exception(f"HTTP {e.code}: {detail}")

        except URLError as e:
            raise Exception(
                "Không thể kết nối FastAPI.\n"
                "Hãy kiểm tra server FastAPI đã chạy chưa.\n\n"
                f"Chi tiết: {e.reason}"
            )

        except json.JSONDecodeError:
            raise Exception("API trả về dữ liệu JSON không hợp lệ.")

    # =====================================================
    # EXTRACT CUSTOMER DATA
    # =====================================================

    def extract_customers(self, response):
        # Trường hợp API trả về danh sách trực tiếp
        if isinstance(response, list):
            return response

        if isinstance(response, dict):

            # Các tên trường có thể chứa danh sách khách hàng
            possible_keys = [
                "data",
                "customers",
                "khach",
                "khach_hang",
                "items",
                "results"
            ]

            for key in possible_keys:
                value = response.get(key)

                if isinstance(value, list):
                    return value

                if isinstance(value, dict):
                    nested = self.extract_customers(value)

                    if nested:
                        return nested

        raise Exception(
            "Không xác định được danh sách khách hàng "
            "từ dữ liệu API trả về."
        )

    # =====================================================
    # BUILD UI
    # =====================================================

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
            text="QUẢN LÝ KHÁCH HÀNG",
            font=("Arial", 23, "bold"),
            fg=self.colors["navy"],
            bg=self.colors["background"]
        ).pack(anchor="w")

        tk.Label(
            header,
            text="Quản lý thông tin và hồ sơ khách lưu trú",
            font=("Arial", 11),
            fg=self.colors["gray"],
            bg=self.colors["background"]
        ).pack(anchor="w", pady=(5, 0))

        # SEARCH BAR
        search_frame = tk.Frame(
            self.main_frame,
            bg=self.colors["white"],
            highlightbackground="#E1E6ED",
            highlightthickness=1
        )
        search_frame.pack(fill="x", padx=35, pady=10)

        tk.Label(
            search_frame,
            text="Tìm kiếm:",
            font=("Arial", 11, "bold"),
            bg=self.colors["white"],
            fg=self.colors["text"]
        ).pack(side="left", padx=(15, 8), pady=15)

        self.search_var = tk.StringVar()

        search_entry = ttk.Entry(
            search_frame,
            textvariable=self.search_var,
            width=35,
            font=("Arial", 11)
        )
        search_entry.pack(side="left", pady=15)
        search_entry.bind("<KeyRelease>", self.search_customers)

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
        ).pack(side="left", padx=10)

        # CUSTOMER FORM
        form = tk.LabelFrame(
            self.main_frame,
            text="THÔNG TIN KHÁCH HÀNG",
            font=("Arial", 11, "bold"),
            fg=self.colors["navy"],
            bg=self.colors["white"],
            padx=15,
            pady=12
        )
        form.pack(fill="x", padx=35, pady=10)

        self.name_var = tk.StringVar()
        self.cccd_var = tk.StringVar()
        self.phone_var = tk.StringVar()

        fields = [
            ("Họ và tên", self.name_var),
            ("CCCD", self.cccd_var),
            ("Số điện thoại", self.phone_var)
        ]

        for index, (label_text, variable) in enumerate(fields):
            tk.Label(
                form,
                text=label_text,
                font=("Arial", 10, "bold"),
                bg=self.colors["white"],
                fg=self.colors["text"]
            ).grid(
                row=0,
                column=index,
                sticky="w",
                padx=10,
                pady=(5, 5)
            )

            ttk.Entry(
                form,
                textvariable=variable,
                font=("Arial", 11),
                width=30
            ).grid(
                row=1,
                column=index,
                sticky="ew",
                padx=10,
                pady=(0, 10)
            )

            form.grid_columnconfigure(index, weight=1)

        # BUTTONS
        button_frame = tk.Frame(
            form,
            bg=self.colors["white"]
        )
        button_frame.grid(
            row=2,
            column=0,
            columnspan=3,
            sticky="w",
            padx=10,
            pady=5
        )

        self.create_button(
            button_frame,
            "THÊM KHÁCH HÀNG",
            self.add_customer,
            self.colors["green"]
        )

        self.create_button(
            button_frame,
            "CẬP NHẬT",
            self.update_customer,
            self.colors["navy"]
        )

        self.create_button(
            button_frame,
            "XÓA",
            self.delete_customer,
            self.colors["red"]
        )

        self.create_button(
            button_frame,
            "XÓA TRẮNG",
            self.clear_form,
            "#8793A5"
        )

        # CUSTOMER TABLE
        table_frame = tk.Frame(
            self.main_frame,
            bg=self.colors["white"],
            highlightbackground="#E1E6ED",
            highlightthickness=1
        )
        table_frame.pack(
            fill="both",
            expand=True,
            padx=35,
            pady=(10, 25)
        )

        tk.Label(
            table_frame,
            text="DANH SÁCH KHÁCH HÀNG",
            font=("Arial", 12, "bold"),
            fg=self.colors["navy"],
            bg=self.colors["white"]
        ).pack(anchor="w", padx=15, pady=12)

        columns = ("id", "ho_ten", "cccd", "sdt")

        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            height=12
        )

        self.tree.heading("id", text="Mã khách hàng")
        self.tree.heading("ho_ten", text="Họ và tên")
        self.tree.heading("cccd", text="CCCD")
        self.tree.heading("sdt", text="Số điện thoại")

        self.tree.column("id", width=130, anchor="center")
        self.tree.column("ho_ten", width=280, anchor="w")
        self.tree.column("cccd", width=220, anchor="center")
        self.tree.column("sdt", width=200, anchor="center")

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
            self.select_customer
        )

        # TABLE STYLE
        style = ttk.Style()

        style.configure(
            "Treeview",
            rowheight=32,
            font=("Arial", 10)
        )

        style.configure(
            "Treeview.Heading",
            font=("Arial", 10, "bold"),
            background="#E9EDF3",
            foreground=self.colors["navy"]
        )

    # =====================================================
    # CREATE BUTTON
    # =====================================================

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

    # =====================================================
    # LOAD CUSTOMERS FROM API
    # =====================================================

    def load_customers(self, keyword=None, refresh=True):
        try:
            if refresh:
                response = self.api_request("GET", "/")
                self.all_customers = self.extract_customers(response)

            customers = self.all_customers

            # Tìm kiếm trên dữ liệu đã tải
            if keyword:
                keyword = keyword.lower().strip()

                customers = [
                    customer for customer in customers
                    if keyword in str(customer.get("ho_ten", "")).lower()
                    or keyword in str(customer.get("cccd", "")).lower()
                    or keyword in str(customer.get("sdt", "")).lower()
                    or keyword in str(customer.get("id", "")).lower()
                ]

            # Xóa dữ liệu cũ trên bảng
            for item in self.tree.get_children():
                self.tree.delete(item)

            # Đưa dữ liệu API vào Treeview
            for customer in customers:
                self.tree.insert(
                    "",
                    "end",
                    values=(
                        customer.get("id", ""),
                        customer.get("ho_ten", ""),
                        customer.get("cccd", ""),
                        customer.get("sdt", "")
                    )
                )

        except Exception as e:
            messagebox.showerror(
                "Lỗi tải khách hàng",
                str(e)
            )

    # =====================================================
    # SEARCH
    # =====================================================

    def search_customers(self, event=None):
        keyword = self.search_var.get().strip()

        self.load_customers(
            keyword if keyword else None,
            refresh=False
        )

    def reset_search(self):
        self.search_var.set("")
        self.load_customers()

    # =====================================================
    # SELECT CUSTOMER
    # =====================================================

    def select_customer(self, event=None):
        selected = self.tree.selection()

        if not selected:
            return

        values = self.tree.item(selected[0], "values")

        self.selected_customer_id = values[0]

        self.name_var.set(values[1])
        self.cccd_var.set(values[2])
        self.phone_var.set(values[3])

    # =====================================================
    # VALIDATE FORM
    # =====================================================

    def validate_form(self):
        name = self.name_var.get().strip()
        cccd = self.cccd_var.get().strip()
        phone = self.phone_var.get().strip()

        if not name or not cccd or not phone:
            messagebox.showwarning(
                "Thiếu thông tin",
                "Vui lòng nhập đầy đủ họ tên, CCCD và số điện thoại."
            )
            return None

        return {
            "ho_ten": name,
            "cccd": cccd,
            "sdt": phone
        }

    # =====================================================
    # ADD CUSTOMER
    # =====================================================

    def add_customer(self):
        data = self.validate_form()

        if data is None:
            return

        try:
            self.api_request(
                "POST",
                "/",
                data
            )

            messagebox.showinfo(
                "Thành công",
                "Đã thêm khách hàng mới."
            )

            self.clear_form()
            self.load_customers()

        except Exception as e:
            messagebox.showerror(
                "Không thể thêm khách hàng",
                str(e)
            )

    # =====================================================
    # UPDATE CUSTOMER
    # =====================================================

    def update_customer(self):
        if self.selected_customer_id is None:
            messagebox.showwarning(
                "Chưa chọn khách hàng",
                "Vui lòng chọn khách hàng cần cập nhật trong bảng."
            )
            return

        data = self.validate_form()

        if data is None:
            return

        try:
            self.api_request(
                "PUT",
                f"/{self.selected_customer_id}",
                data
            )

            messagebox.showinfo(
                "Thành công",
                "Đã cập nhật thông tin khách hàng."
            )

            self.clear_form()
            self.load_customers()

        except Exception as e:
            messagebox.showerror(
                "Lỗi cập nhật",
                str(e)
            )

    # =====================================================
    # DELETE CUSTOMER
    # =====================================================

    def delete_customer(self):
        if self.selected_customer_id is None:
            messagebox.showwarning(
                "Chưa chọn khách hàng",
                "Vui lòng chọn khách hàng cần xóa."
            )
            return

        confirm = messagebox.askyesno(
            "Xác nhận xóa",
            "Bạn có chắc chắn muốn xóa khách hàng này không?"
        )

        if not confirm:
            return

        try:
            self.api_request(
                "DELETE",
                f"/{self.selected_customer_id}"
            )

            messagebox.showinfo(
                "Thành công",
                "Đã xóa khách hàng."
            )

            self.clear_form()
            self.load_customers()

        except Exception as e:
            messagebox.showerror(
                "Không thể xóa",
                "Khách hàng có thể đang được liên kết với booking "
                "hoặc không thể xóa.\n\n"
                + str(e)
            )

    # =====================================================
    # CLEAR FORM
    # =====================================================

    def clear_form(self):
        self.selected_customer_id = None

        self.name_var.set("")
        self.cccd_var.set("")
        self.phone_var.set("")

        self.tree.selection_remove(
            self.tree.selection()
        )
