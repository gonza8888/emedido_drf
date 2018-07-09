# -*- coding: utf-8 -*-
import logging
from django.http import HttpResponseForbidden, HttpResponseNotAllowed
from back_emedido.apps.auth_token.models import AuthToken
from django.http import JsonResponse, HttpResponse
from datetime import datetime
from django.urls import reverse

def TokenValidMiddleware(get_response):
    # One-time configuration and initialization.

    def middleware(request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.

        # Login is not chequed
        # With the two lines after the if, we make it continue to next middleware.
        if request.path.startswith(reverse('authenticate')):
            response = get_response(request)
            return response
            #return None
        if request.path.startswith(reverse('resetn')):
            response = get_response(request)
            return response

        # For every incoming requests, we will check if it was a valid token
        ret = {'status':'ERR_TOKEN', 'message': 'Token inválido'}
        access_token = request.META.get('HTTP_TOKEN', '') or ''
        operator = request.META.get('HTTP_OPERATOR', '') or ''

        if not access_token or not operator:
            ret['message'] = "Credenciales del request inválidas"
            return JsonResponse(ret)

        authobj = AuthToken.objects.filter(token=access_token).first()
        if authobj:
            # If date is after now, it is expired
            if authobj.expiration < datetime.now():
                # logger.exception("RequestToken make by operator %s expired:
                # %s", operator, access_token)
                return JsonResponse(ret)
        else:
            #logger.exception("RequestToken cannot be decoded: %s", token)
            return JsonResponse(ret)

        # If everythig ok, we continue with the chain of middlewares
        response = get_response(request)

        return response

    return middleware

