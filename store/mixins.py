from django.contrib.auth.mixins import AccessMixin
from django.shortcuts import redirect
from django.contrib import messages

class StaffRequiredMixin(AccessMixin):
    """Mixin that restricts view access strictly to authenticated staff members."""
    permission_denied_message = "Access denied. Admin credentials are required to view this page."

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not (request.user.is_staff or request.user.is_superuser):
            messages.error(request, self.permission_denied_message)
            return redirect('store:admin_login')
        return super().dispatch(request, *args, **kwargs)
