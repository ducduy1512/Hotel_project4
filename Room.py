from tkinter import *
from PIL import Image, ImageTk
from tkinter import ttk
from tkinter import messagebox
import os
import mysql.connector
from datetime import datetime


class Roombooking:
    def __init__(self, root):
        self.root = root
        self.root.title("Hotel Management System")
        self.root.geometry("1295x550+230+220")

        # ================== Variables ==================
        self.var_contact = StringVar()
        self.var_checkin = StringVar()
        self.var_checkout = StringVar()
        self.var_roomtype = StringVar()
        self.var_roomavailable = StringVar()
        self.var_meal = StringVar()
        self.var_noofdays = StringVar()
        self.var_paidtax = StringVar()
        self.var_actualtotal = StringVar()
        self.var_total = StringVar()

        self.search_var = StringVar()
        self.txt_search = StringVar()

        # ================== Title ==================
        lbl_title = Label(self.root, text="ROOM BOOKING DETAILS",
                          font=("times new roman", 18, "bold"),
                          bg="black", fg="gold", bd=4, relief=RIDGE)
        lbl_title.place(x=0, y=0, width=1295, height=50)

        # ================== Logo ==================
        base_path = os.path.dirname(os.path.abspath(__file__))
        img_path = os.path.join(base_path, "images")

        try:
            img2 = Image.open(os.path.join(img_path, "logohotel.png"))
            img2 = img2.resize((100, 40), Image.LANCZOS)
            self.photoimg2 = ImageTk.PhotoImage(img2)

            lblimg = Label(self.root, image=self.photoimg2, bd=0, relief=RIDGE)
            lblimg.place(x=5, y=2, width=100, height=40)
        except:
            pass

        # ================== LabelFrame Left ==================
        labelframeleft = LabelFrame(self.root, bd=2, relief=RIDGE, text="Room Booking Details",
                                    font=("times new roman", 12, "bold"), padx=2)
        labelframeleft.place(x=5, y=50, width=425, height=490)

        # Customer Contact
        lbl_cust_contact = Label(labelframeleft, text="Customer Contact", font=("arial", 12, "bold"), padx=2, pady=6)
        lbl_cust_contact.grid(row=0, column=0, sticky=W)

        enty_contact = ttk.Entry(labelframeleft, textvariable=self.var_contact,
                                 font=("arial", 13, "bold"), width=20)
        enty_contact.grid(row=0, column=1, sticky=W)

        btnFetchData = Button(labelframeleft, command=self.Fetch_contact, text="Fetch Data",
                              font=("arial", 8, "bold"), bg="black", fg="gold", width=9)
        btnFetchData.place(x=347, y=4)

        # Check_in Date
        check_in_date = Label(labelframeleft, font=("arial", 12, "bold"), text="Check_in Date:", padx=2, pady=6)
        check_in_date.grid(row=1, column=0, sticky=W)
        txtcheck_in_date = ttk.Entry(labelframeleft, textvariable=self.var_checkin,
                                     font=("arial", 13, "bold"), width=29)
        txtcheck_in_date.grid(row=1, column=1)

        # Check_out Date
        lbl_Check_out = Label(labelframeleft, font=("arial", 12, "bold"), text="Check_Out Date:", padx=2, pady=6)
        lbl_Check_out.grid(row=2, column=0, sticky=W)
        txt_Check_out = ttk.Entry(labelframeleft, textvariable=self.var_checkout,
                                  font=("arial", 13, "bold"), width=29)
        txt_Check_out.grid(row=2, column=1)

        # Room Type
        label_RoomType = Label(labelframeleft, font=("arial", 12, "bold"), text="Room Type:", padx=2, pady=6)
        label_RoomType.grid(row=3, column=0, sticky=W)

        combo_RoomType = ttk.Combobox(labelframeleft, textvariable=self.var_roomtype,
                                      font=("arial", 12, "bold"), width=27, state="readonly")
        combo_RoomType["value"] = ("Single", "Double", "Luxury")
        combo_RoomType.current(0)
        combo_RoomType.grid(row=3, column=1)

        # Available Room
        lblRoomAvailable = Label(labelframeleft, font=("arial", 12, "bold"), text="Available Room:", padx=2, pady=6)
        lblRoomAvailable.grid(row=4, column=0, sticky=W)
        txtRoomAvailable = ttk.Entry(labelframeleft, textvariable=self.var_roomavailable,
                                     font=("arial", 13, "bold"), width=29)
        txtRoomAvailable.grid(row=4, column=1)

        # Meal
        lblMeal = Label(labelframeleft, font=("arial", 12, "bold"), text="Meal:", padx=2, pady=6)
        lblMeal.grid(row=5, column=0, sticky=W)
        txtMeal = ttk.Entry(labelframeleft, textvariable=self.var_meal,
                            font=("arial", 13, "bold"), width=29)
        txtMeal.grid(row=5, column=1)

        # No Of Days
        lblNoOfDays = Label(labelframeleft, font=("arial", 12, "bold"), text="No Of Days:", padx=2, pady=6)
        lblNoOfDays.grid(row=6, column=0, sticky=W)
        txtNoOfDays = ttk.Entry(labelframeleft, textvariable=self.var_noofdays,
                                font=("arial", 13, "bold"), width=29)
        txtNoOfDays.grid(row=6, column=1)

        # Paid Tax
        lblPaidTax = Label(labelframeleft, font=("arial", 12, "bold"), text="Paid Tax:", padx=2, pady=6)
        lblPaidTax.grid(row=7, column=0, sticky=W)
        txtPaidTax = ttk.Entry(labelframeleft, textvariable=self.var_paidtax,
                               font=("arial", 13, "bold"), width=29)
        txtPaidTax.grid(row=7, column=1)

        # Sub Total
        lblSubTotal = Label(labelframeleft, font=("arial", 12, "bold"), text="Sub Total:", padx=2, pady=6)
        lblSubTotal.grid(row=8, column=0, sticky=W)
        txtSubTotal = ttk.Entry(labelframeleft, textvariable=self.var_actualtotal,
                                font=("arial", 13, "bold"), width=29)
        txtSubTotal.grid(row=8, column=1)

        # Total Cost
        lblTotal = Label(labelframeleft, font=("arial", 12, "bold"), text="Total Cost:", padx=2, pady=6)
        lblTotal.grid(row=9, column=0, sticky=W)
        txtTotal = ttk.Entry(labelframeleft, textvariable=self.var_total,
                             font=("arial", 13, "bold"), width=29)
        txtTotal.grid(row=9, column=1)

        # Bill Button
        btnBill = Button(labelframeleft, text="Bill", command=self.total,
                         font=("arial", 11, "bold"), bg="black", fg="gold", width=10)
        btnBill.grid(row=10, column=0, padx=1, sticky=W)

        # ================== Buttons ==================
        btn_frame = Frame(labelframeleft, bd=2, relief=RIDGE)
        btn_frame.place(x=0, y=400, width=412, height=40)

        btnAdd = Button(btn_frame, text="Add", command=self.add_data,
                        font=("arial", 11, "bold"), bg="black", fg="gold", width=10)
        btnAdd.grid(row=0, column=0, padx=1)

        btnUpdate = Button(btn_frame, text="Update", command=self.update,
                           font=("arial", 11, "bold"), bg="black", fg="gold", width=10)
        btnUpdate.grid(row=0, column=1, padx=1)

        btnDelete = Button(btn_frame, text="Delete", command=self.mDelete,
                           font=("arial", 11, "bold"), bg="black", fg="gold", width=10)
        btnDelete.grid(row=0, column=2, padx=1)

        btnReset = Button(btn_frame, text="Reset", command=self.reset,
                          font=("arial", 11, "bold"), bg="black", fg="gold", width=10)
        btnReset.grid(row=0, column=3, padx=1)

        # ================== Right side image ==================
        try:
            img3 = Image.open(os.path.join(img_path, "bedroom1.jpg"))
            img3 = img3.resize((520, 200), Image.LANCZOS)
            self.photoimg3 = ImageTk.PhotoImage(img3)

            lblimg3 = Label(self.root, image=self.photoimg3, bd=0, relief=RIDGE)
            lblimg3.place(x=760, y=55, width=520, height=200)
        except:
            pass

        # ================== Table Frame ==================
        Table_Frame = LabelFrame(self.root, bd=2, relief=RIDGE,
                                 text="View Details And Search System",
                                 font=("arial", 12, "bold"))
        Table_Frame.place(x=435, y=280, width=860, height=260)

        lblSearchBy = Label(Table_Frame, font=("arial", 12, "bold"),
                            text="Search By:", bg="red", fg="white")
        lblSearchBy.grid(row=0, column=0, sticky=W, padx=2)

        self.combo_Search = ttk.Combobox(Table_Frame, textvariable=self.search_var,
                                         font=("arial", 12, "bold"), width=24, state="readonly")
        self.combo_Search["value"] = ("Contact", "Room")
        self.combo_Search.current(0)
        self.combo_Search.grid(row=0, column=1, padx=2)

        self.txtSearch = ttk.Entry(Table_Frame, textvariable=self.txt_search,
                                   font=("arial", 13, "bold"), width=24)
        self.txtSearch.grid(row=0, column=2, padx=2)

        btnSearch = Button(Table_Frame, text="Search", command=self.search,
                           font=("arial", 11, "bold"), bg="black", fg="gold", width=10)
        btnSearch.grid(row=0, column=3, padx=1)

        btnShowAll = Button(Table_Frame, text="Show All", command=self.fetch_data,
                            font=("arial", 11, "bold"), bg="black", fg="gold", width=10)
        btnShowAll.grid(row=0, column=4, padx=1)

        # ================== Show data Table ==================
        details_table = Frame(Table_Frame, bd=2, relief=RIDGE)
        details_table.place(x=0, y=50, width=860, height=180)

        scroll_x = ttk.Scrollbar(details_table, orient=HORIZONTAL)
        scroll_y = ttk.Scrollbar(details_table, orient=VERTICAL)

        self.room_table = ttk.Treeview(details_table,
                                       columns=("contact", "checkin", "checkout", "roomtype",
                                                "roomavailable", "meal", "noOfdays"),
                                       xscrollcommand=scroll_x.set,
                                       yscrollcommand=scroll_y.set)

        scroll_x.pack(side=BOTTOM, fill=X)
        scroll_y.pack(side=RIGHT, fill=Y)

        scroll_x.config(command=self.room_table.xview)
        scroll_y.config(command=self.room_table.yview)

        self.room_table.heading("contact", text="Contact")
        self.room_table.heading("checkin", text="Check-in")
        self.room_table.heading("checkout", text="Check-out")
        self.room_table.heading("roomtype", text="Room Type")
        self.room_table.heading("roomavailable", text="Room No")
        self.room_table.heading("meal", text="Meal")
        self.room_table.heading("noOfdays", text="NoOfDays")

        self.room_table["show"] = "headings"

        for col in ("contact", "checkin", "checkout", "roomtype", "roomavailable", "meal", "noOfdays"):
            self.room_table.column(col, width=100)

        self.room_table.pack(fill=BOTH, expand=1)
        self.room_table.bind("<ButtonRelease-1>", self.get_cursor)

        self.fetch_data()

    # ================== Functions ==================

    def Fetch_contact(self):
        if self.var_contact.get() == "":
            messagebox.showerror("Error", "Please enter Contact Number", parent=self.root)
            return

        try:
            conn = mysql.connector.connect(
                host="localhost",
                username="root",
                password="dinomtp16",
                database="management"
            )
            my_cursor = conn.cursor()
            query = "SELECT Name, Gender, Email, Nationality, Address FROM customer WHERE Mobile=%s"
            value = (self.var_contact.get(),)
            my_cursor.execute(query, value)
            row = my_cursor.fetchone()

            if row is None:
                messagebox.showerror("Error", "This number Not Found", parent=self.root)
            else:
                showDataframe = Frame(self.root, bd=4, relief=RIDGE, padx=2)
                showDataframe.place(x=455, y=55, width=300, height=180)

                Label(showDataframe, text="Name:", font=("arial", 12, "bold")).place(x=0, y=0)
                Label(showDataframe, text=row[0], font=("arial", 12, "bold")).place(x=90, y=0)

                Label(showDataframe, text="Gender:", font=("arial", 12, "bold")).place(x=0, y=30)
                Label(showDataframe, text=row[1], font=("arial", 12, "bold")).place(x=90, y=30)

                Label(showDataframe, text="Email:", font=("arial", 12, "bold")).place(x=0, y=60)
                Label(showDataframe, text=row[2], font=("arial", 12, "bold")).place(x=90, y=60)

                Label(showDataframe, text="Nationality:", font=("arial", 12, "bold")).place(x=0, y=90)
                Label(showDataframe, text=row[3], font=("arial", 12, "bold")).place(x=90, y=90)

                Label(showDataframe, text="Address:", font=("arial", 12, "bold")).place(x=0, y=120)
                Label(showDataframe, text=row[4], font=("arial", 12, "bold")).place(x=90, y=120)

            conn.close()
        except Exception as es:
            messagebox.showerror("Error", f"Error:\n{str(es)}", parent=self.root)

    def total(self):
        try:
            inDate = datetime.strptime(self.var_checkin.get(), "%d/%m/%Y")
            outDate = datetime.strptime(self.var_checkout.get(), "%d/%m/%Y")
            self.var_noofdays.set(abs((outDate - inDate).days))

            if self.var_meal.get() == "BreakFast" and self.var_roomtype.get() == "Single":
                q1 = float(300)
                q2 = float(700)
            elif self.var_meal.get() == "Lunch" and self.var_roomtype.get() == "Double":
                q1 = float(300)
                q2 = float(1200)
            else:
                q1 = float(200)
                q2 = float(1000)

            q3 = float(self.var_noofdays.get())
            q4 = float(q1 + q2)
            q5 = float(q3 * q4)

            Tax = "Rs." + str("%.2f" % (q5 * 0.1))
            ST = "Rs." + str("%.2f" % q5)
            TT = "Rs." + str("%.2f" % (q5 + (q5 * 0.1)))

            self.var_paidtax.set(Tax)
            self.var_actualtotal.set(ST)
            self.var_total.set(TT)

        except Exception as es:
            messagebox.showerror("Error", f"Please enter correct Date format (dd/mm/yyyy)\n{str(es)}", parent=self.root)

    def add_data(self):
        if self.var_contact.get() == "" or self.var_checkin.get() == "":
            messagebox.showerror("Error", "All fields are required", parent=self.root)
        else:
            try:
                conn = mysql.connector.connect(
                    host="localhost",
                    username="root",
                    password="dinomtp16",
                    database="management"
                )
                my_cursor = conn.cursor()
                my_cursor.execute(
                    "INSERT INTO room VALUES (%s,%s,%s,%s,%s,%s,%s)",
                    (
                        self.var_contact.get(),
                        self.var_checkin.get(),
                        self.var_checkout.get(),
                        self.var_roomtype.get(),
                        self.var_roomavailable.get(),
                        self.var_meal.get(),
                        self.var_noofdays.get(),
                    )
                )
                conn.commit()
                self.fetch_data()
                conn.close()
                messagebox.showinfo("Success", "Room Booked successfully", parent=self.root)
            except Exception as es:
                messagebox.showerror("Error", f"Something went wrong:\n{str(es)}", parent=self.root)

    def fetch_data(self):
        try:
            conn = mysql.connector.connect(
                host="localhost",
                username="root",
                password="dinomtp16",
                database="management"
            )
            my_cursor = conn.cursor()
            my_cursor.execute("SELECT * FROM room")
            rows = my_cursor.fetchall()

            if len(rows) != 0:
                self.room_table.delete(*self.room_table.get_children())
                for row in rows:
                    self.room_table.insert("", END, values=row)
            conn.close()
        except Exception as es:
            messagebox.showerror("Error", f"Cannot fetch data:\n{str(es)}", parent=self.root)

    def get_cursor(self, event=""):
        cursor_row = self.room_table.focus()
        content = self.room_table.item(cursor_row)
        row = content["values"]

        if row:
            self.var_contact.set(row[0])
            self.var_checkin.set(row[1])
            self.var_checkout.set(row[2])
            self.var_roomtype.set(row[3])
            self.var_roomavailable.set(row[4])
            self.var_meal.set(row[5])
            self.var_noofdays.set(row[6])

    def update(self):
        if self.var_contact.get() == "":
            messagebox.showerror("Error", "Please enter contact number", parent=self.root)
        else:
            try:
                conn = mysql.connector.connect(
                    host="localhost",
                    username="root",
                    password="dinomtp16",
                    database="management"
                )
                my_cursor = conn.cursor()
                my_cursor.execute(
                    """UPDATE room SET check_in=%s, check_out=%s, roomtype=%s, 
                       roomavailable=%s, meal=%s, noOfdays=%s 
                       WHERE Contact=%s""",
                    (
                        self.var_checkin.get(),
                        self.var_checkout.get(),
                        self.var_roomtype.get(),
                        self.var_roomavailable.get(),
                        self.var_meal.get(),
                        self.var_noofdays.get(),
                        self.var_contact.get(),
                    )
                )
                conn.commit()
                self.fetch_data()
                conn.close()
                messagebox.showinfo("Update", "Room details has been updated successfully", parent=self.root)
            except Exception as es:
                messagebox.showerror("Error", f"Something went wrong:\n{str(es)}", parent=self.root)

    def mDelete(self):
        if self.var_contact.get() == "":
            messagebox.showerror("Error", "Please select a record to delete", parent=self.root)
            return

        mDelete = messagebox.askyesno("Hotel Management System",
                                      "Do you really want to delete this room booking?", parent=self.root)
        if mDelete:
            try:
                conn = mysql.connector.connect(
                    host="localhost",
                    username="root",
                    password="dinomtp16",
                    database="management"
                )
                my_cursor = conn.cursor()
                query = "DELETE FROM room WHERE Contact=%s"
                value = (self.var_contact.get(),)
                my_cursor.execute(query, value)
                conn.commit()
                self.fetch_data()
                conn.close()
                messagebox.showinfo("Delete", "Room booking has been deleted successfully", parent=self.root)
                self.reset()
            except Exception as es:
                messagebox.showerror("Error", f"Something went wrong:\n{str(es)}", parent=self.root)

    def reset(self):
        self.var_contact.set("")
        self.var_checkin.set("")
        self.var_checkout.set("")
        self.var_roomtype.set("Single")
        self.var_roomavailable.set("")
        self.var_meal.set("")
        self.var_noofdays.set("")
        self.var_paidtax.set("")
        self.var_actualtotal.set("")
        self.var_total.set("")

    def search(self):
        try:
            conn = mysql.connector.connect(
                host="localhost",
                username="root",
                password="dinomtp16",
                database="management"
            )
            my_cursor = conn.cursor()

            search_by = self.search_var.get()
            search_txt = self.txt_search.get()

            if search_by == "Contact":
                my_cursor.execute("SELECT * FROM room WHERE Contact LIKE %s", ('%' + search_txt + '%',))
            elif search_by == "Room":
                my_cursor.execute("SELECT * FROM room WHERE roomavailable LIKE %s", ('%' + search_txt + '%',))
            else:
                messagebox.showerror("Error", "Please select search type", parent=self.root)
                return

            rows = my_cursor.fetchall()
            if len(rows) != 0:
                self.room_table.delete(*self.room_table.get_children())
                for row in rows:
                    self.room_table.insert("", END, values=row)
            else:
                messagebox.showinfo("Info", "No record found", parent=self.root)

            conn.close()
        except Exception as es:
            messagebox.showerror("Error", f"Search error:\n{str(es)}", parent=self.root)


if __name__ == "__main__":
    root = Tk()
    obj = Roombooking(root)
    root.mainloop()