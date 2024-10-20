from django.http import JsonResponse
from django.shortcuts import redirect
import stripe
from rest_framework.decorators import api_view

stripe.api_key = 'sk_test_51NjZOfAM6juVImQkcpl8To0kuiUl1PPDTVF2HhOIlvNWBJc6gAD1W01KFqmKeM3FQpIkhGd9eHktddJq7qqiSSOz006zspy7Xv'
YOUR_DOMAIN = 'http://localhost:5173'

@api_view(['POST'])
def create_checkout_session(request):
    quantity = int(request.POST.get('quantity', 1)) 
    total_price = float(request.POST.get('total_price', 25)) 
    total_price_in_cents = int(total_price * 100)


    tax_rate = 0.05
    tax_in_cents = int(total_price_in_cents * tax_rate)

    try:
        checkout_session = stripe.checkout.Session.create(
            line_items=[
                {
                    'price_data': {
                        'currency': 'cad',
                        'product_data': {
                            'name': f'餐食 × {quantity}',
                        },
                        'unit_amount': total_price_in_cents,
                    },
                    'quantity': 1,
                },
                {
                    'price_data': {
                        'currency': 'cad',
                        'product_data': {
                            'name': '税金 (Tax)',
                        },
                        'unit_amount': tax_in_cents, 
                    },
                    'quantity': 1, 
                }
            ],
            mode='payment',
            success_url=YOUR_DOMAIN + '?success=true',
            cancel_url=YOUR_DOMAIN,
        )
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

    return redirect(checkout_session.url, code=303)