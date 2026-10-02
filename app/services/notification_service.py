# app/services/notification_service.py
from fastapi import BackgroundTasks
from app.integrations.email_service import email_service
from app.integrations.sms_service import sms_service

def trigger_order_notifications(
    background_tasks: BackgroundTasks,
    order_id: int,
    total_price: float,
    customer_phone: str,
    customer_email: str = None
):
    """
    Adds notification jobs to the background queue. 
    The API will return immediately to the user while these run in the background.
    """
    # 1. Alert the Admin
    background_tasks.add_task(
        email_service.send_admin_order_alert, 
        order_id, 
        total_price, 
        customer_phone
    )
    
    # 2. Send SMS to Customer
    background_tasks.add_task(
        sms_service.send_order_confirmation,
        customer_phone,
        order_id
    )
    
    # 3. Send Email Receipt (if email exists)
    if customer_email:
        background_tasks.add_task(
            email_service.send_customer_receipt,
            customer_email,
            order_id
        )