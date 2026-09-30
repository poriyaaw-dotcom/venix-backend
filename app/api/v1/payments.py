# app/api/v1/payments.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.payment import PaymentInitiateRequest, PaymentVerifyRequest, PaymentResponse
from app.services import payment_service

router = APIRouter(prefix="/payments", tags=["Payments"])

@router.post("/initiate", response_model=PaymentResponse)
def initiate_payment_endpoint(
    payload: PaymentInitiateRequest,
    db: Session = Depends(get_db)
):
    result = payment_service.initiate_payment(db, payload.order_id, payload.idempotency_key)
    
    if result["status"] == "already_success":
        return PaymentResponse(
            payment_id=result["payment_id"],
            status="success",
            message=result["message"]
        )
        
    return PaymentResponse(
        payment_id=result["payment_id"],
        status=result["status"],
        payment_url=result.get("payment_url"),
        message=result["message"]
    )

@router.post("/verify")
def verify_payment_endpoint(
    payload: PaymentVerifyRequest,
    db: Session = Depends(get_db)
):
    result = payment_service.verify_and_finalize_payment(
        db, 
        payload.order_id, 
        payload.transaction_id, 
        payload.idempotency_key
    )
    return result

# Mock endpoint to simulate the gateway redirecting back to us
@router.get("/mock-success")
def mock_gateway_callback(tx: str, order_id: int, idempotency_key: str):
    """Simulates the payment gateway redirecting the user back to our server."""
    # In a real scenario, the frontend would catch this and call the /verify endpoint,
    # or the gateway would send a server-to-server webhook here.
    return {
        "message": "Mock Gateway Success. Frontend should now call POST /payments/verify with this transaction_id.",
        "transaction_id": tx,
        "order_id": order_id,
        "idempotency_key": idempotency_key
    }