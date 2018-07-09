# -*- coding: utf-8 -*-
from django.contrib.gis.db import models
from back_emedido.apps.parameter.models import Parameter
from back_emedido.apps.rule_callable.models import RuleMethod
from django.conf import settings

def defvalue():
    try:
        valor = Parameter.objects.get(key='def_max_stay_minutes').value
        return int(valor)
    except Parameter.DoesNotExist:
        if hasattr(settings,'DEF_MAX_STAY_MINUTES'):
            return settings.DEF_MAX_PARK_MINUTES
        else:
            return 1440


class Zone(models.Model):
    """Modelo que representa una zona de estacionamiento. Un area de la ciudad.

        .. _Zone:

        +------------------+------------------+----------------+-----------------------------------------------------------+
        | Nombre campo     |       Tipo       | Null permitido |                 Comentario                                |
        +==================+==================+================+===========================================================+
        | zone             | MultiPlygonField |      No        |   FK to zone we are datailing					           |
        |                  |                  |                |   It is a FK, because it is not 1 detail per zone.		   |
        |                  |                  |                |   For example , for zone 1, we have detail for range 9am  |
        |                  |                  |                |   to 11am, and another for 1pm to 18pm					   |
        +------------------+------------------+----------------+-----------------------------------------------------------+
        |   name           |   CharField(64)  |       No       |   Name of the zone                                        |
        +------------------+------------------+----------------+-----------------------------------------------------------+
        |   code           |   CharField(64)  |       No       |   Code of zona (db_index)                                 |
        +------------------+------------------+----------------+-----------------------------------------------------------+
        |  stay_minutes    | SmallInteger     |     No         |   amount of minutes that a stay lasts. Def in parameter   |
        +------------------+------------------+----------------+-----------------------------------------------------------+
        |   rules          | M2M (RuleMethod) |     Yes        |  Relation with active rules for the Zone 				   |
        +------------------+------------------+----------------+-----------------------------------------------------------+
    """


    zone = models.MultiPolygonField()
    name = models.CharField(max_length=64)
    code = models.CharField(max_length=12, db_index=True, unique=True)
    stay_minutes = models.PositiveSmallIntegerField('Amount of minutes a stay lasts', default=defvalue)
    rules = models.ManyToManyField(RuleMethod,related_name="zones", blank=True)

    def __str__(self):
        return '[{code}] {name}'.format(code=self.code, name=self.name)

    class Meta:
        app_label = 'zone'

    def rules_desc(self):
        return "\n".join([r.description for r in self.rules.all()])
    rules_desc.short_description = "Reglas activas"

    @classmethod
    def has_rule(self,code,rule):
        try:
            z = Zone.objects.get(code=code)
            exists = z.rules.get(method=rule)
        except:
            return False
        if exists:
            return True
        else:
            return False
