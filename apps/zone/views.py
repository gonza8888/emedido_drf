# -*- coding: utf-8 -*-
from back_emedido.apps.zone.models import Zone
from back_emedido.apps.zone.serializer import ZoneSerializer
from rest_framework import viewsets
from rest_framework.response import Response
from back_emedido.helpers import list_to_dict
from rest_framework.decorators import detail_route
from datetime import datetime, time, timedelta
#from back_emedido.permissions import IsDjangoUser
from back_emedido.apps.rule_callable.rules import GRACETIME,MAXTIME

class ZoneViewSet(viewsets.ReadOnlyModelViewSet):
    """
        This viewset automatically provides `list`, `retrieve`,
        To insert, do it from djando admin.
    """
    queryset = Zone.objects.all()
    serializer_class = ZoneSerializer
    lookup_field = "code"

    def list(self, request):
        ret = {'msg':'No zones in system.','data':{}, 'status':'ERR'}
        serializer = ZoneSerializer(self.get_queryset(), many=True)
        try:
            data = list_to_dict(serializer.data)
            ret = {"status":"OK", "msg":"ok", "data":data}
        except Exception as e:
            ret['msg'] = "Ups: Internal error. Please try again."
        return Response(ret)

    def retrieve(self, request, code=None):
        try:
            queryset = Zone.objects.get(code=self.kwargs.get('code'))
            serializer = ZoneSerializer(queryset)
            return Response({'msg': "",'data': serializer.data, 'status':'OK'})
        except Exception as e:
            return Response({'msg':'This zone is not in the system.','data':{}, 'status':'ERR'})


    @detail_route(methods=['get'],url_path='get_price/(?P<minutes>[0-9]+)')
    def get_price(self, request, code=None, minutes=None):
        """
            Calc of price of parking
        """
        start_datetime = datetime.now()
        try:
            minutes = int(minutes)
            price = calc_price_parking(code,minutes,start_datetime)
            ret={'msg':"",'data':price, 'status':'OK'}
        except Exception as e:
            ret = {'msg':'Error calculating price.','data':{}, 'status':'ERR'}
        return Response(ret)

    @detail_route(methods=['get'])
    def has_rule(self, request, code=None):
        rule = self.request.query_params.get('rule',None)
        ret={'msg':"",'data':{}, 'status':'ERR'}
        if rule == 'max_time':
            constant = MAXTIME
        elif rule == 'grace_time':
            constant = GRACETIME
        elif rule == 'faults_active':
            constant = FAULT_ACTIVE
        else:
            return Response(ret)

        if Zone.has_rule(code,constant):
            ret={'msg':"",'data':{}, 'status':'OK'}
            return Response(ret)
        else:
            return Response(ret)

def zone_details_for_day(zone_code,day):
    """
        IN:  day and zone, and returns the instance/s of zone_details
        for that day and zone, ordered. Done it looking with "reverse query"

        Obtain every instance of model zone_details, that has a FK to the correspndant zone.
        We will keep with the ones of the day of today (i.e, will have the day=True)
        and ordered by time.

        IN: zone_code : code of a zone
                 day     : int, representing day of week
        OUT: queryset of ZoneDetails corresponding to day and zone
                Example:  <QuerySet [<ZoneDetails: [Microcentro]09:00:00-20:00:00 - 30min->30.0>]>

        Example of a call:
            >>> zone_details_for_day("Macrocentro",1)
            <QuerySet [<ZoneDetails: [Macrocentro]09:00:00-14:00:00 - 30min->20.0>, <ZoneDetails: [Macrocentro]16:30:00-20:00:00 - 30min->20.0>]>
    """
    # zonedetails, it is the "related_field" defined in the model ZoneDetails, in
    # the FK. With tha variable obtain the queryset in reverse way, from one to the many
    zone_details_all = Zone.objects.get(code=zone_code).zonedetails.all()

    if day is 0:
        return zone_details_all.filter(mon=True).order_by('hour_init')
    if day is 1:
        return zone_details_all.filter(tue=True).order_by('hour_init')
    if day is 2:
        return zone_details_all.filter(wed=True).order_by('hour_init')
    if day is 3:
        return zone_details_all.filter(thu=True).order_by('hour_init')
    if day is 4:
        return zone_details_all.filter(fri=True).order_by('hour_init')
    if day is 5:
        return zone_details_all.filter(sat=True).order_by('hour_init')
    if day is 6:
        return zone_details_all.filter(sun=True).order_by('hour_init')


