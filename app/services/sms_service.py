# app/services/sms_service.py
import logging

logger = logging.getLogger(__name__)

def send_purchase_sms(phone_number: str, order_id: int):
    """Send purchase confirmation SMS (Mocked for now, can be replaced with real API later)"""
    logger.info(f"📱 [MOCK SMS] Thank you! Your order #{order_id} has been successfully placed. Sent to {phone_number}")
    return True