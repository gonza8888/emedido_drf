# -*- coding: utf-8 -*-
from back_emedido.apps.parking.models import Parking
from back_emedido.apps.block.models import Block
from back_emedido.apps.zone.models import Zone
from back_emedido.apps.fault.models import Fault
from back_emedido.apps.zone.views import calc_price_parking, zonedetails_nearest_range
from back_emedido.apps.end_user.models import EndUser
from back_emedido.apps.users_x_patents.models import UsersPatents
from back_emedido.apps.parking.serializer import ParkingSerializer,ParkingSerializerShort
from back_emedido.apps.rule_callable.models import RuleMethod
from rest_framework import viewsets, status
from datetime import datetime, timedelta, date
import phonenumbers
from django.db.models import F
from rest_framework.response import Response
from back_emedido.helpers import list_to_dict, format_phone, get_setting_param
from rest_framework.decorators import list_route,detail_route
from django.db.models import Max, Count
from collections import Counter,defaultdict,OrderedDict
#from back_emedido.helpers import duration_format_ok
#from back_emedido.permissions import IsDjangoUser
from back_emedido.apps.rule_callable.rules import GRACETIME,MAXTIME,FREEPARK,MAXTIME_NO,NOTIFYSU

class ParkingViewSet(viewsets.ModelViewSet):
    """
    retrieve:
        Return parking. By id

    list:
        All parkings, or filtered by: phone y/o patent.

    create:
        Park a car.

    delete:
        Function not allowed.

    partial_update:
        Update one or more fields of an existing parking.

    update:
        Update a parking.
    """

    # This functions corresponds with the map METHOS, of model RuleMethod.
    # see inside code rule_callable/models.py
    CALL_MAP = {
        FREEPARK:'_free_for_all',
        MAXTIME:'_max_time_yes',
        MAXTIME_NO:'_max_time_no',
        GRACETIME:'_grace_time',
        NOTIFYSU:'_notify_strong_users',
    }

    serializer_class = ParkingSerializer

    # Overwrite this method
    def get_queryset(self):

        patent = self.request.query_params.get('patent',None)
        block = self.request.query_params.get('block',None)
        phone = self.request.query_params.get('phone',None)

        if not (patent or block or phone):
            queryset = Parking.objects.all()

        if block and patent and phone:
            phone = format_phone(phone)
            queryset = Parking.objects.filter(block__code=block, patent=patent, phone=phone)
        if block and patent:
            queryset = Parking.objects.filter(block__code=block, patent=patent)
        if block and phone:
            phone = format_phone(phone)
            queryset = Parking.objects.filter(block__code=block, phone=phone)
        if patent and phone:
            phone = format_phone(phone)
            queryset = Parking.objects.filter(patent=patent, phone=phone)
        if block:
            queryset = Parking.objects.filter(block__code=block)
        if patent:
            queryset = Parking.objects.filter(patent=patent)
        if phone:
            phone = format_phone(phone)
            queryset = Parking.objects.filter(phone=phone)
        return queryset

    # ---- Overwrite funtions to return estipulated fomat ---- #

    def list(self, request):
        ret = {'msg':'No parking made.','data':{}, 'status':'ERR'}
        serializer = ParkingSerializer(self.get_queryset(), many=True)
        try:
            data = list_to_dict(serializer.data)
            ret = {"status":"OK", "msg":"ok", "data":data}
        except Exception as e:
            ret['msg'] = "Ups: Internal error. Please try again."
        return Response(ret)

    def retrieve(self, request, pk=None):
        try:
            queryset = Parking.objects.get(pk=self.kwargs.get('pk'))
            serializer = ParkingSerializer(queryset)
            return Response({'msg':"",'data':serializer.data, 'status':'OK'})
        except Exception as e:
            return Response({'msg':'Numbered not registered in system.','data':{}, 'status':'ERR'})

    # For security matters, destroy is denied
    def destroy(self,request):
        ret = {"status":"ERR", "msg": "Denied."}
        return Response(ret, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    # Method overwriten in order to do some aditional checks by the time
    # of saving the model instance.
    def create(self,request):
        """
            In:
                patent : patent that will be Parking
                phone : phone of user that is parking
                phone_reseller : phone of reseller that will park someones car
                duration : duration of parking
                block_code : code of block where the car is going to park.

            Pueden pasar las situaciones, suponiendo que A es un usuario y B un reseller.
            There can be 3 situations (A user, B reseller):
            1) A park himeslf, we receive phone and patent of A
            2) B parks A, we receive only A's patent, and B's phone
            3) B parks A, we receive A's patent and phone. And B's phone
        """

        data = {}
        ret = {'status': 'ERR', 'data': data, 'msg': 'Error obteniendo datos'}

        patent = request.data.get("patent",None)
        phone = request.data.get("phone",None)
        phone_reseller = request.data.get("phone_reseller",None)
        duration = request.data.get("duration",None)
        block_code = request.data.get("block",None)
        # Flags to determine if it is normal parking , or a parking done by a reseller.
        # If it is done by resller, users's phone can be used to send sms for example.
        is_p = False
        is_pr = False

        if not (patent and duration and block_code and (phone or phone_reseller)):
            ret['msg'] = "Error en los datos recibidos."
            return Response(ret)

        if phone_reseller:
            phone_reseller = format_phone(phone_reseller)
            is_pr = True
        if phone:
            phone = format_phone(phone)
            if not is_pr:
                is_p = True

        # ----- check duration format ----- #

        try:
            duration_obj = duration_format_ok(duration)
        except Exception as err:
            ret['msg'] = "%s"%err
            return Response(ret)

        # -----  Users's existence  -----#

        # Depending if it is a self park, or a resller park, we have to check
        # that corresponding users exist. Also, set corresponding user as None
        try:
            if is_pr:
                reseller_obj = self._end_user_exists(phone_reseller)
                if not reseller_obj.is_reseller:
                    ret = {'msg':"Permiso denegado.",'data':{}, 'status':'ERR'}
                    return Response(ret)
                enduser_obj = None
                userspatents_obj = None
            else:
                # User existence and asociation to patent
                enduser_obj = EndUser.objects.get(phone=phone)
                userspatents_obj = UsersPatents.objects.get(user=enduser_obj, patent=patent)
                reseller_obj = None

            block_obj = Block.objects.get(code=block_code)
        except UsersPatents.DoesNotExist:
            ret['msg'] = "Phone "+phone+" and patent "+patent+" not associated."
            return Response(ret)
        except Block.DoesNotExist:
            ret['msg'] = "Block "+block_code+" does not exist."
            return Response(ret)
        except AttributeError as err:
            ret['msg'] = "Internal Error. %s" % (err)
            return Response(ret)

        # ----- patent YA ESTACIONADA? ----- #

        try:
            last_parking = Parking.objects.filter(patent=patent).last()
            if last_parking and last_parking.remaining_time > 0:
                ret['msg'] = "The patent is already parked on block: "+last_parking.block.code+"."
                return Response(ret)
        except Parking.DoesNotExist:
            pass
        except Exception as e:
            ret['msg'] = "Error %s"%(e)
            return Response(ret)

        # ----- Park ----- #

       # zd = zonedetails_nearest_range(block_obj.zone.code)

        kw = {
            'block_code': block_code,
            'block_obj': block_obj,
            'duration': duration,
            'duration_obj': duration_obj,
            'enduser_obj': enduser_obj,
           # 'is_p': is_p,
           # 'is_pr': is_pr,
           # 'last_parking_obj': last_parking,
            'patent': patent,
            'phone': phone,
            'phone_reseller': phone_reseller,
            'reseller_obj': reseller_obj,
            'ret': ret,
           # 'userspatents_obj': userspatents_obj,
           # 'zone_details': zd,
            'zone_code': block_obj.zone.code
        }

        #ret = _park(block_obj,patent,duration_obj,phone,phone_reseller,enduser_obj,reseller_obj)
        #ret = _park(**locals())
        # Call it this way, not to pass the function the entire request, 
        # self variable, that goes into locals(). Also this way, param can be modified
        ret = self._park(self,**kw)

        return Response(ret)

    def update(self, request, pk=None):
        ret = {"status":"ERR", "msg": "Denied."}
        return Response(ret, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def partial_update(self, request, pk=None):
        ret = {"status":"ERR", "msg": "Denied."}
        return Response(ret, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @list_route()
    def last_park(self, request):
        """
            Returns last parking. Result depends on filter passed in the url.
            Returns the last one, no matters when it was.

            Last park of all system: /api/parkings/last_park/
            Last park of a patent: /api/parkings/last_park/?patent=<patent>
            Last park of a block: /api/parkings/last_park/?block=<block_code>
            Last park of a phone: /api/parkings/last_park/?phone=<phone>
        """
        ret = {'msg': "", 'data': {}, 'status': 'ERR'}
        queryset = self.get_queryset()
        try:
            parking = queryset.all().last()
            serializer = ParkingSerializer(parking)
            ret = {'msg':'Parking data.', 'data':serializer.data, 'status':'OK'}
        except Exception as e:
            ret['msg'] = "Error %s"%(e)
        return Response(ret)

    @detail_route(methods=['post'])
    def extend_park(self, request,pk=None):
        """POST: Extend a parking.

          :param str phone: phone of user

          ``POST`` url::

            WS_HOST/api/parkings/<id>/extend_park/
            {
              phone : '<phone>'
            }

          :return: Diccionario JSON.

        """
        ret = {'msg': "", 'data': {}, 'status': 'ERR'}
        phone = request.data.get('phone',None)
        try:
            park = Parking.objects.get(pk=pk)
            user = EndUser.objects.get(phone=phone)
        except Parking.DoesNotExist:
            return Response({'status':'ERR','data':{},'msg':'Parking does not exists'})
        except EndUser.DoesNotExist:
            return Response({'status':'ERR','data':{},'msg':'User does not exists'})
        except Exception as e:
            ret['msg'] = "Error %s"%(e)
            return Response(ret)

        if not park.is_active:
            return Response({'status':'ERR','data':{},'msg':'Parking already finished.'})
        if not park.phone == phone:
            return Response({'status':'ERR','data':{},'msg':'Parking not made.'})

        mins = get_setting_param("mins_extend_park")
        zc = park.block.zone.code
        try:
            parking_cost = self._calc_price_park(zc, mins)
        except Exception as e:
            return Response({'msg': "Error %s"%(e), 'status':"ERR", 'data':{}})

        # Nos fijamos si tiene credits
        if user.credits < parking_cost:
            return Response({'status':'ERR','data':{},'msg':'Not enough credits.'})
        # Si tiene regla de maximo tiempo, vemos si no lo sobrepasa
        if Zone.has_rule(zc,MAXTIME):
            dic = {'start_datetime':datetime.now(),'zone_code':zc}
            dic2 = {'params': dic }
            ret = self._max_time_yes(**dic2)
            if ret.get('status') == "ERR":
                return Response({'status':'ERR','data':{},'msg':'Cannot overflow parking limit.'})

        park.duration = park.duration + timedelta(minutes=mins)
        park.used_credits = park.used_credits + parking_cost
        park.save()
        user.credits = F('credits') - parking_cost
        user.save()
        return Response({'status':'OK','data':{'minutes':mins},'msg':'Parking extended {} minutes, {} extra credits will be charged.'.format(mins,int(parking_cost))})

    @detail_route(methods=['post'])
    def cut_park(self, request,pk=None):
        """POST: Finish a parking before time previously estipulated.

          :param str phone: phone of user doing this action

          ``POST`` url::

            WS_HOST/api/parkings/<id>/cut_park/
            {
              phone : '<phone>'
            }

          :return: Diccionario JSON.

        """
        ret = {'msg': "", 'data': {}, 'status': 'ERR'}
        phone = request.data.get('phone',None)
        try:
            park = Parking.objects.get(pk=pk)
            user = EndUser.objects.get(phone=phone)
        except Parking.DoesNotExist:
            return Response({'status':'ERR','data':{},'msg':'Parking does not exists'})
        except EndUser.DoesNotExist:
            return Response({'status':'ERR','data':{},'msg':'User does not exists'})
        except Exception as e:
            ret['msg'] = "Error %s"%(e)
            return Response(ret)

        if not park.is_active:
            return Response({'status':'ERR','data':{},'msg':'Parking already finished.'})
        if not park.phone == phone:
            return Response({'status':'ERR','data':{},'msg':'Parking not done by you.'})

        # Calculate how much are remaining minutes, and return to account
        if park.used_credits > 0:
            credits_returned = int((park.used_credits * park.remaining_time) / (park.duration.total_seconds()/60))
            park.used_credits = F('used_credits') - credits_returned
            user.credits = F('credits') + credits_returned
            park.duration = F('duration') - timedelta(minutes=park.remaining_time)
            user.save(update_fields=['credits'])
            park.save(update_fields=['duration','used_credits'])
            ret['msg'] = "Parking cancelled, you have {} credits returned to you account.".format(credits_returned)
        else:
            credits_returned = 0
            park.duration = F('duration') - timedelta(minutes=park.remaining_time)
            park.save(update_fields=['duration'])
            ret['msg'] = "Parking cancelled."

        ret['status'] = "OK"
        return Response(ret)


    def _get_active_users(self,qset):
        """
            Get active users, those who are "parked correctly"

            INPUT : queryset of parkings
            OUTPUT : queryset of parkings filtered
        """
        now = datetime.now()
        active_list = []
        for park in qset:
            if park.is_active:
                active_list.append(park.id)

        return qset.filter(id__in=active_list)

    @list_route()
    def current_count(self, request):
        """
            Return all parks of all blocks, grouped by block code. Only those who are active or parked correctly
            
            How to know if one parking is active?. Calculate it with start time and duration.
            If start time + duration > now => OK
        """
        data = {}
        ret = {'msg':'','data':data, 'status':'ERR'}
        # TODO : Change this for a more optimized version, for example querying for the last 2 days.
        # Or split tables , and that will be done automatically. We are not initerested (almost never in 
        # who parked 4 days ago in here, only the today and maybe yesterday parkings are relevant)
        qset = self.get_queryset()
        active_qset = self._get_active_users(qset)
        l = [obj.block.code for obj in active_qset]
        # Count occurrence of each element: >>> Counter(l) -->  Counter({'0100': 1, '0101': 1})
        res = Counter(l)
        ret['data'] = res
        ret['status'] = "OK"
        """
            If we want to return data grouped by block instead of counter, uncomment following lines and done.
        """
        # serializer = ParkingSerializer(qset, many=True)
        # try:
            # data = list_to_dict_block__code(serializer.data)
            # ret = {'msg': "parkings actuales de todas las blocks.", 'data': data, 'status': 'OK'}
        # except Exception as err:
            # ret['msg']= "{}".format(err)
        return Response(ret)

    @list_route()
    def active_parks(self,request):
        """
            Returns amount of active parkers 
           
            Example of calls
               All actives:       /api/parkings/active_parks/
               actives of a block:   /api/parkings/active_parks/?block="0101"
               actives of a phone:  /api/parkings/active_parks/?phone="+543416111111"
               actives of a patent:  /api/parkings/active_parks/?patent=AA000AA

            In data will come something like this (219, 225, are parking ids) :
            "data": {
                "count": 1,
                "parkings": {
                        "219": { data of this parking },
                        "225": { data of this parking },
                        .....
                        }
                    }
        """

        data = {}
        ret = {'msg':'','data':data, 'status':'ERR'}
        qset = self.get_queryset()
        active_qset = self._get_active_users(qset)
        if active_qset:
            # max_parkings = Block.objects.get(code=code).total_cars_max_occupation
            # estimate_parkings = Occupationblock . .
            serializer = ParkingSerializerShort(active_qset, many=True)
            data = list_to_dict(serializer.data)
            return Response({'msg':"Curent parks.",'data':{'count':active_qset.count(), 'parkings':data}, 'status':'OK'})
        else:
            return Response({'msg':"No parking corresponding to inputdata.",'data':{}, 'status':'OK'})

    @list_route()
    def parks_now(self,request):
        """
            Parking can be:
                GREEN : Active, into estipulated time
                YELLOW : Into 15 minutes after finished parking. (if activated for zone)
                RED : Already fined in that block.

            Examples of calls
                /api/parkings/parks_now/?block="0101"

            In data will come like this (219, 225, are ids of parking) :
            "data": {
                "count": 1,
                "green": {
                        "219": {data of this parking },
                        "225": {data of this parking },
                        .....
                        },
                "yellow": {
                        "211": {data of this parking },
                    },
                "red": {
                        "214": {data of this parking },
                    }
        """

        data = {}
        ret = {'msg':'','data':data, 'status':'ERR'}
        block = self.request.query_params.get('block',None)
        b = Block.objects.get(code=block)
        if not block:
            ret['msg'] = "Must send block code."
            return Response(ret)

        qset = Parking.objects.filter(block__code=block)

        # ----- Zone has grae time activated? ----- #
        has_gt = False
        if Zone.has_rule(b.zone.code,GRACETIME):
            has_gt = True

        dd_g = {}
        dd_y = {}
        dd_r = {}
        gt = get_setting_param("grace_time_mins")
        distant_between_faults = get_setting_param("hours_bt_faults")
        for park in qset:
            if park.is_active:
                dd_g[park.id] = ParkingSerializerShort(park).data
            elif (park.remaining_time*-1) < gt:
                dd_y[park.id] = ParkingSerializerShort(park).data
            else:
                # If it has faults in between last X hors, mark it as it has been done a fault,
                # in order to not make it again in the future if another inspector check again,
                fbtt = Fault.faults_in_time(park.patent,distant_between_faults)
                if fbtt.count() > 0:
                    dd_r[park.id] = ParkingSerializerShort(park).data
                    dd_r[park.id]['ticket_date'] = fbtt.last().date_creation

        data['g'] = dd_g
        data['y'] = dd_y
        data['r'] = dd_r
        return Response({'msg':"",'data':data, 'status':'OK'})

    def _calc_price_park(self,zone_code, minutes, start_datetime=None,**kwargs):
        if not start_datetime:
            start_datetime = datetime.now()
        parking_cost = calc_price_parking(zone_code, minutes, start_datetime)
        return parking_cost

    def _end_user_exists(self,phone):
        try:
            usr = EndUser.objects.get(phone=phone)
        except EndUser.DoesNotExist:
            ret['msg'] = "Phone "+phone+" not registered"
            return ret
        except AttributeError as err:
            ret['msg'] = "Internal Error. %s" % (err)
            return ret
        return usr

    def _park_user(self,**kwargs):
        params = kwargs.get('params')

        block = params.get('block_obj',None)
        patent = params.get('patent',None)
        duration = params.get('duration_obj',None)
        phone = params.get('phone',None)
        phone_reseller = params.get('phone_reseller',None)
        parking_cost = params.get('parking_cost',None)
        usr = params.get('usr',None)

        if not(block and patent and duration and parking_cost is not None and usr and (phone or phone_reseller)):
            raise Exception("Internal error: Parametros de parking")

        p = Parking()
        p.block = block
        p.patent = patent
        if phone:
            p.phone = phone
        if phone_reseller:
            p.phone_reseller = phone_reseller
        p.duration = duration
        p.used_credits = parking_cost
        usr.credits = F('credits') - parking_cost
        usr.save()
        p.save()
        queryset = Parking.objects.get(pk=p.id)
        serializer = ParkingSerializer(queryset)
        ret = {"status":"OK", "msg": "parking correcto.", "data":serializer.data}
        params['ret'] = ret
        return params

    def _park(self,*args,**kwargs):
        """
            This fuction will load rules form RuleMethod model. We will execite the ones that are active
            for the zone where we are parking. Also if there are other rules for the user or other set 
            that we think we should consider.

            Parameters will come into kwargs, coming from caller.
            
            Parameters:
                block_obj :  Obj of block where thepark is going to be carried out.
                patent : patent that is going to park.
                duration_obj : obj datetime with the duration of the parking.
                phone : phone of end user that will park. Can be null.
                phone_reseller : phone of reseller that will park a client. Can be null.
                enduser_obj : User object, user that will be parked. Can be null.
                reseller_obj : 

            See in function create doc's, why enduser can be null.
        """
        block_obj = kwargs.get('block_obj',None)
        patent = kwargs.get('patent',None)
        duration_obj = kwargs.get('duration_obj',None)
        phone = kwargs.get('phone',None)
        phone_reseller = kwargs.get('phone_reseller',None)
        enduser_obj = kwargs.get('enduser_obj',None)
        reseller_obj = kwargs.get('reseller_obj',None)
        ret = kwargs.get('ret',None)
        zone_code = kwargs.get('zone_code',None)

        if not(block_obj and patent and duration_obj and (enduser_obj or reseller_obj) and (phone or phone_reseller)):
            raise Exception("Internal error: Parametros de parking")

        if not ret:
            data = {}
            ret = {'status': 'ERR', 'data': data, 'msg': 'Error obteniendo datos'}
        else:
            data = ret.get('data',{}) or {}
            ret['data'] = data
        kwargs['ret'] = ret

        # ----- Calculate who is gogint to pay. -----#

        if enduser_obj:
            usr = enduser_obj
        else:
            usr = reseller_obj
        kwargs['usr'] = usr

        # ----- Obtain rules and order them ----- #

        """
        >>> r = zd.rules.order_by('stage','order')
        >>> r
        <QuerySet [<RuleMethod: [Park] Hoy no se cobra parking a nadie.>, <RuleMethod: [Park] Prueba para sort 2>, <RuleMethod: [Park] Prueba para sort>, <RuleMethod: [Park] No hay limite de tiempo para Park>]>
        >>> dd = defaultdict(list)
        >>> for rule in r:
        ...    dd[rule.stage].append(rule)
        ...
        >>> dd
        defaultdict(<class 'list'>, {2: [<RuleMethod: [Park] Hoy no se cobra parking a nadie.>, <RuleMethod: [Park] Prueba para sort 2>, <RuleMethod: [Park] Prueba para sort>], 3: [<RuleMethod: [Park] No hay limite de tiempo para Park>]})
        >>> od = OrderedDict(sorted(dd.items(), key=lambda t: t[0]))
        >>> od
        OrderedDict([(2, [<RuleMethod: [Park] Hoy no se cobra parking a nadie.>, <RuleMethod: [Park] Prueba para sort 2>, <RuleMethod: [Park] Prueba para sort>]), (3, [<RuleMethod: [Park] No hay limite de tiempo para Park>])])
        >>> for k,v in od.items():
        ...   pprint(v)
        ...
            [<RuleMethod: [Park] Hoy no se cobra parking a nadie.>,
            <RuleMethod: [Park] Prueba para sort 2>,
            <RuleMethod: [Park] Prueba para sort>]
            [<RuleMethod: [Park] No hay limite de tiempo para Park>]
        """

        # Split them in stages, and ordered by the order field
        zone_rules = block_obj.zone.rules.filter(action='Park').order_by('stage','order')
        dd = defaultdict(list)
        dd2 = defaultdict(list)
        for rule in zone_rules:
            dd[rule.stage].append(rule) if rule.pre_exec else dd2[rule.stage].append(rule)
        # Ordered dict, to ensuer that they will be traversed in order.
        rules_pre_exec = OrderedDict(sorted(dd.items(), key=lambda t: t[0]))
        rules_post_exec = OrderedDict(sorted(dd2.items(), key=lambda t: t[0]))

        # ----- Flags ----- #
        # Do we haveto calculate available credits?
        kwargs['credit_ok'] = False
        # If there is free day , this will be cero. If not , some function will modify this param
        kwargs['parking_cost'] = 0

        # Create new copu, so we can pass and modify among functions
        dic = {'params':kwargs}

        # ----- Rules PRE_EXEC ----- #

        # For each stage, execute correspoding function
        # If the function returns OK, continue (or cut if it is marked to cut exec)
        # If ok is not returned, some condition is not accomplished
        # Return ret to create function, the one that calls _park.
        for k,r in rules_pre_exec.items():
            for rule in r:
                # Look in self, the mapping rule.method in the dictonary that maps
                # int to function name.
                f = getattr(self,self.CALL_MAP.get(rule.method,""),None)
                if not f:
                    return {'status': 'ERR', 'data': {}, 'msg': 'Error en etapa de parking: '+str(rule.stage)+'. Por favor avise al municipio.'}
                else:
                    # **dic, converts this dic to name dargs. And there will be params=kwargs
                    ret = f(**dic)
                    if ret.get('ret').get('status') == 'OK':
                        dic = {'params': ret} # With this we pass data among funcs
                        if rule.cut_exec: # Cut stage exec?
                            break
                    else:
                        return ret.get('ret')

        # ----- See if user has enough credits ----- #
        #       If it is not calculated by some rule before

        if not dic.get('params').get('credit_ok',None):
            credits = usr.credits
            minutes_parked = round(duration_obj.total_seconds()) / 60
            try:
                parking_cost = self._calc_price_park(zone_code, minutes_parked, datetime.now())
                kwargs['parking_cost'] = parking_cost
            except Exception as e:
                return {'msg': "Error %s"%(e), 'credits':credits, data:{}}

            if parking_cost > credits:
                return {'msg':"Sus créditos no son suficientes para do el parking." , 'credits':credits, data:{}}

        # -----  Main func: Park and reorder asociations ---- #

        try:
            ret = self._park_user(**dic)
            UsersPatents.reorder_asociations(patent,phone)
        except Exception as err:
            ret['msg'] = "Error. %s" % (err)
            return ret

        # ----- Rules POST_EXEC ----- #

        dic = {'params': ret}
        if ret.get('ret').get('status') == 'OK':
            for k,r in rules_post_exec.items():
                for rule in r:
                    f = getattr(self,self.CALL_MAP.get(rule.method,""),None)
                    if not f:
                        ret = {'status': 'OK', 'data': {}, 'msg': 'Usted estaciono correctamente, pero hubo otro error en etapa de parking: '+str(rule.stage)+'. Por favor avise al municipio.'}
                        return ret
                    else:
                        ret = f(**dic)
                        if ret.get('ret').get('status') == 'OK':
                            dic = {'params': ret}
                            if rule.cut_exec:
                                break
                        else:
                            return ret.get('ret')

        ret['ret']['status'] = "OK"
        ret['ret']['msg'] = "Parked ok"
        # sino de las reglas post exec.
        return ret.get('ret')


    def _notify_strong_users(self,**kwargs):
        params = kwargs.get('params')
        patent = params.get('patent',None)
        phone = params.get('phone',None)
        # ----- send sms to asoc users ---- #
        msg = "El vehiculo de matricula "+str(patent)+" fue estacionado por el numero de phone "+str(phone)+"."
        UsersPatents.send_msg_to_strong_asoc(patent,phone,msg)
        params['ret'] = {'status': 'OK', 'data': {}, 'msg': ''}
        return params

    def _max_time_yes(self,**kwargs):
        params = kwargs.get('params')
        sd = params.get('start_datetime',None)
        zone_code = params.get('zone_code',None)

        # ---- See if duration is less or eq than allowed in zone --#
        zd = zonedetails_nearest_range(zone_code, sd)

        # Calc intersection of time between park and max allowed
        # If it overflows it.
        # Because for example, if someone parks at 2.3pm for an hour, and start chargin after 15
        # There is half an hour that will not count for chargin.

        time_end = (datetime.now() + timedelta(minutes=minutes_parked)).time()
        if time_end > zd.hour_init:
            uno = datetime.strptime("{}:{}:00".format(zd.hour_init.hour,zd.hour_init.minute),'%H:%M:%S')
            dos = datetime.strptime("{}:{}:00".format(time_end.hour,time_end.minute),'%H:%M:%S')
            minutes_intersected = (dos - uno).total_seconds() / 60
        else:
            minutes_intersected = 0

        if zd.max_minutes and zd.max_minutes < minutes_intersected:
            ret = {"status":"ERR", "msg": "Max time allowed surpased.",'data':{}}
            params['ret'] = ret
            return params
        params['ret'] = {'status': 'OK', 'data': {}, 'msg': ''}
        return params

    # ----- Finish if rules are created ----- #

    def _max_time_no(self,**kwargs):
        params = kwargs.get('params')
        params['ret'] = {'status': 'OK', 'data': {}, 'msg': ''}
        return params

    def _grace_time(self,**kwargs):
        params = kwargs.get('params')
        params['ret'] = {'status': 'OK', 'data': {}, 'msg': ''}
        return params

    def _free_for_all(self,**kwargs):
        params = kwargs.get('params')
        params['credit_ok']=True
        ret = {"status":"OK", "msg": "", 'data':{}}
        params['ret'] = ret
        return params


def list_to_dict_block__code(lista):
    """
        Transform a list of parkings, convert a dict where the key is block code
        and valua, list with parking data.
    """
    ret = {}
    try:
        for obj in lista:
            clave = obj.get('block').get('code')
            if ret.get(clave, None) is None:
                ret[clave] = []
            ret[clave].append(obj)
        return ret
    except Exception as e:
        raise Exception("Error procesando los datos de parkings.")


def duration_format_ok(duration_str):
    """
        in: String representing duration
        out: Obj timedelta converted from string

        Check if format is correct.
        Check that is multiplus of 15.
        Check that is less than param.
    """
    try:
        t = datetime.strptime(duration_str,"%H:%M:%S")
        duration_obj = timedelta(hours=t.hour, minutes=t.minute, seconds=t.second)
    except Exception as e:
        raise Exception("Formato incorrecto de la duration. Debe ser HH:MM:SS y multiplo de 15 minutes.")

    if not (duration_obj.total_seconds() / 60) % 15 == 0:
        raise Exception("El tiempo de parking debe ser múltiplo de 15 minutes.")

    return duration_obj

