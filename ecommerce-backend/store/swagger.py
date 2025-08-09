from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
    openapi.Info(
        title="E-commerce API",
        default_version='v1',
        description="""
        Welcome to the E-commerce Backend API! This documentation helps you interact with our
        backend services for product management, shopping carts, orders, and payments.

        ### Authentication
        Most endpoints require authentication. We use **JWT Bearer Token** authentication.

        1.  **Obtain Token:**
            * `POST /api/token/pair/` with `email` and `password` to get your `access` token.
                ```json
                {
                    "email": "johndoe@gmail.com",
                    "password": "qwerty4321"
                }
                ```
                The response will contain your `access` and `refresh` tokens.

        2.  **Authorize in Swagger:**
            * Click the **"Authorize" button** (green/blue button or lock icon) below.
            * In the modal, enter your `access` token in the format: `Bearer YOUR_ACCESS_TOKEN`.
                Example: `Bearer eyJhbGciOiJIUzI1NiI...`
            * Click "Authorize" and then "Close".

        3.  **Make Authenticated Requests:** All subsequent requests made through this Swagger UI will include your token.

        ### API Endpoints
        * **Products:** Browse products, product variants, and images.
        * **Cart:** Add/remove items from your shopping cart.
        * **Orders:** Create orders from your cart and manage shipping addresses.
        * **Payments:** Initiate payments for orders (using Stripe).
        * **Reviews:** Leave reviews for products.
        """,
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="wilfredmugacha@gmail.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)