def zonedetails_nearest_range(zone_code, start_datetime=None):
    """
        Obtain detauls of a zone, choosing the next range of tima that is not
        free to park

        I.e., if for example, if now is 2pm, and in the chosen zone parking is charged
        between 3pm and 8pm, this function will return the instance zone_details that has
        that range time.

        IN : Zone code, datetime object
        OUT  : Object ZoneDetails

        Example of call:
            >>> from datetime import datetime
            >>> t = time(2)
            >>> t
            datetime.time(2, 0)
            >>> datetime.now()
            datetime.datetime(2017, 11, 28, 15, 3, 16, 448038)
            >>> zonedetails_nearest_range("Macrocentro")
            <ZoneDetails: [Macrocentro]16:30:00-20:00:00 - 30min->20.0>
            >>> zonedetails_nearest_range("Macrocentro",t)
            <ZoneDetails: [Macrocentro]09:00:00-14:00:00 - 30min->20.0>
    """
    if start_datetime:
        timenow = start_datetime.time()
        day = start_datetime.weekday()
    else:
        # datetime.time(15, 29, 22, 129537)
        timenow = datetime.now().time()
        # Return the day of the week as an integer, where Monday is 0 and Sunday is 6
        day = datetime.today().weekday()

    qset_zonedetails_today = zone_details_for_day(zone_code,day)

    if not qset_zonedetails_today:
        raise Exception("No hay detalles cargado para hoy, revisar")

    # Traverse elements to guess in which we are.If we are at the end  of a day
    # we obtain the first interval of the next day.
    # For example, a "graph" of what would be the range of what is it charged
    # when parking in the day
    # 00hs      8hs     13hs    14hs           20hs      23.59hs
    # ----------|||||||||||-------|||||||||||||||-----------
    zonedetails = None
    for item in qset_zonedetails_today:
        end = item.hour_end
        # See if we are before or after or inside range of current elem.

        # As they are ordered by time, we check if we are before the end of the period
        # as if we are before it starts, we will pick that as wll.
        # (and as they are ordered, if one element has passed, it means that it is
        # after the one that has not alreay passed the condition.
        if timenow < end:
            zonedetails = item
            break;

    # This means that now, is after the last interval where the user hasto pay and the end of today
    # So we pick the first of next day
    if zonedetails is None:
        day += 1
        qset_zonedetails_tomorrow = zone_details_for_day(zone_code,day)
        zonedetails = qset_zonedetails_tomorrow.first()

    return zonedetails

