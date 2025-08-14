from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse

def home_view(request):
    return JsonResponse({
        "message": "Welcome to Hospital Management API",
        "endpoints": {
            "docs": "/api/",
            "admin": "/admin/"
        }
    })

urlpatterns = [
    path("", home_view),
    path('admin/', admin.site.urls),
    path('api/', include('app.urls')),  # Replace 'app' with your app name
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
