
import tkinter as tk

from pages.dashboard import Dashboard
from pages.customers import CustomersPage
from pages.rooms import RoomsPage
from pages.room_types import RoomTypesPage
from pages.bookings import BookingsPage
from pages.peak_seasons import PeakSeasonsPage
from pages.services import ServicesPage
from pages.payments import PaymentsPage
from pages.invoices import InvoicesPage
from pages.reports import ReportsPage


class HotelManagementApp:
    def __init__(self, root):
        self.root = root

        # ===== WINDOW SETTINGS =====
        self.root.title("Hotel Management System")
        self.root.geometry("1400x800")
        self.root.minsize(1100, 650)
        self.root.configure(bg="#F4F6F9")

        # ===== COLOR SETTINGS =====
        self.navy = "#101F35"
        self.gold = "#D5AD5B"
        self.white = "#FFFFFF"
        self.background = "#F4F6F9"
        self.active_color = "#243A58"
        self.gray = "#8793A5"

        # ===== BUILD APPLICATION =====
        self.build_layout()

        # Open dashboard when application starts
        self.show_dashboard()

    # ==========================================
    # MAIN LAYOUT
    # ==========================================
    def build_layout(self):

        # ===== SIDEBAR =====
        self.sidebar = tk.Frame(
            self.root,
            bg=self.navy,
            width=245
        )

        self.sidebar.pack(
            side="left",
            fill="y"
        )

        self.sidebar.pack_propagate(False)

        # ===== LOGO =====
        tk.Label(
            self.sidebar,
            text="H HOTEL",
            font=("Georgia", 28, "bold"),
            fg=self.gold,
            bg=self.navy
        ).pack(pady=(40, 5))

        tk.Label(
            self.sidebar,
            text="MANAGEMENT SYSTEM",
            font=("Arial", 10),
            fg=self.white,
            bg=self.navy
        ).pack(pady=(0, 45))

        # ===== MENU ITEMS =====
        menu_items = [
            ("Tổng quan", self.show_dashboard),
            ("Khách hàng", self.show_customers),
            ("Quản lý phòng", self.show_rooms),
            ("Loại phòng", self.show_room_types),
            ("Đặt phòng", self.show_bookings),
            ("Mùa cao điểm", self.show_peak_seasons),
            ("Dịch vụ", self.show_services),
            ("Thanh toán", self.show_payments),
            ("Hóa đơn", self.show_invoices),
            ("Báo cáo", self.show_reports)
        ]

        self.menu_buttons = {}

        for label, command in menu_items:

            button = tk.Button(
                self.sidebar,
                text=label,
                command=command,
                font=("Arial", 11),
                fg=self.white,
                bg=self.navy,
                activebackground=self.active_color,
                activeforeground=self.gold,
                relief="flat",
                anchor="w",
                padx=28,
                pady=14,
                cursor="hand2",
                bd=0
            )

            button.pack(
                fill="x",
                padx=8
            )

            self.menu_buttons[label] = button

        # ===== SIDEBAR FOOTER =====
        tk.Label(
            self.sidebar,
            text="HOTEL MANAGEMENT v1.0",
            font=("Arial", 8),
            fg="#8793A5",
            bg=self.navy
        ).pack(
            side="bottom",
            pady=20
        )

        # ===== MAIN CONTENT AREA =====
        self.main_area = tk.Frame(
            self.root,
            bg=self.background
        )

        self.main_area.pack(
            side="right",
            fill="both",
            expand=True
        )

    # ==========================================
    # CLEAR CURRENT PAGE
    # ==========================================
    def clear_main_area(self):

        for widget in self.main_area.winfo_children():
            widget.destroy()

    # ==========================================
    # UPDATE ACTIVE MENU
    # ==========================================
    def update_active_menu(self, menu_name):

        for name, button in self.menu_buttons.items():

            button.configure(
                bg=self.navy,
                fg=self.white
            )

        if menu_name in self.menu_buttons:

            self.menu_buttons[menu_name].configure(
                bg=self.active_color,
                fg=self.gold
            )

    # ==========================================
    # OPEN PAGE
    # ==========================================
    def open_page(self, page_class, menu_name):

        self.clear_main_area()

        self.update_active_menu(menu_name)

        # Create selected page inside main area
        page_class(self.main_area)

    # ==========================================
    # DASHBOARD
    # ==========================================
    def show_dashboard(self):

        self.open_page(
            Dashboard,
            "Tổng quan"
        )

    # ==========================================
    # CUSTOMER MANAGEMENT
    # ==========================================
    def show_customers(self):

        self.open_page(
            CustomersPage,
            "Khách hàng"
        )

    # ==========================================
    # ROOM MANAGEMENT
    # ==========================================
    def show_rooms(self):

        self.open_page(
            RoomsPage,
            "Quản lý phòng"
        )

    # ==========================================
    # OTHER MODULES - COMING SOON
    # ==========================================
    def show_room_types(self):

        self.open_page(RoomTypesPage, "Loại phòng")

    def show_bookings(self):

        self.open_page(BookingsPage, "Đặt phòng")

    def show_peak_seasons(self):

        self.open_page(PeakSeasonsPage, "Mùa cao điểm")

    def show_services(self):

        self.open_page(ServicesPage, "Dịch vụ")

    def show_payments(self):

        self.open_page(PaymentsPage, "Thanh toán")

    def show_invoices(self):

        self.open_page(InvoicesPage, "Hóa đơn")

    def show_reports(self):

        self.open_page(ReportsPage, "Báo cáo")

    # ==========================================
    # COMING SOON PAGE
    # ==========================================
    def show_coming_soon(self, page_name):

        self.clear_main_area()

        self.update_active_menu(page_name)

        tk.Label(
            self.main_area,
            text=page_name.upper(),
            font=("Arial", 24, "bold"),
            fg=self.navy,
            bg=self.background
        ).pack(
            anchor="w",
            padx=35,
            pady=(35, 10)
        )

        tk.Label(
            self.main_area,
            text="Chức năng này sẽ được xây dựng ở phần tiếp theo.",
            font=("Arial", 12),
            fg=self.gray,
            bg=self.background
        ).pack(
            anchor="w",
            padx=35
        )


# ==========================================
# RUN APPLICATION
# ==========================================
if __name__ == "__main__":

    root = tk.Tk()

    app = HotelManagementApp(root)

    root.mainloop()
