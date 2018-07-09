from django.test import TestCase
#from .models import ZoneDetails
from back_emedido.apps.zone.models import Zone
from back_emedido.apps.zone_details.models import ZoneDetails
from datetime import time
from django.contrib.gis.geos import (Point,GEOSGeometry, MultiPolygon, Polygon)
from django.core.exceptions import ValidationError

class ZoneDetailsTest(TestCase):
    def test_creation(self):
        init= time(9,1)
        end= time(12,1)
        poly3="""POLYGON((50 50, 60 70, 60 70, 50 100, 20 20, 50 50))"""
#        import pdb;pdb.set_trace()
        z = Zone(zone=MultiPolygon(GEOSGeometry(poly3)), name="zona3", code="microcentro")
        z.save()
        self.assertTrue(ZoneDetails.objects.create(zone=z,hour_init=init, hour_end=end, price=1.0,stay_price=50.0, max_minutes=700,minutes=123))

        # Error cause max_minutes is more than configured.
        with self.assertRaises(ValidationError):
            ZoneDetails.objects.create(zone=z,hour_init=init, hour_end=end, price=1.0,stay_price=50.0, max_minutes=7000,minutes=123)
        #self.assertTrue(ZoneDetails.objects.create(zone=z,hour_init=init, hour_end=end, price=1.0,stay_price=50.0, max_minutes=7000,minutes=123))

        # Error, xq falta el argumento "minutes"
        #self.assertTrue(ZoneDetails.objects.create(zone=z,hour_init=init, hour_end=end, price=1.0,stay_price=50.0, max_minutes=700))

        self.assertTrue(ZoneDetails.objects.create(zone=z,hour_init=init, hour_end=end, price=1.0,stay_price=50.0, minutes=700))

        with self.assertRaises(ValidationError):
            ZoneDetails.objects.create(zone=z,hour_init=init, hour_end=end, price=1.0,stay_price=50.0, max_minutes=700)
