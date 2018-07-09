# -*- coding: utf-8 -*-
from django.db import models
from back_emedido.apps.block.models import Block
from phonenumber_field.modelfields import PhoneNumberField
from datetime import datetime, timedelta, date
from django.core.validators import MinValueValidator

class Parking(models.Model):
    """
        Model epresenting action of parking
        Where , which vehicle, which phone, and date,
        for how long.
    """

    DURATION_TIME_CHOICES = (

        (timedelta(minutes=15), "15 min"),
        (timedelta(minutes=30), "30 min"),
        (timedelta(minutes=45), "45 min"),
        (timedelta(hours=1), "1 hour"),
        (timedelta(hours=1, minutes=15), "1:15 hours"),
        (timedelta(hours=1, minutes=30), "1:30 hours"),
        (timedelta(hours=1, minutes=45), "1:45 hours"),
        (timedelta(hours=2), "2 hours"),
        (timedelta(hours=2, minutes=15), "2:15 hours"),
        (timedelta(hours=2, minutes=30), "2:30 hours"),
        (timedelta(hours=2, minutes=45), "2:45 hours"),
        (timedelta(hours=3), "3 hours"),
    )

    block = models.ForeignKey(Block, on_delete=models.PROTECT)
    patent = models.CharField(max_length=7)
    phone = PhoneNumberField('phone del usuario',blank=True,null=True,db_index=True)
    phone_reseller = PhoneNumberField('phone del que genera el parking',blank=True,null=True,db_index=True)
    date_start = models.DateTimeField('Fecha/Hora comienzo de parking',car_now_add=True)
    # Durationfield is of type timedelta also. So it has days, seconds and microseconds.
    # If we initialize it with minuts, it is converted
    # d = datetime.timedelta(minutes=1) ; d.seconds == 60
    duration = models.DurationField('duration del parking',choices=DURATION_TIME_CHOICES)
    used_credits = models.FloatField('credits usados por el tiempo de parking', validators = [MinValueValidator(0.0)])

    @property
    def remaining_time(self):
        """
        Returns time remaining of current park,
        If it is negative, the park is expired.
        """
        diff_seconds = (datetime.now() - self.date_start).total_seconds()
        diff_seconds = int(round(diff_seconds))

        duration_seconds = self.duration.total_seconds()
        # We have duration in seconds, and seconds of the difference between now and start of parking
        # If diff is less than duration, this will be positive, else negative.
        return  int( (duration_seconds - diff_seconds) / 60)

    # Datetieme of finalization of parking ticket.
    @property
    def date_end(self):
        date_end = (self.date_start+self.duration)
        return date_end

    @property
    def is_active(self):
        """
            Property that tell us if a car is active or "well parked", i.e. the parks is not expired.
        """
        return (self.date_start+self.duration) > datetime.now()


    def __unicode__(self):
        return u'[%s] %s'%(self.patent, self.block.code)
    def __str__(self):
        return '[{a}] {b}'.format(a=self.patent, b=self.block.code)

    class Meta:
        app_label = 'parking'
