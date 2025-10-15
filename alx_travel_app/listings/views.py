import os
import requests
from django.http import JsonResponse
from django.views import View
from .models import Payment
from dotenv import load_dotenv

load_dotenv()

CHAPA_SECRET_KEY = os.getenv('CHAPA_SECRET_KEY')

class InitiatePaymentView(View):
    def post(self, request):
        booking_reference = request.POST.get('booking_reference')
        amount = request.POST.get('amount')

        headers = {
            'Authorization': f'Bearer {CHAPA_SECRET_KEY}',
            'Content-Type': 'application/json'
        }
        data = {
            'amount': amount,
            'currency': 'ETB',
            'tx_ref': booking_reference,
            'callback_url': 'http://localhost:8000/api/verify-payment/'
        }

        response = requests.post('https://api.chapa.co/v1/transaction/initialize', json=data, headers=headers)
        res_data = response.json()

        if res_data.get('status') == 'success':
            transaction_id = res_data['data']['tx_ref']
            Payment.objects.create(
                booking_reference=booking_reference,
                transaction_id=transaction_id,
                amount=amount,
                status='Pending'
            )
            return JsonResponse({'payment_url': res_data['data']['checkout_url']})
        return JsonResponse(res_data, status=400)


class VerifyPaymentView(View):
    def get(self, request):
        transaction_id = request.GET.get('transaction_id')

        headers = {'Authorization': f'Bearer {CHAPA_SECRET_KEY}'}
        url = f"https://api.chapa.co/v1/transaction/verify/{transaction_id}"
        response = requests.get(url, headers=headers)
        res_data = response.json()

        try:
            payment = Payment.objects.get(transaction_id=transaction_id)
            if res_data.get('status') == 'success' and res_data['data']['status'] == 'success':
                payment.status = 'Completed'
            else:
                payment.status = 'Failed'
            payment.save()
        except Payment.DoesNotExist:
            return JsonResponse({'error': 'Payment record not found'}, status=404)

        return JsonResponse(res_data)
