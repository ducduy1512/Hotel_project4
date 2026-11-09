
from tkinter import *
from tkinter import ttk
import mysql.connector


class DetailsRoom:
    def __init__(self, root):
        self.root = root

        self.var_floor = StringVar()
        self.var_RoomNo = StringVar()
        self.var_RoomType = StringVar(value="Single")

        Label(root, text="ROOM DETAILS",
              font=("Times New Roman", 18, "bold"),
              bg="black", fg="gold").place(
                  x=0, y=0, width=1310, height=45
              )

        # ================= FORM =================
        form = LabelFrame(root, text="New Room Add")
        form.place(x=10, y=55, width=400, height=250)

        Label(form, text="Floor").grid(row=0, column=0, padx=10, pady=10)
        ttk.Entry(form, textvariable=self.var_floor).grid(row=0, column=1)

        Label(form, text="Room No").grid(row=1, column=0, padx=10, pady=10)
        ttk.Entry(form, textvariable=self.var_RoomNo).grid(row=1, column=1)

        Label(form, text="Room Type").grid(row=2, column=0, padx=10, pady=10)

        ttk.Combobox(form, textvariable=self.var_RoomType,
                     values=("Single", "Double", "Luxury"),
                     state="readonly").grid(row=2, column=1)

        # ================= BUTTONS =================
        btn_frame = Frame(form)
        btn_frame.place(x=5, y=170, width=385, height=35)

        Button(btn_frame, text="Add", command=self.add_data,
               width=8).grid(row=0, column=0, padx=2)

        Button(btn_frame, text="Update", command=self.update,
               width=8).grid(row=0, column=1, padx=2)

        Button(btn_frame, text="Delete", command=self.delete_data,
               width=8).grid(row=0, column=2, padx=2)

        Button(btn_frame, text="Reset", command=self.reset,
               width=8).grid(row=0, column=3, padx=2)

        # ================= TABLE =================
        table_frame = LabelFrame(root, text="Show Room Details")
        table_frame.place(x=425, y=55, width=870, height=480)

        scroll_y = ttk.Scrollbar(table_frame, orient=VERTICAL)
        scroll_x = ttk.Scrollbar(table_frame, orient=HORIZONTAL)

        self.room_table = ttk.Treeview(
            table_frame,
            columns=("floor", "roomno", "roomType"),
            show="headings",
            yscrollcommand=scroll_y.set,
            xscrollcommand=scroll_x.set
        )

        scroll_y.pack(side=RIGHT, fill=Y)
        scroll_x.pack(side=BOTTOM, fill=X)

        scroll_y.config(command=self.room_table.yview)
        scroll_x.config(command=self.room_table.xview)

        self.room_table.heading("floor", text="Floor")
        self.room_table.heading("roomno", text="Room No")
        self.room_table.heading("roomType", text="Room Type")

        self.room_table.column("floor", width=150)
        self.room_table.column("roomno", width=150)
        self.room_table.column("roomType", width=150)

        self.room_table.pack(fill=BOTH, expand=True)
        self.room_table.bind("<ButtonRelease-1>", self.get_cursor)

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
        if not self.var_floor.get() or not self.var_RoomNo.get():
            self.status("Floor and Room No are required!", "red")
            return

        try:
            conn = self.connect_db()
            cursor = conn.cursor()

            cursor.execute(
                "INSERT INTO details VALUES (%s,%s,%s)",
                (self.var_floor.get(), self.var_RoomNo.get(),
                 self.var_RoomType.get())
            )

            conn.commit()
            cursor.close()
            conn.close()

            self.fetch_data()
            self.reset()
            self.status("Room added successfully!")

        except Exception as e:
            self.status(str(e), "red")

    # ================= FETCH =================
    def fetch_data(self):
        try:
            conn = self.connect_db()
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM details")
            rows = cursor.fetchall()

            self.room_table.delete(*self.room_table.get_children())

            for row in rows:
                self.room_table.insert("", END, values=row)

            cursor.close()
            conn.close()

            self.status("Room data loaded!")

        except Exception as e:
            self.status(str(e), "red")

    # ================= GET CURSOR =================
    def get_cursor(self, event=None):
        selected = self.room_table.focus()

        if selected:
            row = self.room_table.item(selected, "values")

            self.var_floor.set(row[0])
            self.var_RoomNo.set(row[1])
            self.var_RoomType.set(row[2])

    # ================= UPDATE =================
    def update(self):
        if not self.var_RoomNo.get():
            self.status("Select room first!", "red")
            return

        try:
            conn = self.connect_db()
            cursor = conn.cursor()

            cursor.execute(
                "UPDATE details SET Floor=%s, RoomType=%s WHERE RoomNo=%s",
                (self.var_floor.get(), self.var_RoomType.get(),
                 self.var_RoomNo.get())
            )

            conn.commit()
            cursor.close()
            conn.close()

            self.fetch_data()
            self.status("Room updated successfully!")

        except Exception as e:
            self.status(str(e), "red")

    # ================= DELETE =================
    def delete_data(self):
        if not self.var_RoomNo.get():
            self.status("Select room first!", "red")
            return

        try:
            conn = self.connect_db()
            cursor = conn.cursor()

            cursor.execute("DELETE FROM details WHERE RoomNo=%s",
                           (self.var_RoomNo.get(),))

            conn.commit()
            cursor.close()
            conn.close()

            self.fetch_data()
            self.reset()
            self.status("Room deleted successfully!")

        except Exception as e:
            self.status(str(e), "red")

    # ================= RESET =================
    def reset(self):
        self.var_floor.set("")
        self.var_RoomNo.set("")
        self.var_RoomType.set("Single")
