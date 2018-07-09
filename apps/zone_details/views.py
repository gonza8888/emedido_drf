# -*- coding: utf-8 -*-
from back_emedido.apps.zone_details.models import ZoneDetails
from back_emedido.apps.zone_details.serializer import ZoneDetailsSerializer
from rest_framework import viewsets
from rest_framework.response import Response
from back_emedido.helpers import list_to_dict

class ZoneDetailsViewSet(viewsets.ReadOnlyModelViewSet):
    """
        This viewset automatically provides `list`, `retrieve`,
        To insert, do it from djando admin.
    """
    queryset = ZoneDetails.objects.all()
    serializer_class = ZoneDetailsSerializer

    def list(self, request):
        ret = {'msg':'No hay zonas en el sistema.','data':{}, 'status':'ERR'}
        serializer = ZoneDetailsSerializer(self.get_queryset(), many=True)
        try:
            data = list_to_dict(serializer.data)
            ret = {"status":"OK", "msg":"ok", "data":data}
        except Exception as e:
            ret['msg'] = "Ups: Error Interno. Por favor reintente"
        return Response(ret)