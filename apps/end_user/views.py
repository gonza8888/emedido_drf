# -*- coding: utf-8 -*-
"""
     * retrieve: *
       Obtain a user, through his phone.

     * list: *
       List all the users.

     * create: *
       A user is registered for the first time, we save your profile.

     *login:*
       We received phone and pin, and see if they match the stored info.

     * Penalties: *
       List of fines from a user.

     * recharges: *
       List of user credits recharges.

     * resetpin: *
       The user asks to be sent by SMS again his pin.

     * transfer: *
       A reseller (who is a type of end user), transfers credit to another user.

     * transferFriend: *
       Credit transfer between users.

     * credits_history *
       We obtain data of recharges / transfers of a user

     * faults_pending *
       Missing unpaid faults

     * pay_faults *
       Pay a list of unpaid faults

     * faults *
       List of faults associated with a telephone.
"""

from django.db.models import F
from django.core import serializers
from back_emedido.apps.fault.models import Fault
from back_emedido.apps.fault.serializer import FaultSerializer, FaultSerializerShort
from back_emedido.apps.parking.models import Parking
from back_emedido.apps.end_user.models import EndUser
from back_emedido.apps.end_user.serializer import EndUserSerializer, EndUserSerializerAll
from back_emedido.apps.recharge_card.models import RechargeCard
from back_emedido.apps.recharge_card.serializer import RechargeCardSerializer, RechargeCardSerializerHistory
from back_emedido.apps.users_x_patents.models import UsersPatents
from back_emedido.apps.auth_token.models import AuthToken
from back_emedido.apps.transfers.models import Transfers
from back_emedido.apps.transfers.serializer import TransfersSerializer
from back_emedido.apps.payment_mp.models import PaymentMp
from back_emedido.apps.payment_mp.serializer import PaymentMpSerializerAll , PaymentMpSerializerShort
from back_emedido.settings.common import INIT_TRIES
from back_emedido.helpers import list_to_dict, gen_random_num_of_length, format_phone, calc_amount_recharged,get_setting_param
from back_emedido.apps.sms.views import enviar_sms_list
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.cache import never_cache
from back_emedido.decorators import is_reseller
from rest_framework.decorators import detail_route
from rest_framework import mixins, viewsets
from rest_framework.response import Response
from django.db.models import Q
import json
#from back_emedido.permissions import IsDjangoUser

