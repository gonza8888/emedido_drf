from django.conf.urls import url, include
from zone import views
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'zones', views.ZoneViewSet, base_name="zones")

urlpatterns = [
    url(r'^api/', include(router.urls)),
]
