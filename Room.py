
from tkinter import *
from tkinter import ttk
from datetime import datetime
import mysql.connector


class Roombooking:
    def __init__(self, root):
        self.root = root

        # ================= VARIABLES =================
        self.var_contact = StringVar()
        self.var_checkin = StringVar()
        self.var_checkout = StringVar()
        self.var_roomtype = StringVar(value="Single")
        self.var_roomavailable = StringVar()
        self.var_meal = StringVar(value="Breakfast")
        self.var_noofdays = StringVar(value="1")
        self.var_paidtax = StringVar(value="0")
        self.var_actualtotal = StringVar(value="0")
        self.var_total = StringVar(value="0")

        self.var_search = StringVar()
        self.var_search_by = StringVar(value="Contact")

        # ================= TITLE =================
        Label(
            root,
            text="ROOM BOOKING DETAILS",
            font=("Times New Roman", 18, "bold"),
            bg="black",
            fg="gold"
        ).place(x=0, y=0, width=1310, height=45)

        # ================= LEFT FORM =================
        form = LabelFrame(
            root,
            text="Booking Information",
            font=("Arial", 11, "bold"),
            bd=2,
            relief=RIDGE
        )
        form.place(x=10, y=55, width=390, height=480)

        # Contact
        Label(form, text="Contact", font=("Arial", 10, "bold")).grid(
            row=0, column=0, sticky="w", padx=7, pady=5
        )

        ttk.Entry(form, textvariable=self.var_contact, width=20).grid(
            row=0, column=1, padx=5, pady=5
        )

        # Check In
        Label(form, text="Check In", font=("Arial", 10, "bold")).grid(
            row=1, column=0, sticky="w", padx=7, pady=5
        )

        ttk.Entry(form, textvariable=self.var_checkin, width=20).grid(
            row=1, column=1, padx=5, pady=5
        )

        # Check Out
        Label(form, text="Check Out", font=("Arial", 10, "bold")).grid(
            row=2, column=0, sticky="w", padx=7, pady=5
        )

        ttk.Entry(form, textvariable=self.var_checkout, width=20).grid(
            row=2, column=1, padx=5, pady=5
        )

        # Room Type
        Label(form, text="Room Type", font=("Arial", 10, "bold")).grid(
            row=3, column=0, sticky="w", padx=7, pady=5
        )

        self.combo_roomtype = ttk.Combobox(
            form,
            textvariable=self.var_roomtype,
            state="readonly",
            width=18
        )
        self.combo_roomtype.grid(row=3, column=1, padx=5, pady=5)

        self.combo_roomtype.bind(
            "<<ComboboxSelected>>",
            self.load_room_numbers
        )

        # Room No
        Label(form, text="Room No", font=("Arial", 10, "bold")).grid(
            row=4, column=0, sticky="w", padx=7, pady=5
        )

        self.combo_roomno = ttk.Combobox(
            form,
            textvariable=self.var_roomavailable,
            width=18
        )
        self.combo_roomno.grid(row=4, column=1, padx=5, pady=5)

        # Meal
        Label(form, text="Meal", font=("Arial", 10, "bold")).grid(
            row=5, column=0, sticky="w", padx=7, pady=5
        )

        ttk.Combobox(
            form,
            textvariable=self.var_meal,
            values=("Breakfast", "Lunch", "Dinner"),
            width=18
        ).grid(row=5, column=1, padx=5, pady=5)

        # Number of Days
        Label(form, text="No. of Days", font=("Arial", 10, "bold")).grid(
            row=6, column=0, sticky="w", padx=7, pady=5
        )

        ttk.Entry(
            form,
            textvariable=self.var_noofdays,
            width=20
        ).grid(row=6, column=1, padx=5, pady=5)

        # Tax
        Label(form, text="Tax", font=("Arial", 10, "bold")).grid(
            row=7, column=0, sticky="w", padx=7, pady=5
        )

        ttk.Entry(
            form,
            textvariable=self.var_paidtax,
            width=20,
            state="readonly"
        ).grid(row=7, column=1, padx=5, pady=5)

        # Subtotal
        Label(form, text="Subtotal", font=("Arial", 10, "bold")).grid(
            row=8, column=0, sticky="w", padx=7, pady=5
        )

        ttk.Entry(
            form,
            textvariable=self.var_actualtotal,
            width=20,
            state="readonly"
        ).grid(row=8, column=1, padx=5, pady=5)

        # Total
        Label(form, text="Total", font=("Arial", 10, "bold")).grid(
            row=9, column=0, sticky="w", padx=7, pady=5
        )

        ttk.Entry(
            form,
            textvariable=self.var_total,
            width=20,
            state="readonly"
        ).grid(row=9, column=1, padx=5, pady=5)

        # ================= BUTTONS =================
        Button(
            form,
            text="Calculate",
            command=self.total,
            bg="black",
            fg="gold",
            font=("Arial", 9, "bold")
        ).place(x=10, y=400, width=85, height=30)

        Button(
            form,
            text="Fetch Customer",
            command=self.fetch_contact,
            bg="black",
            fg="gold",
            font=("Arial", 9, "bold")
        ).place(x=105, y=400, width=120, height=30)

        Button(
            form,
            text="Add",
            command=self.add_data,
            bg="black",
            fg="gold",
            font=("Arial", 9, "bold")
        ).place(x=235, y=400, width=65, height=30)

        Button(
            form,
            text="Update",
            command=self.update,
            bg="black",
            fg="gold",
            font=("Arial", 9, "bold")
        ).place(x=305, y=400, width=70, height=30)

        Button(
            form,
            text="Delete",
            command=self.delete_data,
            bg="black",
            fg="gold",
            font=("Arial", 9, "bold")
        ).place(x=10, y=435, width=85, height=30)

        Button(
            form,
            text="Reset",
            command=self.reset,
            bg="black",
            fg="gold",
            font=("Arial", 9, "bold")
        ).place(x=105, y=435, width=85, height=30)

        # ================= RIGHT FRAME =================
        right_frame = Frame(root, bd=2, relief=RIDGE)
        right_frame.place(x=410, y=55, width=890, height=480)

        # ================= SEARCH =================
        search_frame = LabelFrame(
            right_frame,
            text="Search Booking",
            font=("Arial", 10, "bold")
        )
        search_frame.pack(fill=X, padx=5, pady=5)

        ttk.Combobox(
            search_frame,
            textvariable=self.var_search_by,
            values=("Contact", "Room"),
            state="readonly",
            width=12
        ).grid(row=0, column=0, padx=5, pady=5)

        ttk.Entry(
            search_frame,
            textvariable=self.var_search,
            width=25
        ).grid(row=0, column=1, padx=5)

        Button(
            search_frame,
            text="Search",
            command=self.search_data
        ).grid(row=0, column=2, padx=5)

        Button(
            search_frame,
            text="Show All",
            command=self.fetch_data
        ).grid(row=0, column=3, padx=5)

        # ================= TABLE =================
        table_frame = Frame(right_frame)
        table_frame.pack(fill=BOTH, expand=True, padx=5, pady=5)

        scroll_x = ttk.Scrollbar(table_frame, orient=HORIZONTAL)
        scroll_y = ttk.Scrollbar(table_frame, orient=VERTICAL)

        columns = (
            "contact",
            "checkin",
            "checkout",
            "roomtype",
            "roomavailable",
            "meal",
            "noofdays"
        )

        self.room_table = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            xscrollcommand=scroll_x.set,
            yscrollcommand=scroll_y.set
        )

        scroll_x.pack(side=BOTTOM, fill=X)
        scroll_y.pack(side=RIGHT, fill=Y)

        scroll_x.config(command=self.room_table.xview)
        scroll_y.config(command=self.room_table.yview)

        headings = (
            "Contact",
            "Check In",
            "Check Out",
            "Room Type",
            "Room No",
            "Meal",
            "Days"
        )

        for col, heading in zip(columns, headings):
            self.room_table.heading(col, text=heading)
            self.room_table.column(col, width=110)

        self.room_table.pack(fill=BOTH, expand=True)

        self.room_table.bind(
            "<ButtonRelease-1>",
            self.get_cursor
        )

        # ================= STATUS =================
        self.lbl_status = Label(
            root,
            text="",
            font=("Arial", 10, "bold"),
            fg="green"
        )

        self.lbl_status.place(
            x=10, y=560, width=1280, height=25
        )

        # ================= LOAD DATA =================
        self.load_room_types()
        self.fetch_data()

    # ================= DATABASE =================
    def connect_db(self):
        return mysql.connector.connect(
            host="localhost",
            username="root",
            password="dinomtp16",
            database="management"
        )

    # ================= STATUS =================
    def status(self, text, color="green"):
        self.lbl_status.config(
            text=text,
            fg=color
        )

    # ================= LOAD ROOM TYPE =================
    def load_room_types(self):
        try:
            conn = self.connect_db()
            cursor = conn.cursor()

            cursor.execute(
                "SELECT DISTINCT RoomType FROM details"
            )

            room_types = [row[0] for row in cursor.fetchall()]

            cursor.close()
            conn.close()

            if room_types:
                self.combo_roomtype["values"] = room_types
                self.var_roomtype.set(room_types[0])

            self.load_room_numbers()

        except Exception as e:
            self.combo_roomtype["values"] = (
                "Single", "Double", "Luxury"
            )
            self.status(
                f"Cannot load room types: {e}",
                "red"
            )

    # ================= LOAD ROOM NUMBERS =================
    def load_room_numbers(self, event=None):
        try:
            conn = self.connect_db()
            cursor = conn.cursor()

            cursor.execute(
                "SELECT RoomNo FROM details WHERE RoomType=%s",
                (self.var_roomtype.get(),)
            )

            rooms = [row[0] for row in cursor.fetchall()]

            cursor.close()
            conn.close()

            self.combo_roomno["values"] = rooms

            if rooms:
                self.var_roomavailable.set(rooms[0])
            else:
                self.var_roomavailable.set("")

        except Exception as e:
            self.status(
                f"Cannot load room numbers: {e}",
                "red"
            )

    # ================= FETCH CUSTOMER =================
    def fetch_contact(self):
        contact = self.var_contact.get().strip()

        if not contact:
            self.status(
                "Please enter customer mobile!",
                "red"
            )
            return

        try:
            conn = self.connect_db()
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT Name, Gender, Email, Nationality, Address
                FROM customer
                WHERE Mobile=%s
                """,
                (contact,)
            )

            row = cursor.fetchone()

            cursor.close()
            conn.close()

            if row:
                self.status(
                    f"Customer: {row[0]} | {row[1]} | {row[2]} | "
                    f"{row[3]} | {row[4]}"
                )
            else:
                self.status(
                    "Customer not found!",
                    "red"
                )

        except Exception as e:
            self.status(
                f"Fetch error: {e}",
                "red"
            )

    # ================= CALCULATE TOTAL =================
    def total(self):
        try:
            checkin = datetime.strptime(
                self.var_checkin.get(),
                "%d/%m/%Y"
            )

            checkout = datetime.strptime(
                self.var_checkout.get(),
                "%d/%m/%Y"
            )

            days = (checkout - checkin).days

            if days <= 0:
                self.status(
                    "Check-out must be after Check-in!",
                    "red"
                )
                return False

            self.var_noofdays.set(str(days))

            room_type = self.var_roomtype.get()
            meal = self.var_meal.get().lower()

            # Room price
            if room_type == "Single":
                room_rate = 700
            elif room_type == "Double":
                room_rate = 1200
            else:
                room_rate = 1000

            # Meal price
            if "breakfast" in meal:
                meal_rate = 300
            elif "lunch" in meal:
                meal_rate = 300
            else:
                meal_rate = 200

            subtotal = days * (room_rate + meal_rate)

            tax = subtotal * 0.10

            total = subtotal + tax

            self.var_actualtotal.set(
                f"{subtotal:.0f}"
            )

            self.var_paidtax.set(
                f"{tax:.0f}"
            )

            self.var_total.set(
                f"{total:.0f}"
            )

            self.status(
                "Bill calculated successfully!"
            )

            return True

        except ValueError:
            self.status(
                "Date format must be dd/mm/yyyy!",
                "red"
            )
            return False

    # ================= ADD BOOKING =================
    def add_data(self):
        if (
            not self.var_contact.get().strip()
            or not self.var_checkin.get().strip()
            or not self.var_checkout.get().strip()
            or not self.var_roomavailable.get().strip()
        ):
            self.status(
                "Please fill all required fields!",
                "red"
            )
            return

        if not self.total():
            return

        try:
            conn = self.connect_db()
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO room
                VALUES (%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    self.var_contact.get(),
                    self.var_checkin.get(),
                    self.var_checkout.get(),
                    self.var_roomtype.get(),
                    self.var_roomavailable.get(),
                    self.var_meal.get(),
                    self.var_noofdays.get()
                )
            )

            conn.commit()

            cursor.close()
            conn.close()

            self.fetch_data()

            self.status(
                "Booking added successfully!"
            )

        except Exception as e:
            self.status(
                f"Database error: {e}",
                "red"
            )

    # ================= FETCH DATA =================
    def fetch_data(self):
        try:
            conn = self.connect_db()
            cursor = conn.cursor()

            cursor.execute(
                "SELECT * FROM room"
            )

            rows = cursor.fetchall()

            self.room_table.delete(
                *self.room_table.get_children()
            )

            for row in rows:
                self.room_table.insert(
                    "",
                    END,
                    values=row
                )

            cursor.close()
            conn.close()

            self.status(
                f"Loaded {len(rows)} booking(s)!"
            )

        except Exception as e:
            self.status(
                f"Cannot load bookings: {e}",
                "red"
            )

    # ================= GET CURSOR =================
    def get_cursor(self, event=None):
        selected = self.room_table.focus()

        if not selected:
            return

        row = self.room_table.item(
            selected,
            "values"
        )

        if row:
            self.var_contact.set(row[0])
            self.var_checkin.set(row[1])
            self.var_checkout.set(row[2])
            self.var_roomtype.set(row[3])
            self.var_roomavailable.set(row[4])
            self.var_meal.set(row[5])
            self.var_noofdays.set(row[6])

    # ================= UPDATE BOOKING =================
    def update(self):
        if not self.var_contact.get().strip():
            self.status(
                "Select booking from table first!",
                "red"
            )
            return

        if not self.total():
            return

        try:
            conn = self.connect_db()
            cursor = conn.cursor()

            cursor.execute(
                """
                UPDATE room
                SET CheckIn=%s,
                    CheckOut=%s,
                    RoomType=%s,
                    Room=%s,
                    Meal=%s,
                    NoOfDays=%s
                WHERE Contact=%s
                """,
                (
                    self.var_checkin.get(),
                    self.var_checkout.get(),
                    self.var_roomtype.get(),
                    self.var_roomavailable.get(),
                    self.var_meal.get(),
                    self.var_noofdays.get(),
                    self.var_contact.get()
                )
            )

            conn.commit()

            cursor.close()
            conn.close()

            self.fetch_data()

            self.status(
                "Booking updated successfully!"
            )

        except Exception as e:
            self.status(
                f"Update error: {e}",
                "red"
            )

    # ================= DELETE BOOKING =================
    def delete_data(self):
        if not self.var_contact.get().strip():
            self.status(
                "Select booking from table first!",
                "red"
            )
            return

        try:
            conn = self.connect_db()
            cursor = conn.cursor()

            cursor.execute(
                "DELETE FROM room WHERE Contact=%s",
                (self.var_contact.get(),)
            )

            conn.commit()

            cursor.close()
            conn.close()

            self.fetch_data()
            self.reset()

            self.status(
                "Booking deleted successfully!"
            )

        except Exception as e:
            self.status(
                f"Delete error: {e}",
                "red"
            )

    # ================= SEARCH BOOKING =================
    def search_data(self):
        keyword = self.var_search.get().strip()

        if self.var_search_by.get() == "Contact":
            field = "Contact"
        else:
            field = "Room"

        try:
            conn = self.connect_db()
            cursor = conn.cursor()

            cursor.execute(
                f"SELECT * FROM room WHERE {field} LIKE %s",
                (f"%{keyword}%",)
            )

            rows = cursor.fetchall()

            self.room_table.delete(
                *self.room_table.get_children()
            )

            for row in rows:
                self.room_table.insert(
                    "",
                    END,
                    values=row
                )

            cursor.close()
            conn.close()

            self.status(
                f"Found {len(rows)} booking(s)!"
            )

        except Exception as e:
            self.status(
                f"Search error: {e}",
                "red"
            )

    # ================= RESET =================
    def reset(self):
        self.var_contact.set("")
        self.var_checkin.set("")
        self.var_checkout.set("")
        self.var_roomtype.set("Single")
        self.var_roomavailable.set("")
        self.var_meal.set("Breakfast")
        self.var_noofdays.set("1")
        self.var_paidtax.set("0")
        self.var_actualtotal.set("0")
        self.var_total.set("0")

        self.status("Form reset!")