class EndUserViewSet(mixins.CreateModelMixin,
           mixins.ListModelMixin,
           mixins.RetrieveModelMixin,
           viewsets.GenericViewSet):

    queryset = EndUser.objects.all()
    serializer_class = EndUserSerializer
    lookup_field = "phone"

    def list(self, request):
        """List of users in system

          ``GET`` api url is::

            WS_HOST/api/endusers/


          :return: JSON dictionary.

          ``JSON Dictionary`` returned::

            {
              'status' : <string>,
              'data'   : <dict>,
              'msg'    : <string>,
            }


          :rtype:
            :status: 'ERR' or 'OK'
            :msg: String , with a message we want to return to caller of WS
            :data: Dict of dicts. Each object is an user. Model : EndUser_

        """
        ret = {'msg':'No users on system.','data':{}, 'status':'ERR'}
        serializer = EndUserSerializer(self.get_queryset(), many=True)
        try:
            data = list_to_dict(serializer.data)
            ret = {"status":"OK", "msg":"ok", "data":data}
        except Exception as e:
            ret['msg'] = "Internal error. Try again."
        return Response(ret)

    def retrieve(self, request, phone=None):
        """Obtain an user through his phone number

          :param str phone: Phone of user we want to obtain.

          ``GET`` url::

            WS_HOST/api/endusers/{phone}/


          :return: JSON Dictionary.

          ``JSON Dictionary`` returned:

            {
              'status' : <string>,
              'data'   : <dict>,
              'msg'    : <string>,
            }


          :rtype:
            :status: 'ERR' or 'OK'
            :msg: String , with a message we want to return to caller of WS
            :data: Dict with data of the user.

        """
        try:
            queryset = EndUser.objects.get(phone=self.kwargs.get('phone'))
            serializer = EndUserSerializer(queryset)
            return Response({'msg':"",'data':serializer.data, 'status':'OK'})
        except Exception as e:
            return Response({'msg':'Number not registerd in system.','data':{}, 'status':'ERR'})

    def create(self, request):
        """POST : Create end user

          :param str phone: Phone of user we will createo
          :param str name: Name
          :param str surname: Surname.
          :param str dni: id number
          :param str dni_type: Type of id. We can see posibilities in EndUser_ model
          :param email: 
          :type email: [OPCIONAL] str

          ``POST`` url example::

            WS_HOST/api/endusers/
            {
              'phone' : "+45341667889",
              'name' : "Gonzalo",
              'surname' : "Amadio",
              'dni' : "33873841",
              'dni_type' : "DNI",
              'email' : "gonzalo@gmail.com",
            }


          :return: JSON Dictionary.

          ``JSON Dictionary`` returned::

            {
              'status' : <string>,
              'data'   : <dict>,
              'msg'    : <string>,
            }


          :rtype:
            :status: 'ERR' or 'OK'
            :msg: with a message we want to return to caller of WS
            :data: 

        """
        data = {}
        ret = {'msg':'', 'data':{}, 'status':'ERR'}

        # ----- Get data of post and check them ----- #

        name = request.data.get("name",None)
        phone = request.data.get("phone",None)
        surname = request.data.get("surname",None)
        dni = request.data.get("dni",None)
        dni_type = request.data.get("dni_type",None)
        email = request.data.get("email",None) #optional

        if name is None or phone is None or surname is None or dni is None or dni_type is None:
            ret['msg'] = "Error: missing arguments."
            return Response(ret)

        try:
            phone = format_phone(phone)
            data = { 'phone' : phone }
            request.data['phone'] = phone
        except Exception as err:
            m = "%s"%err
            ret = {'status': 'ERR', 'data': data, 'msg': m }
            return Response(ret)

        # ----- If user exists, do not create and return ----- #
        # ----- If not, we create it and return OK. Also we create the token ----- #
        if EndUser.objects.filter(phone=phone).exists():
            ret = {'status': 'ERR', 'data': data, 'msg': 'Phone already registerd.' }
            return Response(ret)
        else:
            # Create user this wat, to use serializer validators as well.
            pin = gen_random_num_of_length(4)
            request.data['pin'] = pin
            serializer = EndUserSerializerAll(data=request.data)
            if serializer.is_valid():
                serializer.save()
                authobj, created = AuthToken.objects.update_or_create(
                    phone=phone,
                    defaults={'token':AuthToken.generate_key(40)}
                )
                pin = str(pin)
                txt = "You have been registerd in SimplE. Your pin is: "+pin
                enviar_sms_list([(None,str(phone),txt)])
                ret['status'] = 'OK'
                ret['msg'] = 'User created. Your pin should arrive by sms in a moment.'
                ret['data'] = {'token': authobj.token}
            else:
                for item in serializer.errors:
                    ret['msg'] += serializer.errors.get(item)[0] + " "
        return Response(ret)


