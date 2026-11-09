
from tkinter import *
from PIL import Image, ImageTk
import os

from Customer import Cust_Win
from Room import Roombooking
from Details import DetailsRoom


class HotelManagementSystem:
    def __init__(self, root):
        self.root = root
        self.root.title("Hotel Management System")
        self.root.geometry("1550x800+0+0")

        base_path = os.path.dirname(os.path.abspath(__file__))
        img_path = os.path.join(base_path, "images")

        # ================= HEADER =================
        try:
            img = Image.open(os.path.join(img_path, "hotel1.png"))
            img = img.resize((1550, 140), Image.LANCZOS)
            self.photoimg1 = ImageTk.PhotoImage(img)

            Label(self.root, image=self.photoimg1).place(
                x=0, y=0, width=1550, height=140
            )
        except:
            Label(self.root, text="HOTEL MANAGEMENT SYSTEM",
                  font=("Times New Roman", 30, "bold"),
                  bg="lightgray").place(
                      x=0, y=0, width=1550, height=140
                  )

        # ================= TITLE =================
        Label(self.root, text="HOTEL MANAGEMENT SYSTEM",
              font=("Times New Roman", 30, "bold"),
              bg="white", fg="black").place(
                  x=0, y=140, width=1550, height=50
              )

        # ================= MAIN FRAME =================
        self.main_frame = Frame(self.root, bd=2, relief=RIDGE)
        self.main_frame.place(x=0, y=190, width=1550, height=610)

        # ================= MENU LEFT =================
        menu_frame = Frame(self.main_frame, bd=2, relief=RIDGE, bg="black")
        menu_frame.place(x=0, y=0, width=230, height=606)

        Label(menu_frame, text="MENU",
              font=("Times New Roman", 20, "bold"),
              bg="black", fg="gold").place(
                  x=0, y=0, width=225, height=40
              )

        btn_frame = Frame(menu_frame, bg="black")
        btn_frame.place(x=5, y=45, width=220, height=300)

        Button(btn_frame, text="CUSTOMER",
               command=lambda: self.show_page(Cust_Win),
               font=("Arial", 13, "bold"),
               bg="black", fg="gold").grid(
                   row=0, column=0, sticky="ew", pady=5, ipady=8
               )

        Button(btn_frame, text="ROOM BOOKING",
               command=lambda: self.show_page(Roombooking),
               font=("Arial", 13, "bold"),
               bg="black", fg="gold").grid(
                   row=1, column=0, sticky="ew", pady=5, ipady=8
               )

        Button(btn_frame, text="ROOM DETAILS",
               command=lambda: self.show_page(DetailsRoom),
               font=("Arial", 13, "bold"),
               bg="black", fg="gold").grid(
                   row=2, column=0, sticky="ew", pady=5, ipady=8
               )

        Button(btn_frame, text="HOME",
               command=self.show_home,
               font=("Arial", 13, "bold"),
               bg="black", fg="gold").grid(
                   row=3, column=0, sticky="ew", pady=5, ipady=8
               )

        Button(btn_frame, text="LOGOUT",
               command=self.root.destroy,
               font=("Arial", 13, "bold"),
               bg="black", fg="gold").grid(
                   row=4, column=0, sticky="ew", pady=5, ipady=8
               )

        btn_frame.grid_columnconfigure(0, weight=1)

        # ================= CONTENT FRAME =================
        self.content_frame = Frame(self.main_frame, bg="white", bd=1, relief=RIDGE)
        self.content_frame.place(x=232, y=0, width=1312, height=606)

        self.show_home()

    # ================= SHOW PAGE =================
    def show_page(self, page_class):
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        page_class(self.content_frame)

    # ================= HOME =================
    def show_home(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        Label(self.content_frame,
              text="WELCOME TO HOTEL MANAGEMENT SYSTEM",
              font=("Times New Roman", 25, "bold"),
              bg="white", fg="black").pack(expand=True)


if __name__ == "__main__":
    root = Tk()
    obj = HotelManagementSystem(root)
    root.mainloop()
