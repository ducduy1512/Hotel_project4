HOTEL PROJECT 5 — FULL PACKAGE (CUSTOMER ROOM TYPE CARDS INCLUDED)

This is the complete project based on the latest ZIP supplied in this conversation.
The Customer Portal card layout and supporting API summary have been integrated.

CUSTOMER PORTAL UPDATES
- Replaces the room-type dropdown with room-type cards.
- Four room types (Standard, Deluxe, VIP and Family) appear in a 2-column x 2-row
  gallery on normal desktop/tablet screens.
- Each card contains a large empty image area reserved for photos to be added later.
- Each card shows the room type name, nightly base price, maximum capacity, room
  count and default services currently configured on rooms of that type.
- Service summaries show how many rooms provide each service and the quantity
  range where quantities differ between rooms.
- The customer selects a room-type card first, then chooses check-in/check-out
  dates and searches only available rooms of the selected type.
- Selecting a specific room still loads that room's exact default services. The
  customer can customize selections and quantities before confirming a booking.
- The existing customer booking endpoint and stored procedure continue to save
  the selected services with the booking. No database schema migration is added.

PYCHARM STARTUP
1. Open Hotel_Project5_HTML5_GUI/Hotel_project5 in PyCharm.
2. Select the project interpreter: .venv/Scripts/python.exe.
3. Open app.py and click Run.
4. Keep the PyCharm Run window open while using the website.
5. Open http://127.0.0.1:8000/ in Microsoft Edge or Chrome.
6. API documentation is available at http://127.0.0.1:8000/docs.

If the bundled virtual environment is not valid on another computer, create a new
PyCharm virtual environment and run: python -m pip install -r requirements.txt

DATABASE
- Existing MySQL configuration is read from the project .env file.
- Check DB_HOST, DB_USER, DB_PASSWORD, DB_NAME and DB_PORT before starting.
- The card service summary reads dichvu rows with booking_id IS NULL and a
  non-null phong_id. The individual-room service endpoint is unchanged.

NOTES
- No room photos were inserted; the image areas are intentionally placeholders.
- The 2-column layout is retained on narrow screens as requested; card spacing and text size reduce on small displays.
- Run booking/payment/invoice tests against the local MySQL database before
  submission. This ZIP cannot include a live database server or user data.
