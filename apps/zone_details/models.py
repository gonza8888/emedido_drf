# -*- coding: utf-8 -*-
from django.contrib.gis.db import models
from back_emedido.apps.zone.models import Zone
from back_emedido.apps.parameter.models import Parameter
from django.core.exceptions import ValidationError
from django.conf import settings
from django.utils.translation import gettext as _
from datetime import datetime

def defvalue():
    try:
        valor = Parameter.objects.get(key='def_max_park_minutes').value
        return int(valor)
    except Parameter.DoesNotExist:
        if hasattr(settings,'DEF_MAX_PARK_MINUTES'):
            return settings.DEF_MAX_PARK_MINUTES
        else:
            return 180

class ZoneDetails(models.Model):
    """Modelo que representa los detalles de una zona. Los horarios que se puede estacionar,
       los precios, la cantidad maxima de minutos que se puede estacionar, el precio de la estadia.

        .. _ZoneDetails:

        +------------------+------------------+----------------+-----------------------------------------------------------+
        | Nombre campo     |       Tipo       | Null permitido |                 Comentario                                |
        +==================+==================+================+===========================================================+
        | zone             | ForeignKey(zone) |       No       |   FK a la zona de la que estamos detallando datos         |
        |                  |                  |                |   Es una FK, porque no es un solo detalle para cada zona. |
        |                  |                  |                |   Por ejemplo para la zona 1, tenemos el detalle de 9am   |
        |                  |                  |                |   a 11am, y otro de 13 a 18.                              |
        +------------------+------------------+----------------+-----------------------------------------------------------+
        | hour_init        |     TimeField    |       No       |   Inicio del rango horario en el que se puede estacionar  |
        |                  |                  |                | Se aclara, que pueden haber varios rangos de 1 mismos dia |
        +------------------+------------------+----------------+-----------------------------------------------------------+
        | hour_end         |   TimeField      |       No       |  Fin del rango horario que se puede estacionar            |
        +------------------+------------------+----------------+-----------------------------------------------------------+
        | price            | FloatField       |       No       |   Precio por cantidad de minutos estipulados              |
        +------------------+------------------+----------------+-----------------------------------------------------------+
        | minutes          | SmallInteger     |       No       | Cantidad de minutos que salen lo que indica el campo price|
        +------------------+------------------+----------------+-----------------------------------------------------------+
        | stay_price       | FloatField       |       No       |   Precio de lo que sale una estadia completa              |
        +------------------+------------------+----------------+-----------------------------------------------------------+
        | max_minutes      | SmallInteger     |       Si       | Cantidad maxima de minutos que se puede estacionar en zona|
        |                  |                  |                | Se permite un valor nulo, entonces, no hay limite existe  |
        +------------------+------------------+----------------+-----------------------------------------------------------+
        |mon,tue, ... sun  | BooleanField     |     No         | Dias de la semana en los que son validos estos datos.     |
        +------------------+------------------+----------------+-----------------------------------------------------------+
    """

    # codigo zona , horario de inicio, horario de fin, minutos, precio, precio_estadia, maximo_minutos

    zone = models.ForeignKey(Zone, verbose_name="Zone's details code", on_delete=models.CASCADE, related_name='zonedetails')
    hour_init = models.TimeField('Init of time range that can be parked')
    hour_end = models.TimeField('End of time range that can be parked')
    # Price field, indicates the cost in credits for the minutes in minutes field
    # Exaple 10 credits for 30 minutes
    price = models.FloatField('Credits for amount of minutes')
    minutes = models.PositiveSmallIntegerField('Amount of minutes for calc price.')

    stay_price = models.FloatField('Price of a complete stay')
    max_minutes = models.PositiveSmallIntegerField('Max amount of minutes that can be parked', null=True, blank=True)

    # Days for which this data is valid. For example, for sunday can differ
    # the price from the rest of the days.
    mon = models.BooleanField('Lun', default=True)
    tue = models.BooleanField('Mar', default=True)
    wed = models.BooleanField('Mie', default=True)
    thu = models.BooleanField('Jue', default=True)
    fri = models.BooleanField('Vie', default=True)
    sat = models.BooleanField('Sáb', default=True)
    sun = models.BooleanField('Dom', default=True)

    def clean(self,*args,**kwargs):
        price = self.price
        stay_price = self.stay_price

        init = self.hour_init
        end = self.hour_end
        if end < init:
            raise ValidationError('End time can not be less than start.')

        if price > stay_price:
            raise ValidationError('Price of period can not be more than stay price')
        return

    def save(self,*args,**kwargs):
        self.full_clean()
        return super(ZoneDetails, self).save(*args, **kwargs)

    def __str__(self):
        return '[{code}]{init}-{end} - {minutes}min->{price}'.format(code=self.zone.code, init=self.hour_init, end=self.hour_end, minutes=self.minutes, price=self.price)

    class Meta:
        app_label = 'zone_details'
