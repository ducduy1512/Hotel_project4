
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

        self.frame = ttk.Frame(parent)
        self.frame.pack(
            fill="both",
            expand=True,
            padx=15,
            pady=15
        )

        self.create_widgets()
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
