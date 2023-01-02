from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View


# Google related views
# See https://developers.google.com/identity/protocols/oauth2/web-server#python
class GoogleAuthView(View):
    def get(request):
        # For now nothing
        return "k"

class GoogleCallBackView(View):
    def get(request):
        # For now nothing
        return "k"
