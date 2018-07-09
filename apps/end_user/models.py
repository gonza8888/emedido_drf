# -*- coding: utf-8 -*-
from django.db import models
#from django.contrib.auth.models import User
from phonenumber_field.modelfields import PhoneNumberField
from django.core.validators import MinValueValidator
from back_emedido.apps.users_x_patents.models import UsersPatents
from back_emedido.apps.recharge_card.models import RechargeCard
from back_emedido.apps.fault.models import Fault
#from back_emedido.apps.penalty.models import Penalty
from back_emedido.helpers import get_setting_param
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

def validate_credit(value):
    c = get_setting_param("negative_credit_allowed")
    if value < c:
        raise ValidationError(
            _('No puede tener menos de %(cred)s créditos.'),
            params={'cred':c},
        )

class EndUser(models.Model):
    """Modelo que representa a un user final.

        .. _EndUser:

        +------------------+------------------+----------------+-----------------------------------------------------------+
        | Nombre campo     |       Tipo       | Null permitido |                 Comentario                                |
        +==================+==================+================+===========================================================+
        | phone            | PhoneNumberField |       No       |   Phone of user, unique and ideintifier                   |
        +------------------+------------------+----------------+-----------------------------------------------------------+
        | pin              |     small int    |       No       |   Pin of user                                             |
        +------------------+------------------+----------------+-----------------------------------------------------------+
        | name             |     Char(48)     |       No       |                                                           |
        +------------------+------------------+----------------+-----------------------------------------------------------+
        | surname          | Char(48)         |       No       |                                                           |
        +------------------+------------------+----------------+-----------------------------------------------------------+
        | dni              | Char(20)         |       No       |                                                           |
        +------------------+------------------+----------------+-----------------------------------------------------------+
        | dni_type         | Char             |       No       |   Types of DNI:                                           |
        |                  |                  |                |   "DNI", "CI", "LE", "LC", "Otro"                         |
        +------------------+------------------+----------------+-----------------------------------------------------------+
        | email            | EmailField       |       Si       |  Email optional                                           |
        +------------------+------------------+----------------+-----------------------------------------------------------+
        | credits          | Float (def 0)    |                |  Credits the user has , to park                           |
        |                  |                  |                |  Charge by card, transfer or MercadoPago                  |
        +------------------+------------------+----------------+-----------------------------------------------------------+
        | last_charge      | Float (def 0)    |                |  Last charge done                                         |
        +------------------+------------------+----------------+-----------------------------------------------------------+
        | locked_reason    | Char(128)(def '')|                |  Reason why the user was blocked                          |
        +------------------+------------------+----------------+-----------------------------------------------------------+
        | locked           | Bool (def False) |                |  Flag to know if user is blocked                          |
        +------------------+------------------+----------------+-----------------------------------------------------------+
        | init_tries       | Small int (def 0)|                |  Couter of failed logins                                  |
        +------------------+------------------+----------------+-----------------------------------------------------------+
        | is_reseller      | Bool (def False) |                |  Flag to tel if it reseller                               |
        +------------------+------------------+----------------+-----------------------------------------------------------+
        | main_patent      | Char(7)          |     Si         |  Main patent, linked to user                              |
        +------------------+------------------+----------------+-----------------------------------------------------------+
        | created          | DateTime         |     No         |  date of creation of user                                 |
        +------------------+------------------+----------------+-----------------------------------------------------------+
        | last_modified    | DateTime         |     No         |  Date last modified of users                              |
        +------------------+------------------+----------------+-----------------------------------------------------------+

    """

    phone = PhoneNumberField(db_index=True, unique=True)
    pin = models.PositiveSmallIntegerField()

    name = models.CharField(max_length=48)
    surname = models.CharField(max_length=48)
    dni = models.CharField(max_length=20)
    DNI_TYPE_CHOICES = (
        ('DNI', 'DNI'),
        ('CI', 'CI'),
        ('LC', 'LC'),
        ('LE', 'LE'),
        ('Otro', 'Otro'),
    )
    dni_type = models.CharField(max_length=20,choices=DNI_TYPE_CHOICES)
    email = models.EmailField(max_length=70,blank=True, null=True)

    credits = models.FloatField('Credits', validators = [validate_credit], default=0)
    last_charge = models.FloatField('Last recharge done', default=0)
    main_patent = models.CharField(max_length=7,blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True, editable=False, null=False, blank=False)
    last_modified = models.DateTimeField(auto_now=True, editable=False, null=False, blank=False)

    # This three fuelds are ment to manage lock of accounts. For now, 3 attempts of
    # failed logins, is the only reason why an account will be blocked
    # When login ok, counter reset to 0
    locked = models.BooleanField(default=False)
    locked_reason = models.CharField(max_length=128,blank=True, null=True, default='')
    init_tries = models.PositiveSmallIntegerField('Failed login attempts.',default=0)

    is_reseller = models.BooleanField(default=False)

    def __unicode__(self):
        return u'[%s] %s %s'%(self.phone, self.name, self.surname)
    def __str__(self):
        return '[{phone}] {name} {surname}'.format(phone=self.phone, name=self.name, surname=self.surname)
    class Meta:
        app_label = 'end_user'

    # This properties are added to serializer, so we will see them wen we ask for user data
    # Round numbers, only calculated counters
    @property
    def count_recharges(self):
        """Cantidad de Recharges realizadas from Phone.
        """
        return RechargeCard.count_recharges(self.phone)

    @property
    def count_patents(self):
        """Cantidad de patents asociadas al phone.
        """
        return UsersPatents.count_patents(self.phone)

    @property
    def count_faults(self):
        """Cantidad de faltas asociadas al phone ( a sus patents )
        """
        return Fault.count_faults(phone=self.phone)
