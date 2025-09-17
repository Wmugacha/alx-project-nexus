from celery import shared_task
from django.core.mail import send_mail
from .models import Order

@shared_task
def send_order_confirmation_email_task(order_id):
    """
    Sends a confirmation email for a completed order.
    """
    try:
        order = Order.objects.select_related('user').get(id=order_id)
        recipient_email = order.user.email
        
        subject = f"Your Order {order.order_number} is Confirmed!"
        message = f"Thank you for your purchase, {order.user.username}!\n\nYour order details:\nOrder ID: {order.order_number}\nStatus: {order.status}"
        
        send_mail(
            subject,
            message,
            'noreply@yourshop.com',  # Replace with your 'from' address
            [recipient_email],
            fail_silently=False,
        )
        print(f"Email for order {order_id} sent to {recipient_email}.")
        
    except Order.DoesNotExist:
        print(f"Order with ID {order_id} does not exist. Email not sent.")
