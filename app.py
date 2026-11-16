import json
import os
import tkinter as tk
from tkinter import ttk, messagebox

from api_client import api_client, APIError

# Import các trang chức năng
from pages.dashboard import DashboardPage
from pages.customers import CustomersPage
from pages.room_types import RoomTypesPage
from pages.rooms import RoomsPage
from pages.bookings import BookingsPage
from pages.peak_seasons import PeakSeasonsPage
from pages.services import ServicesPage
from pages.payments import PaymentsPage
from pages.invoices import InvoicesPage
from pages.reports import ReportsPage


class HotelManagementApp:

    def __init__(self, root):
        self.root = root

        self.root.title("HOTEL MANAGEMENT SYSTEM")
        self.root.geometry("1250x780")
        self.root.minsize(1050, 650)
        self.root.configure(bg="#F3F4F6")

        self.current_page = None
        self.current_page_name = None
        self.current_user = None

        self.nav_buttons = {}

        # Danh sách các trang
        self.pages = {
            "dashboard": {
                "title": "Tổng quan",
                "icon": "⌂",
                "class": DashboardPage
            },
            "customers": {
                "title": "Quản lý khách hàng",
                "icon": "♙",
                "class": CustomersPage
            },
            "room_types": {
                "title": "Quản lý loại phòng",
                "icon": "▦",
                "class": RoomTypesPage
            },
            "rooms": {
                "title": "Quản lý phòng",
                "icon": "▣",
                "class": RoomsPage
            },
            "bookings": {
                "title": "Quản lý booking",
                "icon": "▤",
                "class": BookingsPage
            },
            "peak_seasons": {
                "title": "Mùa cao điểm",
                "icon": "◷",
                "class": PeakSeasonsPage
            },
            "services": {
                "title": "Quản lý dịch vụ",
                "icon": "✧",
                "class": ServicesPage
            },
            "payments": {
                "title": "Quản lý thanh toán",
                "icon": "₫",
                "class": PaymentsPage
            },
            "invoices": {
                "title": "Quản lý hóa đơn",
                "icon": "▧",
                "class": InvoicesPage
            },
            "reports": {
                "title": "Báo cáo doanh thu",
                "icon": "▥",
                "class": ReportsPage
            }
        }

        self.setup_style()

        self.root.protocol(
            "WM_DELETE_WINDOW",
            self.on_close
        )

        saved_user = self.load_session()

        if saved_user:
            self.current_user = saved_user
            self.create_layout()
            self.show_page("dashboard")
            self.update_user_header()
        else:
            self.show_login()

    # ==================================================
    # STYLE
    # ==================================================

    def setup_style(self):

        style = ttk.Style()

        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure(
            "TFrame",
            background="#F3F4F6"
        )

        style.configure(
            "TLabel",
            background="#F3F4F6",
            foreground="#1F2937",
            font=("Arial", 10)
        )

        style.configure(
            "Nav.TButton",
            font=("Arial", 10),
            padding=(12, 11),
            anchor="w",
            background="#1F2937",
            foreground="white",
            borderwidth=0
        )

        style.map(
            "Nav.TButton",
            background=[
                ("active", "#374151"),
                ("pressed", "#374151")
            ],
            foreground=[
                ("active", "white")
            ]
        )

        style.configure(
            "Active.Nav.TButton",
            font=("Arial", 10, "bold"),
            padding=(12, 11),
            anchor="w",
            background="#2563EB",
            foreground="white",
            borderwidth=0
        )

        style.map(
            "Active.Nav.TButton",
            background=[
                ("active", "#1D4ED8"),
                ("pressed", "#1D4ED8")
            ],
            foreground=[
                ("active", "white")
            ]
        )

    # ==================================================
    # LOGIN SCREEN
    # ==================================================

    def show_login(self):

        if hasattr(self, "login_frame"):
            try:
                if self.login_frame.winfo_exists():
                    self.login_frame.destroy()
            except tk.TclError:
                pass

        self.login_frame = tk.Frame(
            self.root,
            bg="#F3F4F6"
        )
        self.login_frame.pack(fill="both", expand=True)

        box = tk.Frame(
            self.login_frame,
            bg="white",
            padx=45,
            pady=35,
            highlightbackground="#E5E7EB",
            highlightthickness=1
        )
        box.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(
            box,
            text="HOTEL MANAGEMENT",
            font=("Arial", 21, "bold"),
            bg="white",
            fg="#1F2937"
        ).pack(pady=(0, 8))

        tk.Label(
            box,
            text="Đăng nhập hệ thống",
            font=("Arial", 12),
            bg="white",
            fg="#6B7280"
        ).pack(pady=(0, 25))

        tk.Label(
            box,
            text="Tên đăng nhập",
            font=("Arial", 10, "bold"),
            bg="white"
        ).pack(anchor="w")

        self.username_entry = tk.Entry(
            box,
            width=34,
            font=("Arial", 12),
            relief="solid",
            bd=1
        )
        self.username_entry.pack(pady=(6, 16), ipady=7)

        tk.Label(
            box,
            text="Mật khẩu",
            font=("Arial", 10, "bold"),
            bg="white"
        ).pack(anchor="w")

        self.password_entry = tk.Entry(
            box,
            width=34,
            font=("Arial", 12),
            show="*",
            relief="solid",
            bd=1
        )
        self.password_entry.pack(pady=(6, 10), ipady=7)

        self.show_password_var = tk.BooleanVar(value=False)

        tk.Checkbutton(
            box,
            text="Hiện mật khẩu",
            variable=self.show_password_var,
            command=self.toggle_password,
            bg="white",
            activebackground="white"
        ).pack(anchor="w")

        self.login_button = tk.Button(
            box,
            text="ĐĂNG NHẬP",
            font=("Arial", 11, "bold"),
            bg="#2563EB",
            fg="white",
            activebackground="#1D4ED8",
            relief="flat",
            cursor="hand2",
            command=self.login,
            height=2
        )
        self.login_button.pack(fill="x", pady=(20, 10))

        tk.Button(
            box,
            text="Đăng ký tài khoản mới",
            font=("Arial", 10),
            bg="white",
            fg="#2563EB",
            relief="flat",
            cursor="hand2",
            command=self.show_register
        ).pack(pady=5)

        tk.Label(
            box,
            text="Hotel Management System",
            font=("Arial", 9),
            bg="white",
            fg="#9CA3AF"
        ).pack(pady=(15, 0))

        self.username_entry.focus_set()

        self.username_entry.bind(
            "<Return>",
            lambda event: self.password_entry.focus_set()
        )

        self.password_entry.bind(
            "<Return>",
            lambda event: self.login()
        )

    # ==================================================
    # SESSION
    # ==================================================

    def get_session_path(self):
        return os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "session.json"
        )

    def save_session(self, user):
        data = {
            "logged_in": True,
            "user": user
        }

        with open(
                self.get_session_path(),
                "w",
                encoding="utf-8"
        ) as file:
            json.dump(data, file, ensure_ascii=False, indent=4)

    def load_session(self):
        try:
            with open(
                    self.get_session_path(),
                    "r",
                    encoding="utf-8"
            ) as file:
                data = json.load(file)

            if data.get("logged_in") and data.get("user"):
                return data["user"]

        except (FileNotFoundError, json.JSONDecodeError):
            pass

        return None

    def clear_session(self):
        try:
            os.remove(self.get_session_path())
        except FileNotFoundError:
            pass

    # ==================================================
    # SHOW / HIDE PASSWORD
    # ==================================================

    def toggle_password(self):

        if self.show_password_var.get():
            self.password_entry.config(show="")
        else:
            self.password_entry.config(show="*")

    # ==================================================
    # RESULT POPUP
    # ==================================================

    def show_result_popup(
        self,
        parent,
        title,
        message,
        success=True
    ):

        popup = tk.Toplevel(parent)

        popup.title(title)
        popup.geometry("380x230")
        popup.resizable(False, False)
        popup.configure(bg="white")

        popup.transient(parent)
        popup.grab_set()

        # Căn giữa cửa sổ thông báo
        popup.update_idletasks()

        parent_x = parent.winfo_rootx()
        parent_y = parent.winfo_rooty()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()

        x = parent_x + (parent_width - 380) // 2
        y = parent_y + (parent_height - 230) // 2

        popup.geometry(f"+{x}+{y}")

        if success:
            color = "#16A34A"
            icon = "✓"
        else:
            color = "#DC2626"
            icon = "✕"

        tk.Label(
            popup,
            text=icon,
            font=("Arial", 34, "bold"),
            fg=color,
            bg="white"
        ).pack(pady=(18, 3))

        tk.Label(
            popup,
            text=title,
            font=("Arial", 16, "bold"),
            fg=color,
            bg="white"
        ).pack(pady=5)

        tk.Label(
            popup,
            text=message,
            font=("Arial", 10),
            fg="#374151",
            bg="white",
            wraplength=320,
            justify="center"
        ).pack(pady=8)

        tk.Button(
            popup,
            text="Đóng",
            font=("Arial", 10, "bold"),
            bg=color,
            fg="white",
            activebackground=color,
            activeforeground="white",
            relief="flat",
            cursor="hand2",
            width=12,
            command=popup.destroy
        ).pack(pady=10)

        popup.wait_window()

    # ==================================================
    # LOGIN PROCESS
    # ==================================================

    def login(self):

        username = self.username_entry.get().strip()
        password = self.password_entry.get()

        if not username or not password:

            messagebox.showwarning(
                "Thông báo",
                "Vui lòng nhập tên đăng nhập và mật khẩu."
            )

            return

        self.login_button.config(
            state="disabled",
            text="ĐANG ĐĂNG NHẬP..."
        )

        self.root.update_idletasks()

        try:

            result = api_client.post(
                "/api/auth/login",
                {
                    "username": username,
                    "password": password
                }
            )

            if result.get("success"):

                self.current_user = result.get("user")

                if not self.current_user:
                    raise APIError(
                        "API không trả về thông tin người dùng."
                    )

                self.save_session(self.current_user)

                self.login_frame.destroy()

                self.create_layout()
                self.show_page("dashboard")
                self.update_user_header()
            else:

                messagebox.showerror(
                    "Đăng nhập thất bại",
                    result.get(
                        "message",
                        "Không thể đăng nhập."
                    )
                )

        except APIError as error:

            messagebox.showerror(
                "Đăng nhập thất bại",
                str(error)
            )

        finally:

            try:
                if self.login_frame.winfo_exists():
                    self.login_button.config(
                        state="normal",
                        text="ĐĂNG NHẬP"
                    )
            except tk.TclError:
                pass

    # ==================================================
    # REGISTER SCREEN
    # ==================================================

    def show_register(self):

        # Xóa giao diện đăng nhập
        self.login_frame.destroy()

        # Tạo giao diện đăng ký trên chính cửa sổ hiện tại
        self.login_frame = tk.Frame(
            self.root,
            bg="#F3F4F6"
        )
        self.login_frame.pack(fill="both", expand=True)

        box = tk.Frame(
            self.login_frame,
            bg="white",
            padx=45,
            pady=25,
            highlightbackground="#E5E7EB",
            highlightthickness=1
        )
        box.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(
            box,
            text="TẠO TÀI KHOẢN",
            font=("Arial", 21, "bold"),
            bg="white",
            fg="#1F2937"
        ).pack(pady=(0, 8))

        tk.Label(
            box,
            text="Đăng ký tài khoản nhân viên",
            font=("Arial", 11),
            bg="white",
            fg="#6B7280"
        ).pack(pady=(0, 20))

        # Họ và tên
        tk.Label(
            box,
            text="Họ và tên",
            bg="white",
            font=("Arial", 10, "bold")
        ).pack(anchor="w")

        full_name_entry = tk.Entry(
            box,
            font=("Arial", 12),
            relief="solid",
            bd=1
        )
        full_name_entry.pack(fill="x", pady=(5, 13), ipady=7)

        # Tên đăng nhập
        tk.Label(
            box,
            text="Tên đăng nhập",
            bg="white",
            font=("Arial", 10, "bold")
        ).pack(anchor="w")

        username_entry = tk.Entry(
            box,
            font=("Arial", 12),
            relief="solid",
            bd=1
        )
        username_entry.pack(fill="x", pady=(5, 13), ipady=7)

        # Mật khẩu
        tk.Label(
            box,
            text="Mật khẩu",
            bg="white",
            font=("Arial", 10, "bold")
        ).pack(anchor="w")

        password_entry = tk.Entry(
            box,
            font=("Arial", 12),
            show="*",
            relief="solid",
            bd=1
        )
        password_entry.pack(fill="x", pady=(5, 13), ipady=7)

        # Xác nhận mật khẩu
        tk.Label(
            box,
            text="Xác nhận mật khẩu",
            bg="white",
            font=("Arial", 10, "bold")
        ).pack(anchor="w")

        confirm_entry = tk.Entry(
            box,
            font=("Arial", 12),
            show="*",
            relief="solid",
            bd=1
        )
        confirm_entry.pack(fill="x", pady=(5, 15), ipady=7)

        # Xử lý đăng ký
        def register():

            full_name = full_name_entry.get().strip()
            username = username_entry.get().strip()
            password = password_entry.get()
            confirm_password = confirm_entry.get()

            if not all([full_name, username, password, confirm_password]):
                self.show_result_popup(
                    self.root,
                    "Thiếu thông tin",
                    "Vui lòng nhập đầy đủ thông tin.",
                    False
                )
                return

            if len(full_name) < 2:
                self.show_result_popup(
                    self.root,
                    "Thông tin không hợp lệ",
                    "Họ tên phải có ít nhất 2 ký tự.",
                    False
                )
                return

            if len(username) < 3:
                self.show_result_popup(
                    self.root,
                    "Thông tin không hợp lệ",
                    "Tên đăng nhập phải có ít nhất 3 ký tự.",
                    False
                )
                return

            if len(password) < 6:
                self.show_result_popup(
                    self.root,
                    "Mật khẩu không hợp lệ",
                    "Mật khẩu phải có ít nhất 6 ký tự.",
                    False
                )
                return

            if password != confirm_password:
                self.show_result_popup(
                    self.root,
                    "Mật khẩu không khớp",
                    "Vui lòng nhập lại mật khẩu xác nhận.",
                    False
                )
                return

            register_button.config(
                state="disabled",
                text="ĐANG ĐĂNG KÝ..."
            )

            self.root.update_idletasks()

            try:

                result = api_client.post(
                    "/api/auth/register",
                    {
                        "full_name": full_name,
                        "username": username,
                        "password": password
                    }
                )

                if result.get("success"):

                    # Chuyển về màn hình đăng nhập
                    self.show_login()

                    self.username_entry.insert(0, username)
                    self.password_entry.focus_set()

                    # Chuyển về màn hình đăng nhập
                    # Khôi phục phiên đăng nhập
                    saved_user = self.load_session()

                    if saved_user:
                        self.current_user = saved_user
                        self.create_layout()
                        self.show_page("dashboard")
                        self.update_user_header()
                    else:
                        self.show_login()

                    self.username_entry.insert(0, username)
                    self.password_entry.focus_set()

                else:

                    self.show_result_popup(
                        self.root,
                        "Đăng ký thất bại",
                        result.get(
                            "message",
                            "Không thể tạo tài khoản."
                        ),
                        False
                    )

            except APIError as error:

                self.show_result_popup(
                    self.root,
                    "Đăng ký thất bại",
                    str(error),
                    False
                )

            finally:

                try:
                    if register_button.winfo_exists():
                        register_button.config(
                            state="normal",
                            text="ĐĂNG KÝ"
                        )
                except tk.TclError:
                    pass

        # Nút đăng ký
        register_button = tk.Button(
            box,
            text="ĐĂNG KÝ",
            font=("Arial", 11, "bold"),
            bg="#16A34A",
            fg="white",
            activebackground="#15803D",
            activeforeground="white",
            relief="flat",
            cursor="hand2",
            command=register,
            height=2
        )
        register_button.pack(fill="x", pady=(5, 8))

        # Nút quay lại đăng nhập
        tk.Button(
            box,
            text="← Quay lại đăng nhập",
            font=("Arial", 10),
            bg="white",
            fg="#2563EB",
            relief="flat",
            cursor="hand2",
            command=self.show_login
        ).pack(pady=5)

        full_name_entry.focus_set()

    # ==================================================
    # USER INFORMATION
    # ==================================================

    def update_user_header(self):

        if not self.current_user:
            return

        name = (
            self.current_user.get("full_name")
            or self.current_user.get("username")
        )

        self.user_label.config(
            text=f"Xin chào, {name}"
        )

    # ==================================================
    # LOGOUT
    # ==================================================

    def logout(self):

        confirm = messagebox.askyesno(
            "Xác nhận đăng xuất",
            "Bạn có chắc chắn muốn đăng xuất không?"
        )

        if not confirm:
            return

        self.clear_session()

        if hasattr(self, "main_container"):
            self.main_container.destroy()

        self.current_page = None
        self.current_page_name = None
        self.nav_buttons = {}

        self.show_login()

    # ==================================================
    # CREATE MAIN LAYOUT
    # ==================================================

    def create_layout(self):

        self.main_container = tk.Frame(
            self.root,
            bg="#F3F4F6"
        )

        self.main_container.pack(
            fill="both",
            expand=True
        )

        # Sidebar
        self.sidebar = tk.Frame(
            self.main_container,
            bg="#1F2937",
            width=250
        )

        self.sidebar.pack(
            side="left",
            fill="y"
        )

        self.sidebar.pack_propagate(False)

        self.create_sidebar()

        # Content
        self.content_container = tk.Frame(
            self.main_container,
            bg="#F3F4F6"
        )

        self.content_container.pack(
            side="right",
            fill="both",
            expand=True
        )

        self.create_header()
        self.create_content()
        self.create_status_bar()

    # ==================================================
    # SIDEBAR
    # ==================================================

    def create_sidebar(self):

        logo_frame = tk.Frame(
            self.sidebar,
            bg="#1F2937"
        )

        logo_frame.pack(
            fill="x",
            padx=15,
            pady=(25, 25)
        )

        tk.Label(
            logo_frame,
            text="HOTEL",
            font=("Arial", 23, "bold"),
            bg="#1F2937",
            fg="white"
        ).pack(anchor="w")

        tk.Label(
            logo_frame,
            text="MANAGEMENT SYSTEM",
            font=("Arial", 9, "bold"),
            bg="#1F2937",
            fg="#9CA3AF"
        ).pack(anchor="w", pady=(3, 0))

        tk.Frame(
            self.sidebar,
            bg="#374151",
            height=1
        ).pack(fill="x", padx=15, pady=(0, 15))

        tk.Label(
            self.sidebar,
            text="MENU CHỨC NĂNG",
            font=("Arial", 9, "bold"),
            bg="#1F2937",
            fg="#9CA3AF"
        ).pack(anchor="w", padx=20, pady=(0, 10))

        menu_frame = tk.Frame(
            self.sidebar,
            bg="#1F2937"
        )

        menu_frame.pack(
            fill="x",
            padx=10
        )

        for page_key, page_info in self.pages.items():

            button_text = (
                f"{page_info['icon']}   {page_info['title']}"
            )

            button = ttk.Button(
                menu_frame,
                text=button_text,
                style="Nav.TButton",
                command=lambda key=page_key: self.show_page(key)
            )

            button.pack(
                fill="x",
                pady=3
            )

            self.nav_buttons[page_key] = button

        footer = tk.Frame(
            self.sidebar,
            bg="#1F2937"
        )

        footer.pack(
            side="bottom",
            fill="x",
            padx=15,
            pady=20
        )

        tk.Frame(
            footer,
            bg="#374151",
            height=1
        ).pack(fill="x", pady=(0, 12))

        tk.Label(
            footer,
            text="HOTEL MANAGEMENT",
            font=("Arial", 9, "bold"),
            bg="#1F2937",
            fg="#D1D5DB"
        ).pack(anchor="w")

        tk.Label(
            footer,
            text="Database Management Project",
            font=("Arial", 8),
            bg="#1F2937",
            fg="#9CA3AF"
        ).pack(anchor="w", pady=(4, 0))

    # ==================================================
    # HEADER
    # ==================================================

    def create_header(self):

        self.header = tk.Frame(
            self.content_container,
            bg="white",
            height=70
        )

        self.header.pack(fill="x")
        self.header.pack_propagate(False)

        self.header_title = tk.Label(
            self.header,
            text="Tổng quan",
            font=("Arial", 16, "bold"),
            bg="white",
            fg="#111827"
        )

        self.header_title.pack(
            side="left",
            padx=25
        )

        self.header_right = tk.Frame(
            self.header,
            bg="white"
        )

        self.header_right.pack(
            side="right",
            padx=25
        )

        self.user_label = tk.Label(
            self.header_right,
            text="",
            font=("Arial", 10, "bold"),
            bg="white",
            fg="#1F2937"
        )

        self.user_label.pack(
            side="left",
            padx=10
        )

        tk.Button(
            self.header_right,
            text="Đăng xuất",
            bg="#DC2626",
            fg="white",
            font=("Arial", 9, "bold"),
            relief="flat",
            cursor="hand2",
            command=self.logout
        ).pack(
            side="left",
            padx=5
        )

        tk.Frame(
            self.content_container,
            bg="#E5E7EB",
            height=1
        ).pack(fill="x")

    # ==================================================
    # CONTENT
    # ==================================================

    def create_content(self):

        self.page_container = tk.Frame(
            self.content_container,
            bg="#F3F4F6"
        )

        self.page_container.pack(
            fill="both",
            expand=True
        )

    # ==================================================
    # STATUS BAR
    # ==================================================

    def create_status_bar(self):

        self.status_bar = tk.Frame(
            self.content_container,
            bg="white",
            height=30
        )

        self.status_bar.pack(
            side="bottom",
            fill="x"
        )

        self.status_bar.pack_propagate(False)

        self.status_text = tk.Label(
            self.status_bar,
            text="Sẵn sàng",
            font=("Arial", 8),
            bg="white",
            fg="#6B7280"
        )

        self.status_text.pack(
            side="left",
            padx=15
        )

        tk.Label(
            self.status_bar,
            text="Hotel Management System",
            font=("Arial", 8),
            bg="white",
            fg="#9CA3AF"
        ).pack(
            side="right",
            padx=15
        )

    # ==================================================
    # PAGE NAVIGATION
    # ==================================================

    def show_page(self, page_key):

        if page_key not in self.pages:

            messagebox.showerror(
                "Lỗi",
                "Không tìm thấy chức năng được yêu cầu."
            )

            return

        for widget in self.page_container.winfo_children():
            widget.destroy()

        page_info = self.pages[page_key]

        self.header_title.config(
            text=page_info["title"]
        )

        for key, button in self.nav_buttons.items():

            if key == page_key:
                button.configure(
                    style="Active.Nav.TButton"
                )
            else:
                button.configure(
                    style="Nav.TButton"
                )

        try:

            page_class = page_info["class"]

            self.current_page = page_class(
                self.page_container
            )

            self.current_page_name = page_key

            self.status_text.config(
                text=f"Đang mở: {page_info['title']}"
            )

        except Exception as error:

            self.current_page = None
            self.current_page_name = None

            self.status_text.config(
                text="Không thể mở chức năng."
            )

            messagebox.showerror(
                "Lỗi mở trang",
                f"Không thể mở {page_info['title']}.\n\n"
                f"Chi tiết lỗi:\n{error}"
            )

    # ==================================================
    # CLOSE APPLICATION
    # ==================================================

    def on_close(self):

        confirm = messagebox.askyesno(
            "Xác nhận thoát",
            "Bạn có chắc chắn muốn thoát chương trình?"
        )

        if confirm:
            self.root.destroy()


# ======================================================
# MAIN
# ======================================================

def main():

    root = tk.Tk()

    app = HotelManagementApp(root)

    root.mainloop()


if __name__ == "__main__":
    main()
