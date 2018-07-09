# -*- coding: utf-8 -*-
#from django.core.exceptions import PermissionDenied
from back_emedido.apps.end_user.models import EndUser
from rest_framework.response import Response

def is_reseller(function):
    def wrap(request, *args, **kwargs):
        try:
            entry = EndUser.objects.get(phone=kwargs['phone'])
            if entry.is_reseller:
                return function(request, *args, **kwargs)
            else:
                #raise PermissionDenied
                ret = {'msg':"Permission Denied.",'data':{}, 'status':'ERR'}
                return Response(ret)
        except Exception as arr:
            ret = {'msg':"Permission Denied.",'data':{}, 'status':'ERR'}
            return Response(ret)
    wrap.__doc__ = function.__doc__
    wrap.__name__ = function.__name__
    return wrap
