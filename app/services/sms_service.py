def send_purchase_sms(phone_number: str, order_id: int, amount: int):
    """
    Sends a thank you / purchase confirmation SMS to the user.
    
    TODO: Tomorrow, replace this mock with your chosen provider's SDK (e.g., Kavenegar, Melipayamak).
    Example for Kavenegar:
        from kavenegar import *
        api = KavenegarAPI('YOUR_API_KEY')
        message = f"سفارش شما با شماره {order_id} با موفقیت ثبت شد. مبلغ: {amount} تومان. از خرید شما متشکریم!"
        api.sms_send({'receptor': phone_number, 'message': message})
    """
    
    # 🚨 MOCK IMPLEMENTATION (Safe for testing today)
    print(f"\n🔥 [MOCK SMS] Sending to {phone_number}: سفارش #{order_id} با موفقیت ثبت شد. مبلغ: {amount} تومان. از خرید شما متشکریم! 🔥\n")
    
    # TODO: Uncomment the real API call tomorrow and delete the print statement above.
    # return True
