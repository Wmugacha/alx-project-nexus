# 🛒 E-Commerce Backend

A robust, scalable, and secure backend system built with Django and PostgreSQL to power an e-commerce product catalog. This project is part of my ALX Project Nexus submission and demonstrates practical application of backend engineering principles learned during the ProDev Backend Engineering Program. It's designed to be the core API for a modern e-commerce platform.

## 📌 Project Overview

This backend simulates a real-world e-commerce application, providing comprehensive APIs for:

- Custom User Authentication & Authorization (JWT)
- Product & Category Management with advanced querying
- Shopping Cart & Order Management
- Payment Processing with Stripe Checkout Sessions
- Robust Webhook Handling for asynchronous payment updates
- Background Task Processing (Celery & RabbitMQ) for efficiency
- Caching (Redis) for performance
- Interactive API Documentation (Swagger/OpenAPI)

The application is containerized with Docker and deployed to Railway, utilizing continuous integration for automated deployments.

## 🧰 Technologies Used

- **Python + Django** — Core backend web framework
- **PostgreSQL** — Primary relational database
- **Django REST Framework (DRF)** — Powerful toolkit for building RESTful APIs
- **Django Simple JWT** — Secure, token-based authentication (JWT)
- **drf-yasg** — Automatic generation of interactive Swagger/OpenAPI documentation
- **Stripe** — Leading payment gateway for handling payments and webhooks (specifically Stripe Checkout Sessions)
- **Celery + RabbitMQ** — Distributed task queue for asynchronous background processing
- **Redis** — In-memory data store for caching and as Celery broker/backend
- **Docker** — Containerization for isolated and consistent development/production environments
- **Whitenoise** — Efficient static file serving in production (for Django Admin and Swagger UI assets)
- **Django Extensions** — Provides useful extensions like runscript for seeding
- **GitHub Actions** — CI/CD pipeline for automated testing and deployment to Railway

## 🚀 Key Features

### ✅ Core API Endpoints

- **User Management**: Registration, JWT-based login, and profile management.
- **Product & Category Management**: Full CRUD operations for products, product variants, and categories.
- **Shopping Cart**: Add, update, and remove items from a user's cart.
- **Order Management**: Create orders from carts, with detailed order item and shipping address snapshots.
- **Shipping Addresses**: Manage multiple shipping addresses per user.

### 🔎 Advanced API Querying

- **Filtering**: Products by category, name, active status, etc.
- **Sorting**: Products by various criteria (e.g., price, creation date).
- **Pagination**: Efficient retrieval of large datasets.

### 💳 Payment Integration

- **Stripe Checkout Sessions**: Seamless and secure payment flow via Stripe's hosted checkout page.
- **Stripe Webhook Handling**: Asynchronous updates for payment success/failure, ensuring order fulfillment reliability.
- **Secure handling of sensitive payment information** (handled by Stripe).

### 📑 API Documentation

- **Swagger UI**: Interactive and auto-generated API documentation available at the `/swagger/` endpoint, providing a clear interface for testing and understanding all API capabilities.
- **Redoc**: Alternative documentation at `/redoc/`.

### ⚡ Asynchronous Task Processing

- **Celery & RabbitMQ**: Offloads resource-intensive tasks, such as sending order confirmation emails, to background workers.
- **Redis**: Used as the result backend for Celery, storing task results and metadata.

## 📁 Project Structure

```

ecommerce\_backend/
├── ecommerce\_project/            # Main Django project settings and URL configurations
├── store/                        # Core e-commerce logic: Products, Categories, Carts, Orders, Payments, Webhooks
│   ├── migrations/
│   ├── models.py
│   ├── views.py
│   ├── serializers.py
│   ├── urls.py
│   ├── tasks.py
│   ├── admin.py
│   └── management/
│       └── commands/
│           └── seed.py           # Database seeding script (Django management command)
├── users/                        # User authentication and custom user model
│   ├── migrations/
│   ├── models.py
│   ├── views.py
│   ├── serializers.py
│   ├── urls.py
│   └── admin.py
├── staticfiles/                  # Collected static files (Django Admin, drf-yasg assets)
├── .env.example                  # Example for local environment variables
├── Dockerfile                    # Docker build instructions for the application
├── docker-compose.yml            # Defines services for local development (PostgreSQL, RabbitMQ, Redis, Celery)
├── requirements.txt              # Python dependencies
├── manage.py                     # Django management utility
└── README.md                     # This file

```

