# app/integrations/email_service.py
class EmailService:
    """Adapter for Gmail/SMTP. Mocked for now, ready for real SMTP later."""
    
    def send_admin_order_alert(self, order_id: int, total_price: float, customer_phone: str):
        # TODO: Replace with real smtplib or FastAPI-Mail later
        print(f"📧 [MOCK GMAIL] Admin Alert: New Order #{order_id} for {total_price} Tomans from {customer_phone}")
        return True

    def send_customer_receipt(self, customer_email: str, order_id: int):
        # TODO: Replace with real SMTP later
        print(f"📧 [MOCK GMAIL] Receipt sent to {customer_email} for Order #{order_id}")
        return True

email_service = EmailService()