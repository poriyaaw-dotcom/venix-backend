# app/services/payment_service.py
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from decimal import Decimal

from app.models.order import Order, OrderStatus
from app.models.payment import Payment, PaymentStatus
from app.integrations.payment_gateway import payment_gateway
from app.services.inventory_service import check_and_deduct_stock

def initiate_payment(db: Session, order_id: int, idempotency_key: str) -> dict:
    # 1. Check if this exact checkout attempt was already processed (Idempotency)
    existing_payment = db.query(Payment).filter(Payment.idempotency_key == idempotency_key).first()
    if existing_payment:
        if existing_payment.status == PaymentStatus.SUCCESS:
            return {"payment_id": existing_payment.id, "status": "already_success", "message": "Payment already completed."}
        return {"payment_id": existing_payment.id, "status": existing_payment.status.value, "message": "Payment pending."}

    # 2. Fetch Order
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order.status != OrderStatus.PENDING_PAYMENT:
        raise HTTPException(status_code=400, detail=f"Order is already {order.status.value}")

    # 3. Create Pending Payment Record
    new_payment = Payment(
        order_id=order_id,
        amount=order.total_price,
        status=PaymentStatus.PENDING,
        idempotency_key=idempotency_key
    )
    db.add(new_payment)
    db.commit()
    db.refresh(new_payment)

    # 4. Get Payment URL from Gateway (Mock or Real)
    amount_in_rials = float(order.total_price) * 10
    callback_url = "http://localhost:3000/payment/callback"
    
    gateway_response = payment_gateway.generate_payment_url(amount_in_rials, order_id, callback_url)

    return {
        "payment_id": new_payment.id,
        "status": "pending",
        "payment_url": gateway_response["payment_url"],
        "message": "Redirect user to payment_url"
    }

def verify_and_finalize_payment(db: Session, order_id: int, transaction_id: str, idempotency_key: str) -> dict:
    # 1. Lock the payment row to prevent race conditions (Idempotency enforcement)
    payment = db.query(Payment).filter(
        Payment.idempotency_key == idempotency_key
    ).with_for_update().first()

    if not payment:
        raise HTTPException(status_code=404, detail="Payment record not found")

    # 2. If already successful, return success immediately (Idempotency)
    if payment.status == PaymentStatus.SUCCESS:
        return {"status": "success", "message": "Payment already verified and processed."}

    # 3. Verify with the Gateway
    amount_in_rials = float(payment.amount) * 10
    is_valid = payment_gateway.verify_payment(transaction_id, amount_in_rials)

    if not is_valid:
        payment.status = PaymentStatus.FAILED
        db.commit()
        raise HTTPException(status_code=400, detail="Payment verification failed at gateway.")

    # 4. Payment is valid! Finalize the order.
    order = db.query(Order).filter(Order.id == order_id).with_for_update().first()
    
    # Update Payment Status
    payment.status = PaymentStatus.SUCCESS
    payment.gateway_transaction_id = transaction_id
    
    # Update Order Status
    order.status = OrderStatus.PAID

    # 5. NEW: Increment sold_count for each product in the order
    for item in order.items:
        item.variant.product.sold_count += item.quantity

    # 6. Safely Deduct Inventory for each item
    for item in order.items:
        check_and_deduct_stock(db, item.variant_id, item.quantity)

    # 7. Commit all changes atomically
    db.commit()

    return {"status": "success", "message": "Payment successful and order finalized."}