from django.conf.urls import url, include
from parking import views
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'parkings', views.ParkingViewSet, base_name="parkings")

# The API URLs are now determined carmatically by the router.
# Additionally, we include the login URLs for the browsable API.
urlpatterns = [
    url(r'^api/', include(router.urls)),
]
