from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('core.urls')),  # API endpoints
    path('', include('core.template_urls')),  # Template views
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
