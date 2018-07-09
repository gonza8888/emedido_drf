#from django.contrib.gis import admin
from django.contrib import admin
from .models import ZoneDetails

Sclass ZoneDetailsAdmin(admin.ModelAdmin):
    list_display = ("zone_custom", "hour_range", "price_minutes", "mon","tue","wed","thu","fri","sat","sun")

    list_filter = ("zone","sat","sun")

    def hour_range(self, obj):
        return "%s -> %s" % (obj.hour_init, obj.hour_end)
    hour_range.short_description = 'Rango horario'

    def price_minutes(self, obj):
        return "%s -> %s" % (obj.price, obj.minutes)
    price_minutes.short_description = 'Precio-Minutos'

    def zone_custom(self, obj):
        return "[%s] %s" % (obj.zone.code, obj.zone.name)
    zone_custom.short_description = "Zona"
#    zone_custom.admin_order_field = "zone.name"

admin.site.register(ZoneDetails, ZoneDetailsAdmin)
