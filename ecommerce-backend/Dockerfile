# Use official Python image
FROM python:3.11-slim

# Set env vars
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy project
COPY . /app/

RUN python manage.py collectstatic --noinput

# Expose the port your app runs on
EXPOSE 8000

# Run Gunicorn
CMD python manage.py migrate --noinput && gunicorn ecommerce_project.wsgi:application --bind 0.0.0.0:$PORT
