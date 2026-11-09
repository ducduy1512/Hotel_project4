
from tkinter import *
from tkinter import ttk
import mysql.connector
import random


class Cust_Win:
    def __init__(self, root):
        self.root = root

        self.var_ref = StringVar(value=str(random.randint(1000, 9999)))
        self.var_name = StringVar()
        self.var_mother = StringVar()
        self.var_gender = StringVar(value="Male")
        self.var_post = StringVar()
        self.var_mobile = StringVar()
        self.var_email = StringVar()
        self.var_nationality = StringVar(value="VietNam")
        self.var_idproof = StringVar(value="CCCD")
        self.var_idnumber = StringVar()
        self.var_address = StringVar()

        self.var_search = StringVar()
        self.var_search_by = StringVar(value="Mobile")

        # ================= TITLE =================
        Label(root, text="CUSTOMER DETAILS",
              font=("Times New Roman", 18, "bold"),
              bg="black", fg="gold").place(
                  x=0, y=0, width=1310, height=45
              )

        # ================= FORM =================
        form = LabelFrame(root, text="Customer Information",
                          font=("Arial", 11, "bold"))
        form.place(x=10, y=55, width=420, height=490)

        fields = [
            ("Ref", self.var_ref),
            ("Name", self.var_name),
            ("Mother", self.var_mother),
            ("Gender", self.var_gender),
            ("Post Code", self.var_post),
            ("Mobile", self.var_mobile),
            ("Email", self.var_email),
            ("Nationality", self.var_nationality),
            ("ID Proof", self.var_idproof),
            ("ID Number", self.var_idnumber),
            ("Address", self.var_address)
        ]

        for i, (label, var) in enumerate(fields):
            Label(form, text=label,
                  font=("Arial", 10, "bold")).grid(
                      row=i, column=0, sticky="w", padx=8, pady=6
                  )

            if label == "Gender":
                widget = ttk.Combobox(
                    form, textvariable=var,
                    values=("Male", "Female", "Other"),
                    state="readonly", width=22
                )
            elif label == "Nationality":
                widget = ttk.Combobox(
                    form, textvariable=var,
                    values=("VietNam", "American", "British", "Other"),
                    width=22
                )
            elif label == "ID Proof":
                widget = ttk.Combobox(
                    form, textvariable=var,
                    values=("CCCD", "DrivingLicence", "Passport"),
                    width=22
                )
            else:
                widget = ttk.Entry(form, textvariable=var, width=25)

            widget.grid(row=i, column=1, padx=5, pady=4)

            if label == "Ref":
                widget.config(state="readonly")

        # ================= BUTTONS =================
        btn_frame = Frame(form)
        btn_frame.place(x=5, y=420, width=400, height=35)

        Button(btn_frame, text="Add", command=self.add_data,
               width=8).grid(row=0, column=0, padx=2)

        Button(btn_frame, text="Update", command=self.update,
               width=8).grid(row=0, column=1, padx=2)

        Button(btn_frame, text="Delete", command=self.delete_data,
               width=8).grid(row=0, column=2, padx=2)

        Button(btn_frame, text="Reset", command=self.reset,
               width=8).grid(row=0, column=3, padx=2)

        # ================= TABLE =================
        right = Frame(root, bd=2, relief=RIDGE)
        right.place(x=445, y=55, width=850, height=490)

        search_frame = LabelFrame(right, text="Search Customer")
        search_frame.pack(fill=X, padx=5, pady=5)

        ttk.Combobox(search_frame,
                     textvariable=self.var_search_by,
                     values=("Mobile", "Ref", "Name"),
                     state="readonly", width=12).grid(
                         row=0, column=0, padx=5, pady=5
                     )

        ttk.Entry(search_frame, textvariable=self.var_search,
                  width=25).grid(row=0, column=1, padx=5)

        Button(search_frame, text="Search",
               command=self.search_data).grid(row=0, column=2, padx=5)

        Button(search_frame, text="Show All",
               command=self.fetch_data).grid(row=0, column=3, padx=5)

        table_frame = Frame(right)
        table_frame.pack(fill=BOTH, expand=True)

        xscroll = ttk.Scrollbar(table_frame, orient=HORIZONTAL)
        yscroll = ttk.Scrollbar(table_frame, orient=VERTICAL)

        cols = ("ref", "name", "mother", "gender", "post",
                "mobile", "email", "nationality", "idproof",
                "idnumber", "address")

        self.customer_table = ttk.Treeview(
            table_frame, columns=cols, show="headings",
            xscrollcommand=xscroll.set,
            yscrollcommand=yscroll.set
        )

        xscroll.pack(side=BOTTOM, fill=X)
        yscroll.pack(side=RIGHT, fill=Y)

        xscroll.config(command=self.customer_table.xview)
        yscroll.config(command=self.customer_table.yview)

        headings = ("Ref", "Name", "Mother", "Gender", "Post Code",
                    "Mobile", "Email", "Nationality", "ID Proof",
                    "ID Number", "Address")

        for col, heading in zip(cols, headings):
            self.customer_table.heading(col, text=heading)
            self.customer_table.column(col, width=100)

        self.customer_table.pack(fill=BOTH, expand=True)
        self.customer_table.bind("<ButtonRelease-1>", self.get_cursor)

        self.lbl_status = Label(root, text="", fg="green",
                                font=("Arial", 10, "bold"))
        self.lbl_status.place(x=10, y=560, width=1280, height=25)

        self.fetch_data()

    # ================= DATABASE =================
    def connect_db(self):
        return mysql.connector.connect(
            host="localhost",
            username="root",
            password="dinomtp16",
            database="management"
        )

    def status(self, text, color="green"):
        self.lbl_status.config(text=text, fg=color)

    # ================= ADD =================
    def add_data(self):
        if not self.var_name.get() or not self.var_mobile.get():
            self.status("Name and Mobile are required!", "red")
            return

        try:
            conn = self.connect_db()
            cursor = conn.cursor()

            cursor.execute(
                "INSERT INTO customer VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    self.var_ref.get(), self.var_name.get(),
                    self.var_mother.get(), self.var_gender.get(),
                    self.var_post.get(), self.var_mobile.get(),
                    self.var_email.get(), self.var_nationality.get(),
                    self.var_idproof.get(), self.var_idnumber.get(),
                    self.var_address.get()
                )
            )

            conn.commit()
            cursor.close()
            conn.close()

            self.fetch_data()
            self.reset()
            self.status("Customer added successfully!")

        except Exception as e:
            self.status(str(e), "red")

    # ================= FETCH =================
    def fetch_data(self):
        try:
            conn = self.connect_db()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM customer")

            rows = cursor.fetchall()

            self.customer_table.delete(*self.customer_table.get_children())

            for row in rows:
                self.customer_table.insert("", END, values=row)

            cursor.close()
            conn.close()

            self.status("Customer data loaded!")

        except Exception as e:
            self.status(str(e), "red")

    # ================= GET CURSOR =================
    def get_cursor(self, event=None):
        selected = self.customer_table.focus()

        if selected:
            row = self.customer_table.item(selected, "values")

            variables = [
                self.var_ref, self.var_name, self.var_mother,
                self.var_gender, self.var_post, self.var_mobile,
                self.var_email, self.var_nationality,
                self.var_idproof, self.var_idnumber, self.var_address
            ]

            for var, value in zip(variables, row):
                var.set(value)

    # ================= UPDATE =================
    def update(self):
        if not self.var_ref.get():
            self.status("Select customer first!", "red")
            return

        try:
            conn = self.connect_db()
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE customer SET
                Name=%s, Mother=%s, Gender=%s, PostCode=%s,
                Mobile=%s, Email=%s, Nationality=%s,
                Idproof=%s, Idnumber=%s, Address=%s
                WHERE Ref=%s
            """, (
                self.var_name.get(), self.var_mother.get(),
                self.var_gender.get(), self.var_post.get(),
                self.var_mobile.get(), self.var_email.get(),
                self.var_nationality.get(), self.var_idproof.get(),
                self.var_idnumber.get(), self.var_address.get(),
                self.var_ref.get()
            ))

            conn.commit()
            cursor.close()
            conn.close()

            self.fetch_data()
            self.status("Customer updated successfully!")

        except Exception as e:
            self.status(str(e), "red")

    # ================= DELETE =================
    def delete_data(self):
        if not self.var_ref.get():
            self.status("Select customer first!", "red")
            return

        try:
            conn = self.connect_db()
            cursor = conn.cursor()

            cursor.execute("DELETE FROM customer WHERE Ref=%s",
                           (self.var_ref.get(),))

            conn.commit()
            cursor.close()
            conn.close()

            self.fetch_data()
            self.reset()
            self.status("Customer deleted successfully!")

        except Exception as e:
            self.status(str(e), "red")

    # ================= SEARCH =================
    def search_data(self):
        field = self.var_search_by.get()
        keyword = self.var_search.get()

        try:
            conn = self.connect_db()
            cursor = conn.cursor()

            cursor.execute(
                f"SELECT * FROM customer WHERE {field} LIKE %s",
                (f"%{keyword}%",)
            )

            rows = cursor.fetchall()

            self.customer_table.delete(*self.customer_table.get_children())

            for row in rows:
                self.customer_table.insert("", END, values=row)

            cursor.close()
            conn.close()

            self.status(f"Found {len(rows)} customer(s)!")

        except Exception as e:
            self.status(str(e), "red")

    # ================= RESET =================
    def reset(self):
        self.var_ref.set(str(random.randint(1000, 9999)))

        for var in (
            self.var_name, self.var_mother, self.var_post,
            self.var_mobile, self.var_email, self.var_idnumber,
            self.var_address
        ):
            var.set("")

        self.var_gender.set("Male")
        self.var_nationality.set("VietNam")
        self.var_idproof.set("CCCD")