def details_intersected_by_period(zone_code, minutes, start_datetime=None):
    """
        Given a zone, and a queantityin minutes and a date of start(default now()) we obtain the ranges 
        that user has to pay, classified by how they intersect by the period that starts in start date
        and finishes X minutes after
        IN :
            zone_code       String   -   code of zone
            minutes         int      -   quenaity in minutes that the period lasts
            start_datetime  Datetime -   Datetime the period start, default now()
        OUT  :
            ret_included        ZoneDetails - When period of parking is included completely insida a charged range
            ret_init_partial    ZoneDetails - When period interesect partially with a range
            ret_complete        [ZoneDetails] - List of ranges that have to be completely chargend
            ret_end_partial     ZoneDetails - End of period intersect partially a range
    """
    if minutes >= 8640: # 6 dias
        raise Exception("No se puede estacionar por mas de 6 dias")

    if start_datetime:
        # pstart = period start
        pstart = start_datetime
        pstart_time = start_datetime.time()
    else:
        pstart = datetime.now()
        pstart_time = pstart.time()
    # datetime + timedelta = datetime
    pend = pstart + timedelta(minutes=minutes)
    pend_time = pend.time()

    #>>> d1
    #datetime.datetime(2017, 11, 30, 17, 59, 25, 663656)
    #>>> d2
    #datetime.datetime(2017, 12, 4, 0, 39, 25, 663656)
    #>>> (d2.date() - d1.date()).days + 1
    #5
    # Sum one , cause today we want to include it
    amount_of_days = list(range( (pend.date() - pstart.date()).days + 1 ))
    days_in_period = []
    # Save days of the week that are  0 = monday, . . 6 = sunday
    for x in amount_of_days:
        days_in_period.append( (pstart + timedelta(days=x)).weekday() )

    # Basically, what we have to distinguish is which ranges are covered
     # complete, and which partially. In addition to those that are covered
     # completely, at the tips, the beginning or end can cut some
     # range in half, then we have to distinguish them.

    # ---------- Variables that we will return ---------- #

    # The period is included inside complete range (Only can be if period
    # lasts less than a hole day
    ret_included = None
	# Initial range, which is partially touched (may be empty). The range is going to
    # to be partially interesed in the end, ie by Example if the range
    # schedule is between 9 and 11, and the period is from 10 to 12, they are interested in
    # 10 to 11.
    ret_init_partial = None
    # List of ranges that are covered entired by the period
    ret_complete = []
    # List of final range, which is partially touched (may be empty)
    ret_end_partial = None

    # ---------- Calculate and classified periods ---------- #

    # Queryset, with ranges of only a day
    if len(days_in_period) == 1:
        qset = zone_details_for_day(zone_code,days_in_period[0])
        for detail in qset:
            # Case 1: Cover entire range
            if pstart_time < detail.hour_init < detail.hour_end < pend_time:
                ret_complete.append(detail)
            # Case 2 : Period completely included in range
            elif detail.hour_init < pstart_time < pend_time < detail.hour_end:
                ret_included = detail
            # Case 3 : Period intersect partially the end of a range
            elif detail.hour_init < pstart_time < detail.hour_end < pend_time:
                ret_init_partial = detail
            # Case 4 : Period intersect partially the start of a range
            elif pstart_time < detail.hour_init < pend_time < detail.hour_end:
                ret_end_partial = detail
            else:
                continue
                #raise Exception("Algo paso")

    elif len(days_in_period) == 2:
        qset_today = zone_details_for_day(zone_code,days_in_period[0])
        qset_tomorrow = zone_details_for_day(zone_code,days_in_period[1])

		# As we know that it starts today and ends tomorrow, we will filter and
        # stay with the following logic:
        # For today, we are left with all ranges such that the
        # start of the period, this before the end of the range (that is, the period
        # intereseca to the range, or covers it full, or covers a piece of the
        # final)
        # For tomorrow, similar, but in reverse. We are left with
        # the ranges such that the end of the period exceeds the beginning of the range
        # (and may exceed the range completely, or a touch a bit)
        for d in qset_today:
            # Caso 1: Completely covered
            if pstart_time < d.hour_init < d.hour_end:
                ret_complete.append(d)
            # Caso 2: Partially touch end of period
            elif d.hour_init < pstart_time < d.hour_end:
                ret_init_partial = d
            else:
                continue

        for d in qset_tomorrow:
            # Caso 1: Completely covered
            if d.hour_init < d.hour_end < pend_time:
                ret_complete.append(d)
            # Caso 2: Partially touch start of period
            elif d.hour_init < pend_time < d.hour_end:
                ret_end_partial = d
            else:
                continue

    # Queryset with ranges of today, tomorrow and some more days
    elif len(days_in_period) > 2:

    	# If the period lasts more than 2 days, we apply the same logic as
        # when we have two days (for the first and last day), only that the
        # middle days if or if they are going to be included in the period, then
        # full charge.

        qset_today = zone_details_for_day(zone_code,days_in_period[0])
        qset_lastday = zone_details_for_day(zone_code,days_in_period[-1])

        for d in qset_today:
            if pstart_time < d.hour_init < d.hour_end:
                ret_complete.append(d)
            elif d.hour_init < pstart_time < d.hour_end:
                ret_init_partial = d
            else:
                continue

        for d in qset_lastday:
            if d.hour_init < d.hour_end < pend_time:
                ret_complete.append(d)
            elif d.hour_init < pend_time < d.hour_end:
                ret_end_partial = d
            else:
                continue

        del days_in_period[0]
        del days_in_period[-1]
        for d in days_in_period:
            qset = zone_details_for_day(zone_code,d)
            for det in qset:
                ret_complete.append(det)
    else:
        raise Exception("Internal error calculando los periodos abarcados por el parking")

    # Integrity check of function unctionallity, if there is something in ret_included, others must by empty
    if ret_included and (ret_init_partial or ret_complete or ret_end_partial):
        raise Exception("Error de integridad calculando los periodos abarcados por el parking")

    return ret_included,ret_init_partial,ret_complete,ret_end_partial

