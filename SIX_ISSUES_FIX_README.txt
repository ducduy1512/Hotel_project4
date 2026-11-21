HOTEL PROJECT – SIX ISSUES FIX

1) BACK UP hotel_management_erd before applying any changes.
2) This script is tailored to the uploaded hotel_management_full(2).sql snapshot.
   It normalizes snapshot JSON for Booking 7 and 12 and repairs the empty JSON snapshot for Booking 19.
   Review these IDs/dates/prices first if your current database data differs.
3) Open Hotel_Six_Issues_Fix.sql in MySQL Workbench, select hotel_management_erd, and execute the whole script once.
4) Then execute Hotel_TestCase.sql and review all invalid_count / invalid_pair_count values.
5) The patch does not DROP tables or change pay.so_tien, pay.status, hoadon.tong_tien, or payment methods.
6) The script drops obsolete surcharge recalculation triggers and installs the canonical 15 guard triggers. It also recreates the payment/invoice procedure so it inserts an invoice explicitly (no dependency on the removed trg_pay_after_insert).

For a fresh install, use Hotel_Complete.sql OR the split SQL files. Do not run this snapshot-specific reconciliation patch on unrelated datasets.
