# app/integrations/sms_service.py
class SMSService:
    """Adapter for Kavehnegar/Ghasedak/etc. Mocked for now."""
    
    def send_order_confirmation(self, phone_number: str, order_id: int):
        # TODO: Replace with real SMS provider API call later
        print(f"📱 [MOCK SMS] Thank you! Your order #{order_id} has been successfully placed.")
        return True

sms_service = SMSService()