# app/integrations/sms_service.py
import httpx
import logging
from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

def send_otp_sms(phone: str, code: str):
    """
    Sends an OTP code using Melipayamak Pattern (BaseServiceNumber)
    """
    url = "https://rest.payamak-panel.com/api/SendSMS/BaseServiceNumber"
    
    payload = {
        "username": settings.MELI_USERNAME,
        "password": settings.MELI_API_KEY,
        "to": phone,
        "text": code,
        "bodyId": int(settings.MELI_BODY_ID)
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        response = httpx.post(url, json=payload, headers=headers, timeout=10)
        response_data = response.json()
        
        # Melipayamak returns RetStatus: 1 for success
        if response_data.get("RetStatus") == 1:
            logger.info(f"✅ SMS sent successfully to {phone}. RecID: {response_data.get('Value')}")
            return True
        else:
            error_code = response_data.get("RetStatus")
            error_msg = response_data.get("StrRetStatus", "Unknown error")
            logger.error(f"❌ Melipayamak API Error {error_code}: {error_msg} for phone {phone}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Network error while sending SMS to {phone}: {e}")
        return False


class SMSService:
    """Adapter for sending SMS notifications"""
    
    def send_order_confirmation(self, phone_number: str, order_id: int):
        """Send order confirmation SMS (optional - can be implemented later)"""
        logger.info(f"Order confirmation for order #{order_id} to {phone_number}")
        return True


sms_service = SMSService()
