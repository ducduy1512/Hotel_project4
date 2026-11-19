
import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from decimal import Decimal
from xml.sax.saxutils import escape

from api_client import api_client, APIError


class InvoicesPage:

    def __init__(self, parent):
        self.parent = parent
        self.selected_invoice = None
        self.booking_options = {}

        self.frame = ttk.Frame(parent)
        self.frame.pack(
            fill="both",
            expand=True,
            padx=15,
            pady=15
        )

        self.create_widgets()
        self.load_booking_options()
        self.load_invoices()

    # =================================================
    # GIAO DIỆN
    # =================================================

    def create_widgets(self):

        title = ttk.Label(
            self.frame,
            text="QUẢN LÝ HÓA ĐƠN",
            font=("Arial", 18, "bold")
        )
        title.pack(pady=(0, 15))

        # LẬP HÓA ĐƠN TỪ BOOKING
        create_frame = ttk.LabelFrame(
            self.frame,
            text="Lập hóa đơn từ Booking",
            padding=10
        )
        create_frame.pack(fill="x", pady=(0, 8))

        ttk.Label(create_frame, text="Booking:").pack(side="left", padx=(4, 6))
        self.create_booking_var = tk.StringVar()
        self.create_booking_combo = ttk.Combobox(
            create_frame,
            textvariable=self.create_booking_var,
            state="readonly",
            width=48
        )
        self.create_booking_combo.pack(side="left", padx=5, fill="x", expand=True)

        ttk.Button(
            create_frame,
            text="Tải lại Booking",
            command=self.load_booking_options
        ).pack(side="left", padx=5)

        ttk.Label(create_frame, text="Phương thức:").pack(side="left", padx=(10, 6))
        self.create_method_var = tk.StringVar(value="CHUYEN_KHOAN")
        self.create_method_combo = ttk.Combobox(
            create_frame,
            textvariable=self.create_method_var,
            state="readonly",
            width=18,
            values=("TIEN_MAT", "CHUYEN_KHOAN", "THE")
        )
        self.create_method_combo.pack(side="left", padx=5)

        ttk.Button(
            create_frame,
            text="Lập hóa đơn & tính tiền",
            command=self.create_invoice
        ).pack(side="right", padx=5)

        self.booking_status_label = ttk.Label(
            self.frame,
            text="Đang tải danh sách Booking...",
            foreground="#64748B"
        )
        self.booking_status_label.pack(anchor="w", padx=8, pady=(0, 8))

        # TÌM KIẾM

        search_frame = ttk.LabelFrame(
            self.frame,
            text="Tìm kiếm hóa đơn",
            padding=10
        )
        search_frame.pack(fill="x", pady=5)

        ttk.Label(
            search_frame,
            text="Mã hóa đơn:"
        ).pack(side="left", padx=5)

        self.search_var = tk.StringVar()

        ttk.Entry(
            search_frame,
            textvariable=self.search_var,
            width=20
        ).pack(side="left", padx=5)

        ttk.Button(
            search_frame,
            text="Tìm kiếm",
            command=self.search_invoice
        ).pack(side="left", padx=5)

        ttk.Button(
            search_frame,
            text="Hiển thị tất cả",
            command=self.load_invoices
        ).pack(side="left", padx=5)

        ttk.Button(
            search_frame,
            text="Làm mới",
            command=self.load_invoices
        ).pack(side="left", padx=5)

        # NÚT CHỨC NĂNG
        # Đặt phía trên bảng để luôn hiển thị.

        button_frame = ttk.Frame(self.frame)
        button_frame.pack(fill="x", pady=(8, 4))

        ttk.Button(
            button_frame,
            text="Xuất hóa đơn PDF",
            command=self.export_invoice_pdf
        ).pack(side="right", padx=5)

        ttk.Button(
            button_frame,
            text="Xóa thông tin chi tiết",
            command=self.clear_detail
        ).pack(side="right", padx=5)

        # BẢNG HÓA ĐƠN

        table_frame = ttk.Frame(self.frame)
        table_frame.pack(
            fill="both",
            expand=True,
            pady=10
        )

        columns = (
            "id",
            "pay_id",
            "booking_id",
            "ho_ten",
            "so_phong",
            "tien_phong",
            "tien_dich_vu",
            "tong_tien",
            "mua_cao_diem",
            "ngay_lap"
        )

        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            height=8
        )

        headings = {
            "id": "Invoice ID",
            "pay_id": "Payment ID",
            "booking_id": "Booking ID",
            "ho_ten": "Khách hàng",
            "so_phong": "Số phòng",
            "tien_phong": "Tiền phòng",
            "tien_dich_vu": "Tiền dịch vụ",
            "tong_tien": "Tổng tiền",
            "mua_cao_diem": "Mùa cao điểm",
            "ngay_lap": "Ngày lập"
        }

        widths = {
            "id": 85,
            "pay_id": 90,
            "booking_id": 90,
            "ho_ten": 150,
            "so_phong": 80,
            "tien_phong": 120,
            "tien_dich_vu": 120,
            "tong_tien": 130,
            "mua_cao_diem": 110,
            "ngay_lap": 160
        }

        for col in columns:
            self.tree.heading(
                col,
                text=headings[col]
            )

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

        scrollbar_x = ttk.Scrollbar(
            self.frame,
            orient="horizontal",
            command=self.tree.xview
        )

        self.tree.configure(
            yscrollcommand=scrollbar_y.set,
            xscrollcommand=scrollbar_x.set
        )

        self.tree.pack(
            side="left",
            fill="both",
            expand=True
        )

        scrollbar_y.pack(
            side="right",
            fill="y"
        )

        scrollbar_x.pack(fill="x")

        self.tree.bind(
            "<<TreeviewSelect>>",
            self.on_select
        )

        # CHI TIẾT HÓA ĐƠN

        detail_frame = ttk.LabelFrame(
            self.frame,
            text="Thông tin hóa đơn được chọn",
            padding=12
        )
        detail_frame.pack(fill="x", pady=5)

        self.detail_labels = {}

        fields = [
            ("id", "Mã hóa đơn"),
            ("pay_id", "Mã thanh toán"),
            ("booking_id", "Mã booking"),
            ("ho_ten", "Khách hàng"),
            ("so_phong", "Số phòng"),
            ("tong_tien", "Tổng thanh toán")
        ]

        for index, (key, label_text) in enumerate(fields):

            row = index // 3
            col = (index % 3) * 2

            ttk.Label(
                detail_frame,
                text=label_text + ":"
            ).grid(
                row=row,
                column=col,
                padx=5,
                pady=6,
                sticky="w"
            )

            value_label = ttk.Label(
                detail_frame,
                text="",
                font=("Arial", 10, "bold")
            )

            value_label.grid(
                row=row,
                column=col + 1,
                padx=5,
                pady=6,
                sticky="w"
            )

            self.detail_labels[key] = value_label

    # =================================================
    # HÀM HỖ TRỢ
    # =================================================

    @staticmethod
    def format_money(value):

        try:
            number = Decimal(str(value or 0))
            return f"{number:,.0f} đ"

        except Exception:
            return "0 đ"

    @staticmethod
    def format_date(value):

        if value is None:
            return ""

        return str(value)

    @staticmethod
    def safe_text(value):

        return escape(
            str(value if value is not None else "")
        )

    @staticmethod
    def extract_list(response):

        if isinstance(response, list):
            return response

        if isinstance(response, dict):
            invoices = response.get("invoices")

            if isinstance(invoices, list):
                return invoices

        return []

    # =================================================
    # LẬP HÓA ĐƠN TỪ BOOKING
    # =================================================

    def load_booking_options(self):
        """Tải các Booking chưa có hóa đơn từ endpoint chuyên biệt."""
        previous_display = self.create_booking_var.get().strip()
        previous_booking_id = self.booking_options.get(previous_display)

        try:
            response = api_client.get("/api/invoices/eligible-bookings")

            if isinstance(response, list):
                bookings = response
            elif isinstance(response, dict):
                bookings = response.get("bookings")
                if bookings is None:
                    bookings = response.get("data", [])
            else:
                bookings = None

            if not isinstance(bookings, list):
                raise APIError(
                    "API danh sách Booking đủ điều kiện lập hóa đơn "
                    "không trả về danh sách hợp lệ."
                )

            self.booking_options = {}
            display_values = []
            selected_display = ""

            for booking in bookings:
                if not isinstance(booking, dict):
                    continue

                booking_id = booking.get("id", booking.get("booking_id"))
                if booking_id is None:
                    continue

                status = str(booking.get("trang_thai") or "").strip()
                if status == "DA_HUY":
                    continue

                room = booking.get("so_phong")
                if room in (None, ""):
                    room = booking.get("phong_id", "?")

                customer = booking.get("ho_ten") or f"Khách #{booking.get('khach_id', '?')}"
                checkin = str(booking.get("ngay_nhan") or "")[:10]
                checkout = str(booking.get("ngay_tra") or "")[:10]

                display = (
                    f"Booking #{booking_id} | Phòng {room} | {customer} | "
                    f"{checkin} → {checkout} | {status or 'CHƯA RÕ TRẠNG THÁI'}"
                )
                numeric_id = int(booking_id)
                self.booking_options[display] = numeric_id
                display_values.append(display)

                if previous_booking_id == numeric_id:
                    selected_display = display

            self.create_booking_combo["values"] = display_values

            if selected_display:
                self.create_booking_var.set(selected_display)
            elif display_values:
                self.create_booking_var.set(display_values[0])
            else:
                self.create_booking_var.set("")

            if hasattr(self, "booking_status_label"):
                if display_values:
                    self.booking_status_label.config(
                        text=f"Có {len(display_values)} Booking chưa có hóa đơn.",
                        foreground="#247A4B"
                    )
                else:
                    self.booking_status_label.config(
                        text="Không có Booking đủ điều kiện. Hãy kiểm tra Booking hoặc nhấn Tải lại.",
                        foreground="#A16207"
                    )

        except APIError as error:
            if hasattr(self, "booking_status_label"):
                self.booking_status_label.config(
                    text=f"Không tải được Booking: {error}",
                    foreground="#C0392B"
                )
            messagebox.showerror("Lỗi tải Booking", str(error))
        except (TypeError, ValueError, KeyError) as error:
            message = f"Dữ liệu Booking trả về không hợp lệ: {error}"
            if hasattr(self, "booking_status_label"):
                self.booking_status_label.config(
                    text=message,
                    foreground="#C0392B"
                )
            messagebox.showerror("Lỗi dữ liệu Booking", message)

    def create_invoice(self):
        """Ask the API/Stored Procedure to calculate and create Pay + HoaDon."""
        display = self.create_booking_var.get().strip()
        booking_id = self.booking_options.get(display)
        if booking_id is None:
            messagebox.showwarning("Chưa chọn Booking", "Vui lòng chọn Booking cần lập hóa đơn.")
            return

        method = self.create_method_var.get().strip()
        if method not in {"TIEN_MAT", "CHUYEN_KHOAN", "THE"}:
            messagebox.showwarning("Phương thức không hợp lệ", "Vui lòng chọn phương thức thanh toán hợp lệ.")
            return

        if not messagebox.askyesno(
            "Xác nhận lập hóa đơn",
            f"Tính tiền và lập hóa đơn cho Booking #{booking_id} bằng {method}?\n"
            "Database sẽ tự tính tiền phòng, dịch vụ và tạo giao dịch Pay chờ thanh toán."
        ):
            return

        try:
            result = api_client.post(
                "/api/invoices/",
                {"booking_id": booking_id, "method": method}
            )
            invoice = result.get("invoice", {}) if isinstance(result, dict) else {}
            total = invoice.get("tong_tien", 0)
            invoice_id = invoice.get("id", "?")
            messagebox.showinfo(
                "Lập hóa đơn thành công",
                f"{result.get('message', 'Đã lập hóa đơn.')}\n"
                f"Mã hóa đơn: {invoice_id}\n"
                f"Mã Booking: {booking_id}\n"
                f"Tổng tiền: {self.format_money(total)}\n"
                f"Trạng thái thanh toán: {invoice.get('payment_status', 'CHO_THANH_TOAN')}"
            )
            self.load_invoices()
            self.load_booking_options()
        except APIError as error:
            messagebox.showerror("Không thể lập hóa đơn", str(error))

    # =================================================
    # TẢI DANH SÁCH HÓA ĐƠN
    # =================================================

    def load_invoices(self):

        try:
            response = api_client.get("/api/invoices/")
            invoices = self.extract_list(response)

            self.display_invoices(invoices)

        except APIError as error:
            messagebox.showerror(
                "Lỗi tải hóa đơn",
                str(error)
            )

    def display_invoices(self, invoices):

        for item in self.tree.get_children():
            self.tree.delete(item)

        self.clear_detail()

        for invoice in invoices:

            invoice_id = invoice.get("id")

            if invoice_id is None:
                continue

            self.tree.insert(
                "",
                "end",
                iid=str(invoice_id),
                values=(
                    invoice_id,
                    invoice.get("pay_id", ""),
                    invoice.get("booking_id", ""),
                    invoice.get("ho_ten", ""),
                    invoice.get("so_phong", ""),
                    self.format_money(
                        invoice.get("tien_phong", 0)
                    ),
                    self.format_money(
                        invoice.get("tien_dich_vu", 0)
                    ),
                    self.format_money(
                        invoice.get("tong_tien", 0)
                    ),
                    "CÓ" if invoice.get("ap_dung_mua_cao_diem") else "KHÔNG",
                    self.format_date(
                        invoice.get("ngay_lap", "")
                    )
                )
            )

    # =================================================
    # CHỌN HÓA ĐƠN
    # =================================================

    def on_select(self, event=None):

        selected = self.tree.selection()

        if not selected:
            return

        invoice_id = selected[0]

        try:
            response = api_client.get(
                f"/api/invoices/{invoice_id}"
            )

            invoice = response.get("invoice")

            if not invoice:
                raise APIError(
                    "API không trả về thông tin hóa đơn."
                )

            self.selected_invoice = invoice

            display_fields = {
                "id": invoice.get("id"),
                "pay_id": invoice.get("pay_id"),
                "booking_id": invoice.get("booking_id"),
                "ho_ten": invoice.get("ho_ten"),
                "so_phong": invoice.get("so_phong"),
                "tong_tien": self.format_money(
                    invoice.get("tong_tien", 0)
                )
            }

            for key, value in display_fields.items():

                self.detail_labels[key].config(
                    text=str(
                        value if value is not None else ""
                    )
                )

        except APIError as error:

            messagebox.showerror(
                "Lỗi API",
                str(error)
            )

    # =================================================
    # TÌM KIẾM HÓA ĐƠN
    # =================================================

    def search_invoice(self):

        keyword = self.search_var.get().strip()

        if not keyword:
            messagebox.showwarning(
                "Thông báo",
                "Vui lòng nhập mã hóa đơn."
            )
            return

        try:
            response = api_client.get("/api/invoices/")
            invoices = self.extract_list(response)

            filtered = [
                invoice for invoice in invoices
                if str(invoice.get("id", "")) == keyword
            ]

            self.display_invoices(filtered)

            if not filtered:
                messagebox.showinfo(
                    "Kết quả",
                    "Không tìm thấy hóa đơn."
                )

        except APIError as error:

            messagebox.showerror(
                "Lỗi API",
                str(error)
            )

    # =================================================
    # XUẤT HÓA ĐƠN PDF
    # =================================================

    def export_invoice_pdf(self):

        if not self.selected_invoice:
            messagebox.showwarning(
                "Chưa chọn hóa đơn",
                "Vui lòng chọn một hóa đơn trong bảng trước."
            )
            return

        try:
            from reportlab.lib import colors
            from reportlab.lib.enums import TA_CENTER, TA_RIGHT
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import (
                getSampleStyleSheet,
                ParagraphStyle
            )
            from reportlab.lib.units import mm
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            from reportlab.platypus import (
                SimpleDocTemplate,
                Paragraph,
                Spacer,
                Table,
                TableStyle,
                HRFlowable
            )

        except ImportError:
            messagebox.showerror(
                "Thiếu thư viện",
                "Chưa cài đặt ReportLab.\n\n"
                "Chạy lệnh trong Terminal:\n"
                ".venv\\Scripts\\python.exe -m pip install reportlab"
            )
            return

        # Kiểm tra font Arial trên Windows

        font_regular = r"C:\Windows\Fonts\arial.ttf"
        font_bold = r"C:\Windows\Fonts\arialbd.ttf"

        if not os.path.exists(font_regular):
            messagebox.showerror(
                "Không tìm thấy font",
                f"Không tìm thấy font:\n{font_regular}"
            )
            return

        if not os.path.exists(font_bold):
            messagebox.showerror(
                "Không tìm thấy font",
                f"Không tìm thấy font:\n{font_bold}"
            )
            return

        try:
            if "ArialVN" not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(
                    TTFont("ArialVN", font_regular)
                )

            if "ArialVN-Bold" not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(
                    TTFont("ArialVN-Bold", font_bold)
                )

            pdfmetrics.registerFontFamily(
                "ArialVN",
                normal="ArialVN",
                bold="ArialVN-Bold",
                italic="ArialVN",
                boldItalic="ArialVN-Bold"
            )

        except Exception as error:
            messagebox.showerror(
                "Lỗi font",
                f"Không thể nạp font Arial.\n{error}"
            )
            return

        invoice = self.selected_invoice
        invoice_id = invoice.get("id", "")

        default_name = f"HoaDon_{invoice_id}.pdf"

        save_path = filedialog.asksaveasfilename(
            title="Lưu hóa đơn PDF",
            initialfile=default_name,
            defaultextension=".pdf",
            filetypes=[
                ("PDF files", "*.pdf")
            ]
        )

        if not save_path:
            return

        try:
            self.create_invoice_pdf(
                invoice=invoice,
                save_path=save_path,
                colors=colors,
                A4=A4,
                mm=mm,
                getSampleStyleSheet=getSampleStyleSheet,
                ParagraphStyle=ParagraphStyle,
                SimpleDocTemplate=SimpleDocTemplate,
                Paragraph=Paragraph,
                Spacer=Spacer,
                Table=Table,
                TableStyle=TableStyle,
                HRFlowable=HRFlowable,
                TA_CENTER=TA_CENTER,
                TA_RIGHT=TA_RIGHT
            )

            messagebox.showinfo(
                "Xuất hóa đơn thành công",
                f"Đã xuất hóa đơn #{invoice_id}.\n\n"
                f"Đường dẫn:\n{save_path}"
            )

            # Tự động mở file PDF

            try:
                if sys.platform.startswith("win"):
                    os.startfile(save_path)

                elif sys.platform == "darwin":
                    import subprocess
                    subprocess.Popen(["open", save_path])

                else:
                    import subprocess
                    subprocess.Popen(["xdg-open", save_path])

            except Exception:
                pass

        except Exception as error:
            messagebox.showerror(
                "Lỗi xuất hóa đơn",
                f"Không thể tạo PDF.\n\nChi tiết: {error}"
            )

    # =================================================
    # THIẾT KẾ PDF
    # =================================================

    def create_invoice_pdf(
        self,
        invoice,
        save_path,
        colors,
        A4,
        mm,
        getSampleStyleSheet,
        ParagraphStyle,
        SimpleDocTemplate,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
        HRFlowable,
        TA_CENTER,
        TA_RIGHT
    ):

        gold = colors.HexColor("#D9A441")
        navy = colors.HexColor("#172B4D")
        gray = colors.HexColor("#8190A5")
        light_gray = colors.HexColor("#DCE3EC")

        doc = SimpleDocTemplate(
            save_path,
            pagesize=A4,
            rightMargin=20 * mm,
            leftMargin=20 * mm,
            topMargin=17 * mm,
            bottomMargin=17 * mm,
            title=f"Hóa đơn thanh toán #{invoice.get('id')}",
            author="H HOTEL"
        )

        styles = getSampleStyleSheet()

        hotel_style = ParagraphStyle(
            "HotelVN",
            parent=styles["Title"],
            fontName="ArialVN-Bold",
            fontSize=27,
            leading=32,
            alignment=TA_CENTER,
            textColor=gold,
            spaceAfter=8
        )

        title_style = ParagraphStyle(
            "InvoiceTitleVN",
            parent=styles["Heading1"],
            fontName="ArialVN-Bold",
            fontSize=19,
            leading=24,
            alignment=TA_CENTER,
            textColor=navy,
            spaceAfter=12
        )

        center_style = ParagraphStyle(
            "CenterVN",
            parent=styles["Normal"],
            fontName="ArialVN",
            fontSize=10,
            leading=17,
            alignment=TA_CENTER,
            textColor=navy
        )

        label_style = ParagraphStyle(
            "LabelVN",
            parent=styles["Normal"],
            fontName="ArialVN",
            fontSize=10,
            leading=17,
            textColor=gray
        )

        value_style = ParagraphStyle(
            "ValueVN",
            parent=styles["Normal"],
            fontName="ArialVN-Bold",
            fontSize=10,
            leading=17,
            alignment=TA_RIGHT,
            textColor=navy
        )

        normal_style = ParagraphStyle(
            "NormalVN",
            parent=styles["Normal"],
            fontName="ArialVN",
            fontSize=11,
            leading=18,
            textColor=navy
        )

        total_label_style = ParagraphStyle(
            "TotalLabelVN",
            parent=styles["Normal"],
            fontName="ArialVN-Bold",
            fontSize=13,
            leading=19,
            textColor=navy
        )

        total_value_style = ParagraphStyle(
            "TotalValueVN",
            parent=styles["Normal"],
            fontName="ArialVN-Bold",
            fontSize=15,
            leading=20,
            alignment=TA_RIGHT,
            textColor=gold
        )

        def money(value):
            try:
                return f"{Decimal(str(value or 0)):,.0f} đ"
            except Exception:
                return "0 đ"

        def p(value, style):
            return Paragraph(
                self.safe_text(value),
                style
            )

        # LẤY DỮ LIỆU

        invoice_id = invoice.get("id", "")
        pay_id = invoice.get("pay_id", "")
        booking_id = invoice.get("booking_id", "")

        invoice_date = self.format_date(
            invoice.get("ngay_lap", "")
        )

        customer_name = invoice.get("ho_ten", "")
        room_number = invoice.get("so_phong", "")

        method = invoice.get("method", "")
        payment_status = invoice.get("payment_status", "")

        room_money = money(
            invoice.get("tien_phong", 0)
        )

        service_money = money(
            invoice.get("tien_dich_vu", 0)
        )

        total_money = money(
            invoice.get("tong_tien", 0)
        )

        elements = []

        # HEADER

        elements.append(
            p("H HOTEL", hotel_style)
        )

        elements.append(
            p("HÓA ĐƠN THANH TOÁN", title_style)
        )

        elements.append(
            p(f"Mã hóa đơn: #{invoice_id}", center_style)
        )

        elements.append(
            p(f"Ngày lập: {invoice_date}", center_style)
        )

        elements.append(Spacer(1, 9 * mm))

        elements.append(
            HRFlowable(
                width="100%",
                thickness=1.5,
                color=gold
            )
        )

        elements.append(Spacer(1, 7 * mm))

        # THÔNG TIN THANH TOÁN

        information = [
            ("Mã thanh toán", pay_id),
            ("Mã booking", booking_id),
            ("Khách hàng", customer_name),
            ("Số phòng", room_number),
            ("Phương thức", method),
            ("Trạng thái", payment_status)
        ]

        info_data = []

        for label, value in information:
            info_data.append([
                p(label, label_style),
                p(value, value_style)
            ])

        info_table = Table(
            info_data,
            colWidths=[75 * mm, 95 * mm],
            rowHeights=[12 * mm] * len(info_data)
        )

        info_table.setStyle(
            TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3)
            ])
        )

        elements.append(info_table)

        elements.append(Spacer(1, 5 * mm))

        elements.append(
            HRFlowable(
                width="100%",
                thickness=0.8,
                color=light_gray
            )
        )

        elements.append(Spacer(1, 5 * mm))

        # CHI TIẾT THANH TOÁN

        amount_data = [
            [
                p("Tiền phòng", normal_style),
                p(room_money, value_style)
            ],
            [
                p("Tiền dịch vụ", normal_style),
                p(service_money, value_style)
            ]
        ]

        amount_table = Table(
            amount_data,
            colWidths=[85 * mm, 85 * mm],
            rowHeights=[12 * mm, 12 * mm]
        )

        amount_table.setStyle(
            TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3)
            ])
        )

        elements.append(amount_table)

        elements.append(Spacer(1, 5 * mm))

        elements.append(
            HRFlowable(
                width="100%",
                thickness=0.8,
                color=light_gray
            )
        )

        elements.append(Spacer(1, 8 * mm))

        # TỔNG THANH TOÁN

        total_data = [[
            p("TỔNG THANH TOÁN", total_label_style),
            p(total_money, total_value_style)
        ]]

        total_table = Table(
            total_data,
            colWidths=[85 * mm, 85 * mm]
        )

        total_table.setStyle(
            TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5)
            ])
        )

        elements.append(total_table)

        elements.append(Spacer(1, 20 * mm))

        # FOOTER

        elements.append(
            HRFlowable(
                width="100%",
                thickness=0.8,
                color=light_gray
            )
        )

        elements.append(Spacer(1, 5 * mm))

        elements.append(
            p(
                "Cảm ơn quý khách đã sử dụng dịch vụ của H HOTEL!",
                center_style
            )
        )

        doc.build(elements)

    # =================================================
    # XÓA THÔNG TIN CHI TIẾT
    # =================================================

    def clear_detail(self):

        self.selected_invoice = None

        for label in self.detail_labels.values():
            label.config(text="")