#   /api/endusers/+543415142341/recharges/
    @detail_route(methods=['get'])
    def recharges(self, request, phone=None):
        """GET: History of phone credit recharges. For now, only of cards. If we pass a non existent phone return []

          ``GET`` url:

            WS_HOST/api/endusers/{phone}/recharges/

          :return: JSON Dictionary.

          ``JSON Dictionary`` returned::

            {
              'status' : <string>,
              'data'   : <dict>,
              'msg'    : <string>,
            }

          :rtype:
            :status: 'ERR' or 'OK'
            :msg: with a message we want to return to caller of WS
            :data: Dict of dicts. Each object is a recharge done by user.

        """
        ret = {'msg':'No recharges done from this number.','data':{}, 'status':'ERR'}
        try:
            cards_set=RechargeCard.objects.filter(end_user__phone=phone).exclude(date_activated=None)
            data=RechargeCardSerializer(cards_set, many=True).data
            if data:
                data = list_to_dict(data)
                ret={'msg':"",'data':data, 'status':'OK'}
        except Exception as e:
            ret['msg'] = "Internal error. Try again."
        return Response(ret)

    @never_cache
    @detail_route(methods=['post'])
    def login(self, request, phone=None):
        """POST: Get phone and pin and check if they match.

          :param str phone: Phone of user
          :param int pin: Pin (password).
          :param bool is_reseller: Flag that tell uf it is a reseller or not.

          ``POST`` url::

            WS_HOST/api/endusers/{phone}/login/
            {
              'pin': 1234,
              'is_reseller': True o False
            }


          :return: JSON Dictionary.

          ``JSON Dictionary`` returned::

            {
              'status' : <string>,
              'data'   : <dict>,
              'msg'    : <string>,
            }


          :rtype:
            :status: 'ERR' or 'OK'
            :msg: with a message we want to return to caller of WS
            :data: If login ok: {} . if not : {'token':<token>,'phone':<phone>}

        """
        ret = {'msg':"",'data':{}, 'status':'ERR'}
        pin = request.data.get('pin')
        is_res = request.data.get('is_reseller',None)

        if not pin:
            ret['msg'] = "No pin received, try again."
            return Response(ret)

        try:
            phone = format_phone(phone)
            enduser = EndUser.objects.get(phone=phone)

            if is_res and not enduser.is_reseller:
                ret['msg'] = "Acceso Denegado."
                return Response(ret)

            if enduser.locked:
                ret['msg'] = "Blocked account. Please contact the people in charge of the application."
            elif enduser and enduser.pin:
                if int(enduser.pin) == int(pin):
                    #enduser.locked = False
                    if enduser.init_tries != 0:
                        enduser.init_tries = 0
                        enduser.save()
                    # Create token to validate request.
                    # Maybe it is already created, we refresh it
                    authobj, created = AuthToken.objects.update_or_create(
                        phone=phone,
                        defaults={'token':AuthToken.generate_key(40)}
                    )
                    data = {'phone':phone, 'token':authobj.token}
                    ret = {'msg':"Login ok",'data':data, 'status':'OK'}
                else:
                    if enduser.init_tries == INIT_TRIES-1:
                        ret = {'msg':"Pin incorrecto. Se ha bloqueado su cuenta.",'data':{}, 'status':'ERR'}
                        enduser.locked = True
                    elif enduser.init_tries >= INIT_TRIES:
                        ret = {'msg':"Account blocked. Please contact the people in charge of the application.",'data':{}, 'status':'ERR'}
                    else:
                        ret = {'msg':"Incorrect pin.",'data':{}, 'status':'ERR'}

                    enduser.init_tries += 1
                    enduser.save()
            else:
                ret['msg'] = "The user has no pin assigned. Please contact the people in charge of the application."
                ret['status'] = "ERR"
        except EndUser.DoesNotExist:
            ret['msg'] = "User not registerd."
        except Exception as err:
            ret['msg'] = "An error occurred while trying to check the number pin. Try again."
        return Response(ret)

    @detail_route(methods=['post'])
    @never_cache
    def resetpin(self, request, phone=None):
        """POST:  The user want to reset ping. With this WS, create new one and sent by sms.

          :param str phone: phone of usr

          ``POST`` url::

            WS_HOST/api/endusers/{phone}/resetpin/


          :return: JSON Dictionary.

          ``JSON Dictionary`` returned::

            {
              'status' : <string>,
              'data'   : <dict>,
              'msg'    : <string>,
            }


          :rtype:
            :status: 'ERR' or 'OK'
            :msg: with a message we want to return to caller of WS
            :data: {}

        """
        ret = {'msg':"",'data':{}, 'status':'ERR'}
        try:
            enduser = EndUser.objects.get(phone=phone)
            new_pin = gen_random_num_of_length(4)
            new_pin = str(new_pin)
            enduser.pin = new_pin
            enduser.save()
            txt = new_pin+" Tu nuevo pin SimplE"
            enviar_sms_list( [(None, str(phone),txt)] )
            ret['msg'] = "New pin created and sent by SMS to the indicated number."
            ret['status'] = "OK"
        except EndUser.DoesNotExist:
            ret['msg'] = "User does not exists."
        except Exception as err:
            ret['msg'] = "Error sending pin by SMS to "+phone+". Try again please."
        return Response(ret)

    @detail_route(methods=['post'])
    def transfer(self, request, phone=None):
        """POST: Reseller, transfer money to client

          :param str phone: 
          :param str phone_client: Phone of user that will receive the credits.
          :param int credits: amount of credits to transfer..

          ``POST`` url::

            WS_HOST/api/endusers/{phone}/transfer/
            {
              'phone_client': "+4593415667778",
              'credits': 10
            }


          :return: JSON Dictionary.

          ``JSON Dictionary`` returned::

            {
              'status' : <string>,
              'data'   : <dict>,
              'msg'    : <string>,
            }


          :rtype:
            :status: 'ERR' or 'OK'
            :msg: with a message we want to return to caller of WS
            :data: {}

        """
        ret = {'msg':"",'data':{}, 'status':'ERR'}

        # ----- Get request data and check ----- #
        # We receive: Patent that will park, phone (must asoc to the patent),
        # duration (HH:MM:SS), block code 
        
        user_from_phone = phone
        to_friend = request.data.get("to_friend", False)
        user_to_phone = request.data.get('user_to',None)
        credits = request.data.get("credits",None)
        credits = float(credits)

        if not (user_to_phone and credits):
            ret['msg'] = "All parameters needed."
            return Response(ret)

        if user_to_phone == user_from_phone:
            ret['msg'] = "Can not transfer to your number."
            return Response(ret)

        user_to_phone = format_phone(user_to_phone)

        # ----- User exists? ----- #

        try:
            user_from = EndUser.objects.get(phone=user_from_phone)
            user_to = EndUser.objects.get(phone=user_to_phone)
        except EndUser.DoesNotExist:
            ret['msg'] = "Phone "+user_to_phone+" do not have registered account."
            return Response(ret)
        except AttributeError as err:
            ret['msg'] = "Error. %s" % (err)
            return Response(ret)

        # ----- Reseller has enough credits ----- #

        user_from_credits = user_from.credits
        if credits > user_from_credits:
            ret['msg'] = "Credits not enough to make this transfer."
            return Response(ret)

        # ----- Transfer ----- #
        try:
            # Obtain value with F operator and save. If ok, then we park
            user_from.credits = F('credits') - credits
            user_from.save()
            if to_friend == False:
                amount_recharged = calc_amount_recharged(credits)
            else:
                amount_recharged = credits
            user_to.credits = F('credits') + amount_recharged
            user_to.save()

            # ifit is from resller
            if to_friend == False:
                res_hist = Transfers(user_from=user_from, user_to=user_to, credits=credits, credits_transfered=amount_recharged, is_reseller=True)
                res_hist.save()
            else:
                # if it is from end user
                res_hist = Transfers(user_from=user_from, user_to=user_to, credits=0, credits_transfered=amount_recharged, is_reseller=False)
                res_hist.save()
        except Exception as err:
            ret['msg'] = "Error. %s" % (err)
            return Response(ret, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            if to_friend == False:
                ret = {"status":"OK", "msg": "Transfer done to client.", "data":{}}
            else:
                ret = {"status":"OK", "msg": "Transfer done.", "data":{}}
        return Response(ret)

    @detail_route()
    def credits_history(self, request, phone=None):
        """GET: Obtain data of recharges/transfers of a user.

          :param str phone: 

          ``GET`` url::

            WS_HOST/api/endusers/{phone}/credits_history/

          :return: JSON Dictionary.

          ``JSON Dictionary`` returned::

            {
              'status' : <string>,
              'data'   : <dict>,
              'msg'    : <string>,
            }

          :rtype:
            :status: 'ERR' or 'OK'
            :msg: with a message we want to return to caller of WS
            :data: Dict of dicts. Key : id of transfer, Value: Dict with model field.

        """
        ret = {'msg':"",'data':{}, 'status':'ERR'}
        filter = request.GET.get('filter', 'all').lower()
        last = request.GET.get('last', None)
        data = {
          'recharges_card': None,
          'by_reseller': None,
          'payments_mp': None,
          'to_friends': None,
          'from_friends': None
        }
        # si el filtro que enviaron, no está en data.
        if filter != 'all' and filter not in data.keys():
            # Marcamos por defecto el filtro como 'all'
            filter = 'all'

        try:
            phone = format_phone(phone)
            user = EndUser.objects.get(phone=phone)
        except EndUser.DoesNotExist:
            ret['msg'] = "phone "+phone+" do not have registered account."
            return Response(ret)
        except AttributeError as err:
            ret['msg'] = "Error accesing data in query. %s" % (err)
            return Response(ret)
        # Obtain historial.
        try:
            if filter == 'all' or filter == 'recharges_card':
                # Recharges con cards.
                recharges_set = RechargeCard.objects.filter(end_user__phone=phone).exclude(date_activated=None)
                recharges_card = RechargeCardSerializerHistory(recharges_set, many=True)
                data['recharges_card'] = list_to_dict(recharges_card.data)

            if filter == 'all' or filter == 'by_reseller':
                # Recharges from agent (transfer from un reseller).
                transfers_set = Transfers.objects.filter(user_to__phone=phone, is_reseller=True)
                by_reseller = TransfersSerializer(transfers_set, many=True)
                data['by_reseller'] = list_to_dict(by_reseller.data)

            if filter == 'all' or filter == 'payments_mp':
                # Recharges from MercadoPago (payment from the app).
                mp_recharges = PaymentMp.objects.filter(end_user__phone=phone)
                payments_mp = PaymentMpSerializerShort(mp_recharges, many=True)
                data['payments_mp'] = list_to_dict(payments_mp.data)

            if filter == 'all' or filter == 'to_friends':
                # transfer to other user.
                to_friend_transfers = Transfers.objects.filter(user_from__phone=phone, is_reseller=False)
                to_friends = TransfersSerializer(to_friend_transfers, many=True)
                data['to_friends'] = list_to_dict(to_friends.data)

            if filter == 'all' or filter == 'from_friends':
                from_friend_transfers = Transfers.objects.filter(user_to__phone=phone, is_reseller=False)
                from_friends = TransfersSerializer(from_friend_transfers, many=True)
                data['from_friends'] = list_to_dict(from_friends.data)

            # Recorremos el objeto data
            for item in data.keys():
                # Si el objeto, fue llenado con algo y no es None:
                if data[item] is not None:
                    # Lo agregamos al objeto que vamos a devolver.
                    ret['data'][item] = data[item]
        except Exception as err:
            ret['msg'] = "Error. %s" % (err)
            print(err)
            return Response(ret, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            ret['msg'] = 'Data obtained ok.'
            ret['status'] = 'OK'
            return Response(ret)

    # Regex accpets this two styles of patents: AA000AA, o AAA000
    # TODO : Gives me error, but do not know why yet
    #@detail_route(methods=['get'], url_path='faults/(?P<patent>[a-zA-Z]{2,2}[0-9]{3,3}[a-zA-Z]{2,2}|[a-zA-Z]{3,3}[0-9]{3,3})')
    @detail_route(methods=['get'], url_path='faults/(?P<patent>[0-9,A-Z]+)')
    def faults_pending(self, request, phone=None,patent=None):
        """GET: Faults not payed by user

          :param str phone: 

          ``GET`` url::

            WS_HOST/api/endusers/+543416114766/faults/


          :return: JSON Dictionary.

          ``JSON Dictionary`` returned::

            {
              'status' : <string>,
              'data'   : <dict>,
              'msg'    : <string>,
            }


          :rtype:
            :status: 'ERR' or 'OK'
            :msg: with a message we want to return to caller of WS
            :data: Dict of dicts. Key: id of fault, Value: dict with data of each fault.

        """
        ret = {'msg':'','data':{}, 'status':'ERR'}
        try:
            UsersPatents.objects.get(user__phone=phone, patent=patent)
        except UsersPatents.DoesNotExist:
            return Response({'msg':'phone and patent not associated.','data':{}, 'status':'ERR'})
        try:
            # Look for unpayed, and not converted to faut.
            fault_set=Fault.active_faults(patent)
            data=FaultSerializer(fault_set, many=True).data
            if data:
                data = list_to_dict(data)
            ret={'msg':"",'data':data, 'status':'OK'}
        except Exception as e:
            ret['msg'] = "Internal error. Try again."
        return Response(ret)


    @detail_route(methods=['post'])
    def pay_faults(self, request, phone=None):
        """POST: Pay list of unpayed faults. All the available credit can pay.

          :param str phone: 

          ``POST`` url::

            WS_HOST/api/endusers/{phone}/pay_faults/
            {
              'id_faults':[id1,id2, . . ]
            }

          :return: JSON Dictionary.

          ``JSON Dictionary`` returned::

            {
              'status' : <string>,
              'data'   : <dict>,
              'msg'    : <string>,
            }


          :rtype:
            :status: 'ERR' or 'OK'
            :msg: Descriptive text 
            :data: Dict of dicts. Each objects is a recharge done by user.

        """
        data = {}
        ret = {'msg':'','data':data, 'status':'ERR'}
        idsl = request.data.get('id_faults')
        if type(idsl) is str:
            import ast
            ids = ast.literal_eval(idsl)
        else:
            ids = idsl

        if not ids:
            ret['msg'] = "No faults received, try again."
            return Response(ret)

        faults = Fault.objects.filter(pk__in=ids).order_by('date_creation')
        faults_np = faults.filter(payed=False).order_by('date_creation')

        try:
            phone = format_phone(phone)
            usr = EndUser.objects.get(phone=phone)
        except EndUser.DoesNotExist:
            ret['msg'] = "User not registered."

        faults_payed = []
        for fault in faults_np:
            amount = fault.amount
            try:
                usr.credits = F('credits') - amount
                usr.save()
                faults_payed.append(fault.id)
                fault.payed = True
                fault.save()
            except:
                break
        try:
            fps = faults.filter(pk__in=faults_payed)
            data = FaultSerializer(fps,many=True).data
            if data:
                data = list_to_dict(data)
            ret={'msg':"Payed {} faults".format(fps.count()),'data':data, 'status':'OK'}
        except Exception as e:
            ret['msg'] = "Error when paying selected faults."

        # ----- If the parameter to send sms is on, we send sms to asociated users

        if get_setting_param("fault_notify_associated"):
            for fault in fps:
                d = fault.date_creation.strftime('%d/%m/%Y %H:%M')
                msg = "Fault done in "+d+", was payed by "+phone+"."
                UsersPatents.send_msg_to_strong_asoc(fault.patent,None,msg)

        return Response(ret)


    @detail_route(methods=['get'])
    def faults(self, request, phone=None):
        """GET: List of faults asoc to a phone. In fact, patents, asoc to a phone

          :param str phone:

          ``GET`` url::

            WS_HOST/api/endusers/+543416114766/faults/[?filter=<option>]

            # Optiones available in filter:
            # Nothing : all
            # active : Faults pending of payment
            # noactive :  Faults payed.

          :return: JSON Dictionary.

          ``JSON Dictionary`` returned::

            {
              'status' : <string>,
              'data'   : <dict>,
              'msg'    : <string>,
            }

          :rtype:
            :status: 'ERR' or 'OK'
            :msg: with a message we want to return to caller of WS
            :data: Dict of dicts. Each obj is a fault according flter

        """
        data = {}
        ret = {'msg':'','data':data, 'status':'ERR'}
        filt = self.request.query_params.get('filter',None)
        try:
            asocs = UsersPatents.get_asociations(phone=phone)
        except Exception as err:
            ret['msg']= 'Error associating phones.'
            return Response(ret)
        ret = {}
        for asoc in asocs:
            patent = asoc.patent
            if filt == "noactive":
                faults = Fault.objects.filter(patent=patent).filter(Q(payed=True)|Q(to_penalty=True))
            elif filt == "active":
                faults = Fault.objects.filter(patent=patent,payed=False,to_penalty=False)
            else:
                faults = Fault.objects.filter(patent=patent)
            for fault in faults:
                data[fault.id] = FaultSerializerShort(fault).data

        ret = {'msg':'','data':data, 'status':'OK'}
        return Response(ret)
