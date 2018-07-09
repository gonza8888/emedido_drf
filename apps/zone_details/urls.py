from django.conf.urls import url, include
from zone_details import views
from rest_framework.routers import DefaultRouter

# Create a router and register our viewsets with it.
router = DefaultRouter()
router.register(r'zonedetails', views.ZoneDetailsViewSet, base_name="zonedetails")

# The API URLs are now determined automatically by the router.
# Additionally, we include the login URLs for the browsable API.
urlpatterns = [
    url(r'^api/', include(router.urls)),
]