## 🛠️ Installation & Setup (Local Development)

To get the project running on your local machine for development:

1. Clone the repository:

   ```bash
   git clone [https://github.com/Wmugacha/alx-project-nexus.git](https://github.com/Wmugacha/alx-project-nexus.git)
   cd alx-project-nexus/ecommerce-backend
   ```

2. Set up a Python virtual environment:

   ```bash
   python -m venv venv
   source venv/bin/activate    # On Windows: `venv\Scripts\activate`
   ```

3. Install Python dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file:  
   Create a file named `.env` in the `ecommerce_backend/ecommerce_project/` directory (where `settings.py` is located) and add your local environment variables.

   For local PostgreSQL, you might use something like:

   ```bash
   DEBUG=True
   SECRET_KEY=your_very_secret_key_for_local_dev
   DATABASE_URL=postgres://user:password@localhost:5432/mydatabase
   STRIPE_SECRET_KEY=sk_test_YOUR_STRIPE_TEST_SECRET_KEY
   STRIPE_PUBLISHABLE_KEY=pk_test_YOUR_STRIPE_TEST_PUBLISHABLE_KEY
   STRIPE_WEBHOOK_SECRET=whsec_YOUR_STRIPE_TEST_WEBHOOK_SECRET # From Stripe Dashboard for local webhook
   FRONTEND_URL=http://localhost:3000 # Or your local frontend URL
   ```

5. Start Docker Compose services (PostgreSQL, RabbitMQ, Redis):

   ```bash
   docker compose up --build
   ```

   This will spin up the necessary services in Docker containers.

6. Apply database migrations:

   ```bash
   python manage.py migrate
   ```

7. Create a superuser (for Django Admin access):

   ```bash
   python manage.py createsuperuser
   ```

8. Seed the database with sample data:

   ```bash
   python manage.py seed
   ```

9. Run the Django development server:

   ```bash
   python manage.py runserver
   ```

Your API should now be running locally at `http://127.0.0.1:8000/`.

## 🚀 Deployment (AWS & Supabase)

This backend is continuously deployed using an AWS instance and Supabase.

- **Database**: Leverages Supabase for a fully managed, scalable PostgreSQL database.
- **Containerization & Orchestration**: The application stack (Django Web App, Celery Worker, RabbitMQ, and Redis) is containerized and orchestrated using Docker Compose directly on an AWS instance.
- **Automatic Deployments**: GitHub Actions CI/CD pipeline automates testing and deployment to the AWS environment.
- **Environment Variables**: All sensitive keys and configurations (e.g., `DATABASE_URL`, `SECRET_KEY`, Stripe keys) are securely managed on the AWS instance and injected into the containers.

