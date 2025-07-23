# 🛒 E-Commerce Backend

A robust, scalable, and secure backend system built with Django and PostgreSQL to power an e-commerce product catalog. This project is part of my ALX Project Nexus submission and demonstrates practical application of backend engineering principles learned during the **ProDev Backend Engineering Program**.

---

## 📌 Project Overview

This backend simulates a real-world e-commerce application, providing APIs for:

* **User authentication**
* **Product and category management**
* **Filtering, sorting, and pagination**
* **Database performance optimization**
* **Payment processing with Stripe**
* **Background task processing with Celery & RabbitMQ**
* **Caching with Redis**
* **API documentation with Swagger/OpenAPI**

---

## 🧰 Technologies Used

* **Python** + **Django** — Core backend framework
* **PostgreSQL** — Relational database
* **Django REST Framework (DRF)** — RESTful API layer
* **JWT (SimpleJWT)** — Secure user authentication
* **drf-yasg** — Swagger/OpenAPI integration for API documentation
* **Stripe** — Payment gateway integration
* **Celery + RabbitMQ** — Background task processing
* **Redis** — Caching and Celery broker/backend
* **Docker** — Containerization for consistent development environments
* **GitHub Actions** — CI/CD pipeline for automated testing and deployment

---

## 🚀 Key Features

### ✅ CRUD Operations

* Products and Categories: Create, Read, Update, Delete
* User Registration and JWT-based Login

### 🔎 API Query Features

* **Filtering** products by category or name
* **Sorting** by price or creation date
* **Pagination** for large product datasets

### 🔐 Authentication

* JWT token-based authentication system
* Protected endpoints for product/category management

### 💳 Payment Integration

* Stripe payment processing for product purchases
* Secure handling of payment intents and webhooks

### ⏱️ Background Task Management

* Celery + RabbitMQ used to:

  * Send order confirmation emails
  * Handle webhook processing
  * Schedule deferred or retryable tasks

### ⚡ Caching

* Redis caching for:

  * Product listings
  * Frequently accessed endpoints
  * User sessions or carts

### 📑 API Documentation

* Swagger UI auto-generated documentation
* Available via `/swagger/` endpoint

---

## 📁 Project Structure

```
ecommerce_backend/
├── ecommerce_backend/        # Django project settings
├── products/                 # Products & categories app
├── users/                    # User registration/authentication
├── payments/                 # Stripe integration and webhook handlers
├── tasks/                    # Celery task definitions
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── manage.py
└── README.md
```

---

## 🛠️ Installation & Setup (Local)

```bash
# Clone the repo
git clone https://github.com/your-username/alx-project-nexus.git
cd alx-project-nexus/ecommerce-backend

# Set up virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Apply migrations
python manage.py migrate

# Create superuser (for admin access)
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

To run **Celery + RabbitMQ** and **Redis**:

```bash
# Start services using Docker Compose
docker-compose up -d
```

---

## 🔑 Authentication (JWT)

* `POST /api/token/` — Obtain token
* `POST /api/token/refresh/` — Refresh token
* Include token in headers as:
  `Authorization: Bearer <your-token>`

---

## 📚 API Endpoints Overview

| Endpoint              | Method    | Description                      |
| --------------------- | --------- | -------------------------------- |
| `/api/products/`      | GET       | List all products                |
| `/api/products/`      | POST      | Create product (auth required)   |
| `/api/products/<id>/` | GET       | Retrieve single product          |
| `/api/products/<id>/` | PUT/PATCH | Update product                   |
| `/api/products/<id>/` | DELETE    | Delete product                   |
| `/api/categories/`    | GET/POST  | Manage categories                |
| `/api/checkout/`      | POST      | Initiate Stripe checkout session |
| `/api/webhook/`       | POST      | Stripe webhook handler           |
| `/api/token/`         | POST      | Obtain JWT                       |
| `/swagger/`           | GET       | View API documentation           |

---

## 📈 Optimization Techniques

* PostgreSQL indexes on frequently queried fields
* Query optimization using `select_related` and `prefetch_related`
* Redis caching to reduce DB hits
* Background tasks to offload heavy/slow operations

---

## 🧪 Testing

You can use **Postman** or **Swagger UI** to test API endpoints.
Stripe can be tested using test card numbers and their test mode dashboard.

---

## 🔄 Version Control & Workflow

* Atomic, descriptive commits
* Feature-branch workflow (`feat/`, `fix/`, `perf/`, etc.)
* Organized codebase with proper `.gitignore` and `README.md`

---

## 🧠 Lessons Learned

* End-to-end REST API architecture with Django & DRF
* Secure authentication and authorization with JWT
* Payment workflows and webhook handling via Stripe
* Caching for performance, async tasks for scalability
* Dockerized backend development
* Clean code practices and API documentation standards

---

## 👤 Author

**Wilfred Mugacha**
Backend Developer | ALX ProDev Fellow
[LinkedIn](#) | [Email](#)

---

## 📌 Project Status

✅ User authentication
✅ Products & categories CRUD
✅ Pagination, filtering & sorting
✅ PostgreSQL optimization
✅ Stripe payment flow
✅ Celery task queue integration
✅ Redis caching setup
✅ Swagger documentation

🔜 Final deployment, CI/CD with GitHub Actions
