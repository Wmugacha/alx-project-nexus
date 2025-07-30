from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RegisterUserView, UserViewSet

router = DefaultRouter()
router.register(r'', UserViewSet, basename='user')

urlpatterns = [
    path('register/', RegisterUserView.as_view(), name='register'),
    path('', include(router.urls)),
]
