# -*- coding: utf-8 -*-
#from django.core.exceptions import PermissionDenied
#from back_emedido.apps.end_user.models import EndUser
from back_emedido.apps.parameter.models import Parameter
from back_emedido.apps.inspector.models import Inspector
from datetime import datetime, timedelta
from django.db.models import Q

import logging
#logger = logging.getLogger(__name__)

logcron = logging.getLogger('crons')


def test():
    print("Testeando cronjob")
    logcron.info("TESTEANDO CRON")

def put_inspector_offline():
    try:
        m = int(Parameter.objects.get(key="inspector_to_offline_min").value)
        th = datetime.now() - timedelta(minutes=m)
        # Filter inspectors, actives, and last conn null, or older than th (m minutes from now)
        for i in Inspector.objects.filter(active=True).filter(Q(last_modified=None) | Q(last_modified__lt=th)):
            logcron.info("Inspector "+i.name+" change status to INACTIVO")
            i.active=False
            i.save()
        # Dont do this way, cause save() is not aclled
        #Inspector.objects.filter(active=True).filter(Q(lastconn=None) | Q(lastconn__lt=th)).update(active=False)
        # This one neither : i.save(update_fields=['active'])
    except Exception as err:
        logcron.error("With parmeter inspector_to_offline_min, is it defined in parameters table?")
        logcron.error("%s"%err)
