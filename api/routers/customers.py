
# api/routers/customers.py

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from mysql.connector import Error, IntegrityError

from api.database import get_db

router = APIRouter(
    prefix="/api/customers",
    tags=["Customers"]
)


# Dữ liệu nhận khi thêm khách hàng
class CustomerCreate(BaseModel):
    ho_ten: str = Field(min_length=1, max_length=100)
    cccd: str = Field(min_length=1, max_length=20)
    sdt: str = Field(min_length=1, max_length=20)


# Dữ liệu nhận khi cập nhật khách hàng
class CustomerUpdate(BaseModel):
    ho_ten: str = Field(min_length=1, max_length=100)
    cccd: str = Field(min_length=1, max_length=20)
    sdt: str = Field(min_length=1, max_length=20)


# 1. Lấy danh sách khách hàng
@router.get("/")
def get_customers(db=Depends(get_db)):
    cursor = db.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT id, ho_ten, cccd, sdt
            FROM khach
            ORDER BY id
        """)

        return cursor.fetchall()

    except Error as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cursor.close()


# 2. Xem chi tiết khách hàng
@router.get("/{customer_id}")
def get_customer(customer_id: int, db=Depends(get_db)):
    cursor = db.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT id, ho_ten, cccd, sdt
            FROM khach
            WHERE id = %s
        """, (customer_id,))

        customer = cursor.fetchone()

        if customer is None:
            raise HTTPException(
                status_code=404,
                detail="Không tìm thấy khách hàng"
            )

        return customer

    except Error as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cursor.close()


# 3. Thêm khách hàng
@router.post("/", status_code=201)
def create_customer(
    customer: CustomerCreate,
    db=Depends(get_db)
):
    cursor = db.cursor(dictionary=True)

    try:
        cursor.execute("""
            INSERT INTO khach (ho_ten, cccd, sdt)
            VALUES (%s, %s, %s)
        """, (
            customer.ho_ten.strip(),
            customer.cccd.strip(),
            customer.sdt.strip()
        ))

        db.commit()
        new_id = cursor.lastrowid

        cursor.execute("""
            SELECT id, ho_ten, cccd, sdt
            FROM khach
            WHERE id = %s
        """, (new_id,))

        return {
            "message": "Thêm khách hàng thành công",
            "customer": cursor.fetchone()
        }

    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="CCCD hoặc số điện thoại đã tồn tại."
        )

    except Error as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cursor.close()


# 4. Cập nhật khách hàng
@router.put("/{customer_id}")
def update_customer(
    customer_id: int,
    customer: CustomerUpdate,
    db=Depends(get_db)
):
    cursor = db.cursor(dictionary=True)

    try:
        cursor.execute(
            "SELECT id FROM khach WHERE id = %s",
            (customer_id,)
        )

        if cursor.fetchone() is None:
            raise HTTPException(
                status_code=404,
                detail="Không tìm thấy khách hàng"
            )

        cursor.execute("""
            UPDATE khach
            SET ho_ten = %s,
                cccd = %s,
                sdt = %s
            WHERE id = %s
        """, (
            customer.ho_ten.strip(),
            customer.cccd.strip(),
            customer.sdt.strip(),
            customer_id
        ))

        db.commit()

        cursor.execute("""
            SELECT id, ho_ten, cccd, sdt
            FROM khach
            WHERE id = %s
        """, (customer_id,))

        return {
            "message": "Cập nhật khách hàng thành công",
            "customer": cursor.fetchone()
        }

    except HTTPException:
        raise

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="CCCD hoặc số điện thoại đã được sử dụng."
        )

    except Error as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cursor.close()


# 5. Xóa khách hàng
@router.delete("/{customer_id}")
def delete_customer(
    customer_id: int,
    db=Depends(get_db)
):
    cursor = db.cursor()

    try:
        cursor.execute(
            "SELECT id FROM khach WHERE id = %s",
            (customer_id,)
        )

        if cursor.fetchone() is None:
            raise HTTPException(
                status_code=404,
                detail="Không tìm thấy khách hàng"
            )

        cursor.execute(
            "DELETE FROM khach WHERE id = %s",
            (customer_id,)
        )

        db.commit()

        return {
            "message": "Xóa khách hàng thành công",
            "customer_id": customer_id
        }

    except HTTPException:
        raise

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Không thể xóa khách hàng vì đang có booking liên quan."
        )

    except Error as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cursor.close()
