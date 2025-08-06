from rest_framework import permissions

class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_authenticated and request.user.is_staff


class ReviewPermissions(permissions.BasePermission):
    """
    Custom permission to allow:
    - Anyone to read reviews.
    - Authenticated users to create reviews.
    - A review's owner to update their own review (except 'is_approved').
    - Only admins to update 'is_approved' field.
    - Only admins to delete reviews.
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        
        if request.method == 'POST':
            return request.user and request.user.is_authenticated
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        
        if request.method in ['PUT', 'PATCH', 'DELETE']:
            return request.user and request.user.is_staff

            is_owner = obj.user == request.user

            if admin:
                return True
            if is_owner:
                if 'is_approved' in request.data:
                    return False
                return True
            return False
        return False