**Live API Documentation:** Access the interactive Swagger UI for the deployed application at:
[API Documentation](http://51.20.119.5:8002/swagger/)

## 🔑 Authentication (JWT) Workflow

The API uses JWT (JSON Web Tokens) for secure authentication.

- **Register a User**: Use the `POST /api/users/register/` endpoint to create a new user account.
- **Obtain Access & Refresh Tokens**: Send a `POST` request to `/api/token/` (or `/api/token/pair/`) with your email and password. The response will provide an access token (short-lived) and a refresh token (longer-lived).
- **Authorize API Requests**: Include the access token in the `Authorization` header of all subsequent protected API requests:
  ```bash
  Authorization: Bearer <your-access-token>
  ```

In Swagger UI, use the "Authorize" button at the top to set this header for all requests.

- **Refresh Token**: When the access token expires, use the refresh token with a `POST` request to `/api/token/refresh/` to obtain a new access token.

## 📚 API Endpoints Overview

| Endpoint                 | Method        | Description                                |
| ------------------------ | ------------- | ------------------------------------------ |
| `/`                      | GET           | Redirects to Swagger UI documentation      |
| `/admin/`                | GET           | Django Admin panel                         |
| `/api/users/register/`   | POST          | Register a new user                        |
| `/api/users/me/`         | GET/PUT/PATCH | Retrieve/Update authenticated user profile |
| `/api/store/categories/` | GET/POST      | List/Create categories                     |
| `/api/store/products/`   | GET/POST      | List/Create products                       |
| `/api/store/carts/`      | GET/POST      | List/Create carts                          |
| `/api/stripe-webhook/`   | POST          | Stripe webhook handler for payment events  |
| `/swagger/`              | GET           |                                            |

Interactive API documentation (Swagger UI) |

## 📈 Optimization Techniques Implemented

- **Database Indexing**: Strategic use of database indexes on frequently queried fields to speed up data retrieval.
- **Query Optimization**: Utilizing Django ORM's `select_related` and `prefetch_related` to minimize database queries for related objects.
- **Background Tasks**: Offloading long-running or non-critical operations to Celery, preventing API blocking and improving user experience.

## 🧪 Testing

- **API Endpoints**: Thoroughly tested using Postman for individual requests and Swagger UI for interactive exploration and automated request generation.
- **Payment Flow**: Tested end-to-end with Stripe's test card numbers and simulated payment events from the Stripe Dashboard and Stripe CLI.
- **Webhooks**: Verified robust webhook handling by simulating various Stripe events using the `stripe trigger` command and monitoring application logs on Railway.

## 🔄 Version Control & Workflow

- **Atomic Commits**: Maintaining a history of small, self-contained changes with descriptive commit messages.
- **Feature-Branch Workflow**: Development occurs on dedicated feature, fix, or performance branches (feat/, fix/, perf/ prefixes) to ensure a clean main branch.
- **Organized Codebase**: Adhering to Django conventions and clear naming for maintainability.
- **.gitignore**: Properly configured to exclude sensitive information and unnecessary files from the repository.

## 🧠 Lessons Learned

- **End-to-End REST API Architecture**: Gained deep insight into designing and implementing a complete RESTful API with Django and DRF.
- **Secure Authentication & Authorization**: Mastered JWT token-based authentication and implementing permission layers.
- **Payment Workflows & Webhook Handling**: Understood the complexities of integrating a payment gateway like Stripe, including the critical role of secure webhook processing and `checkout.session.completed` events for order fulfillment.
- **Static File Serving in Production**: Emphasized the importance of Whitenoise and `collectstatic` for serving static assets in a deployed Django application.
- **Dockerized Development & Deployment**: Gained hands-on experience in containerizing a Django application and deploying it to a PaaS like Railway, including debugging common deployment issues (e.g., database migrations, environment variables, static files).
- **API Documentation Standards**: Appreciated the value of auto-generated, interactive API documentation for clarity and collaboration.

## 👤 Author

Wilfred Mugacha
Backend Developer | ALX ProDev Graduate
[LinkedIn](https://www.linkedin.com/in/wilfredmugacha) | [Email](mailto:wilfredmugacha@gmail.com)

## 📌 Project Status

- ✅ Custom User Authentication (JWT)
- ✅ Products & Categories CRUD
- ✅ Product Variants & Shipping Addresses
- ✅ Pagination, Filtering & Sorting
- ✅ PostgreSQL Optimization & Migrations
- ✅ Stripe Checkout Session Integration
- ✅ Robust Stripe Webhook Handling
- ✅ Redis Caching Setup
- ✅ Swagger/OpenAPI Documentation
- ✅ Dockerized Development & Deployment to Railway
- ✅ Continuous Deployment