# ----------------------------------------------------
#>>> details_intersected_by_period("Macrocentro",900,start)
#(Pdb) pstart
#datetime.datetime(2017, 11, 30, 15, 49, 6, 221566)
#(Pdb) qset_today
#<QuerySet [<ZoneDetails: [Macrocentro]09:00:00-14:00:00 - 30min->20.0>, <ZoneDetails: [Macrocentro]16:30:00-20:00:00 - 30min->20.0>]>
#(Pdb) qset_tomorrow
#<QuerySet [<ZoneDetails: [Macrocentro]09:00:00-14:00:00 - 30min->20.0>, <ZoneDetails: [Macrocentro]16:30:00-20:00:00 - 30min->20.0>]>
#(None, None, [<ZoneDetails: [Macrocentro]16:30:00-20:00:00 - 30min->20.0>], <ZoneDetails: [Macrocentro]09:00:00-14:00:00 - 30min->20.0>)
# ----------------------------------------------------
#>>> start = start + timedelta(minutes=50)
#>>> start
#datetime.datetime(2017, 11, 30, 16, 39, 6, 221566)
#>>> details_intersected_by_period("Macrocentro",1100,start)
#(None, <ZoneDetails: [Macrocentro]16:30:00-20:00:00 - 30min->20.0>, [], <ZoneDetails: [Macrocentro]09:00:00-14:00:00 - 30min->20.0>)
# ----------------------------------------------------
#(Pdb) pstart
#datetime.datetime(2017, 11, 30, 16, 42, 45, 617996)
#(Pdb) pend
#datetime.datetime(2017, 12, 4, 19, 12, 45, 617996)
#(Pdb) days_in_period
#[3, 4, 5, 6, 0]
#(Pdb) datetime.now()
#datetime.datetime(2017, 11, 30, 15, 18, 9, 895729)
#(Pdb) datetime.now().weekday()
#3
#(Pdb) c
#(None, <ZoneDetails: [Macrocentro]16:30:00-20:00:00 - 30min->20.0>, [<ZoneDetails: [Macrocentro]09:00:00-14:00:00 - 30min->20.0>, <ZoneDetails: [Macrocentro]09:00:00-14:00:00 - 30min->20.0>, <ZoneDetails: [Macrocentro]16:30:00-20:00:00 - 30min->20.0>], <ZoneDetails: [Macrocentro]16:30:00-20:00:00 - 30min->20.0>)
## En esta zona, sabado y domingo es gratis, por lo que no aparecen periodos para esos dos dias.
#>>> Zone.objects.get(code="Macrocentro").zonedetails.all()
#<QuerySet [<ZoneDetails: [Macrocentro]09:00:00-14:00:00 - 30min->20.0>, <ZoneDetails: [Macrocentro]16:30:00-20:00:00 - 30min->20.0>]>


def calc_price_parking(zone_code, minutes, start_datetime):
    """
        IN: zone code, minutes to calculate, time from which to calculate
        OUT: Float (two decimals) of what those minutes come out in that area.

        We calculate the price of a parking taking into account:
             a) The current time
             b) The duration of the parking
             c) The time ranges in which the current area is paid
                 covers the total of the stacking.

		Obtaining these three data, let's stay with all the areas that
         the total parking "touch", and for each zone, we will have
         any of the following cases:

        We will have 5 cases of what you have to pay for those time ranges.
            Case 1)
                The parking does not touch any time zone that is paid => free

            case 2)
                The parking is totally included within a range
                parking -> ||||||
                range -> --- |||||||||||| -------- |||||||||

            case 3)
                The parking covers the entire area
                parking -> ||||||||||
                range -> -------- |||||| -------- |||||||||

            case 4)
                The parking covers a piece of the end of the area.
                parking -> ||||||||||
                range -> --- ||||||| -------- |||||||||

            case 5)
                The parking covers a piece of the beginning of the area.
                parking -> ||||||||
                range -> --- ||||||| -------- |||||||||

            How are we going to analyze each zone in particular, for example
            if we have a parking lot that is something like this:
                parking -> |||||||||||||||||||
                range -> --- ||||||| -------- |||||||||
            It will end up being the combination by Example of case 4 and 5.
            And so on.
    """

	# If you plan to spend more than a stay lasts. We return the price of
    # stadia. As according to the time range, it may be worth different
    # stay, we look for the hourly rate that is charged closer, and we get the
    # price from there.
    zone = Zone.objects.get(code=zone_code)
    stay_minutes = zone.stay_minutes
    if minutes >= stay_minutes:
        zd = zonedetails_nearest_range(zone_code)
        stay_price = float("{0:.2f}".format(zd.stay_price))
        return stay_price


    # ZoneDetails, ZoneDetails, [ZoneDetails], ZoneDetails
    case2,case4,case3,case5 = details_intersected_by_period(zone_code,minutes, start_datetime)

    ret_case2 = 0
    if case2:
        zprice = case2.price
        zminutes = case2.minutes
        ret_case2 = (minutes * zprice ) / zminutes
        ret_case2 = float("{0:.2f}".format(ret_case2))
        return ret_case2

    ret_case4 = 0
    if case4:
        # See minutes between period start and end of range, calculate proportional
        ret_case4 = calc_price_of_range(start_datetime.time(), case4.hour_end, case4.price, case4.minutes)

    ret_case5 = 0
    if case5:
        pend = start_datetime + timedelta(minutes=minutes)
        # See minutes between range start and period's end, calculate proportional
        ret_case5 = calc_price_of_range(case5.hour_init, pend.time() ,  case5.price, case5.minutes)

    ret_case3 = 0
    if case3:
        # Periods summed up completely
        for z in case3:
            ret_case3 += calc_price_of_range(z.hour_init, z.hour_end, z.price, z.minutes)

    ret = ret_case3 + ret_case4 + ret_case5
    ret = float("{0:.2f}".format(ret))
    return ret

def calc_price_of_range(rinit, rend, price, minutes):
    """
		IN:
             zinit: time object, start time
             zend: take object, end time
             price: price coming out, the last minutes
             minutes: amount of minutes q the price indicated.
         OUT: Float, from which time comes between zinit and zend, according to price and minutes.

         We calculate the quantity of minutis between init and end, given
         that X minutes, they come out And price.
    """
    now = datetime.now()
    init = now.replace(hour=rinit.hour, minute=rinit.minute)
    end = now.replace(hour=rend.hour, minute=rend.minute)
    diff_seconds = (end - init).total_seconds()
    diff_min =  int( int(round(diff_seconds)) / 60 )

    return (diff_min * price) / minutes
