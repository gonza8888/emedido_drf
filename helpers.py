# -*- coding: utf-8 -*-
import string
import random
from datetime import datetime, timedelta, date
from back_emedido.db_connections.mysql_connection import sms_db_access
from django.conf import settings

from back_emedido.apps.parameter.models import Parameter

from random import choice, randint
import logging
import hashlib
from back_emedido.settings.common import SALT
from back_emedido.settings.common import RECHARGE_FIRST_LIMIT, RECHARGE_SECOND_LIMIT, RECHARGE_FIRST_STEP, RECHARGE_SECOND_STEP

logging.basicConfig(level=logging.DEBUG,
                     format='%(asctime)s %(levelname)-8s %(message)s',
                     datefmt='%a, %d %b %Y %H:%M:%S',
                     filename='log_back_emedido.log',
                     filemode='a')
log = logging.getLogger('back_emedido')

def to_epoch(date, miliseconds=True):
    """
        The Unix epoch (or Unix time or POSIX time or Unix timestamp) is the number of seconds that have elapsed since January 1, 1970
    """
    seconds = int((date - datetime(1970,1,1)).total_seconds())
    if miliseconds:
        ret = seconds * 1000
    else:
        ret = seconds
    return ret

def this_year():
      return int(datetime.now().year)

def weekday_to_str(num):
    data = {
        '0' : 'mon',
        '1' : 'tue',
        '2' : 'wed',
        '3' : 'thu',
        '4' : 'fri',
        '5' : 'sat',
        '6' : 'sun'
    }

    return data.get(str(num))

def gen_secret_key(numero):
    return ''.join(random.choice(string.ascii_lowercase + string.ascii_uppercase + string.digits) for _ in range(numero))

def gen_random_num_of_length(n):
    """
        Aleatory num of n ciphres
    """
    range_start = 10**(n-1)
    range_end = (10**n)-1
    return randint(range_start, range_end)

def is_password_ok(password):
    """
    We verify that the password has the correct format
    Currently if it is ASCII, of 6 or more characters, it is fine. No more restrictions
    Restrictions of longitúd could go here.
    """
    try:
      #  password.decode('ascii')
        ret = len(password) >= 6
    except UnicodeEncodeError:
        ret = False
    return ret


def duration_format_ok(duration_str):
    """
        in: string representando una duracion
        out: objeto timedelta convertido desde el string.
        Nos fijamos que el formato de la duracion a estacionar sea el correcto.
        Es decir, formato y que la duracion sea multiplo de 15 minutos.
        Ademas, otro chequeo adicional se hace a la hora de hacer un parking, que chequeamos que sea menor que parametro establecido.
    """
    try:
        # TODO: Check if we change to be a pytimeparse and do not enforce this format
        t = datetime.strptime(duration_str,"%H:%M:%S")
        duration_obj = timedelta(hours=t.hour, minutes=t.minute, seconds=t.second)
    except Exception as e:
        raise Exception("Incorrect format of duration, it must be HH:MM:SS and multiplo of 15")
    try:
        # Max duration of parking
        max_duration = Parameter.objects.get(key='max_duration_park').value
        max_duration = "12"
        tmax = datetime.strptime(max_duration,"%H:%M:%S")
        max_duration_obj = timedelta(hours=tmax.hour, minutes=tmax.minute, seconds=tmax.second)
    except:
        raise Exception("Internal error in max parking time parameter.")

    if not (duration_obj.total_seconds() / 60) % 15 == 0:
        raise Exception("Can only park in fractions of 15 minutes.")

    if duration_obj > max_duration_obj:
        raise Exception("Can park a maximum of " + max_duration + " minutes")

    return duration_obj

# ####################
# FORMAT DICTIONARIES

# From this,
# "data": [
# {
   # "cost_price": 10,
   # "id": 1,
   # "valid": true
   # .....
# }
# ],

# to this.
# "data": {
# "1" : {
   # "cost_price": 10,
   # "id": 1,
   # "valid": true
   # .....
# }
# },

def list_to_dict(lista):
    """
        We pass a list of objects, and convert to dictionary where the key
         is the id, and the value the whole object.
    """
    ret = {}
    try:
        for obj in lista:
            ret[obj.get('id')] = obj
        return ret
    except Exception as e:
#        return ret
        raise Exception("Error procesando los datos hacia un diccionario")

def list_to_dict_user__username(lista):
    """
        We pass a list of objects, and convert to dictionary where the key
         is the username (of FK), and the value is the whole object.
    """
    ret = {}
    try:
        for obj in lista:
            clave = obj.get('user').get('username')
            if clave:
                ret[clave] = obj
        return ret
    except Exception as e:
#        return ret
        raise Exception("Error procesando los datos hacia un diccionario")

# ------------------------------------------------------------------------------
#def format_phone(phone):
#    if not (phone[0] == "+" and len(phone) == 13):
def format_phone(phone):
    """
       function to format a phone number. Change per plugin.
        It puts the + forward.
    """
    phone=str(phone)
    if len(phone) == 12:
        return "+" + phone
    elif len(phone) == 13:
        return "+" + phone[1:]
    else:
        return phone

def format_phone_2(phone):
    """
       function to format a phone number. Change per plugin.
       It takes out the + forward.
    """
    phone=str(phone)
    if len(phone) == 12 or len(phone) == 10:
        return phone
    elif len(phone) == 13 and phone[0] == '+':
        return phone[1:]
    else:
        raise Exception("Formato de teléfono incorrecto")

def format_phone_3(phone):
    phone=str(phone)
    if len(phone) == 12:
        return "+"+phone
    elif len(phone) == 13 and phone[0] == '+':
        return phone
    else:
        raise Exception("Formato de teléfono incorrecto")

def check_phone(phone):
    """
       Check that phone format is correct
    """
    if len(phone) == 12:
        return True
    elif len(phone) == 13:
        return "+" == phone[0]
    else:
        raise Exception("Formato de teléfono incorrecto")


# ------------------------------------------------------------------------------
# Functions to hashear (according to what we established) a code of a card.
# And for your verification

def hash_card_code(num, year):
    """
    We take a number and a year. The number, in this case, will be the 7 digits that we generate for the cards.
    To the concatenation of these two, plus a salt, we have it.
    From that hash we get the first 3 numbers and insert them in positions that we preset, within
    the original 7-digit number. Resulting in a number of 10.
    That is the number that will be printed hidden on the card, and the number that the user will use to charge credit.
    out:
        Number of 10 digits
    """
    num = str(num)
    year = str(year)
    if len(num) is not 7:
        raise Exception("numero incorrecto")
    sec_list = []
    count = 0
    string_to_hash = num+year+SALT
    hash_string = hashlib.md5(string_to_hash.encode('utf-8')).hexdigest()
    # Tomamos los 3 primeros numeros del hash. (porque queremos q sean nums)
    for x in hash_string:
        if(x.isdigit() and count < 3):
            sec_list.append(x)
            count = count+1
    # Los insertamos en las posiciones pre-establecidas (2,7 y 8)
    code = num[:2]+sec_list[0]+num[2:6]+sec_list[1]+sec_list[2]+num[6:]
    return int(code)

def de_hash_card_code(code, year):
    """
    To check if a code is valid, we get the 3 numbers of the positions that we preset.
    From that code, we see if we get to it, building with the original procedure, the same number.
    If so, it is because it is a valid code.
    out:
             Number of 10 digits.
    """
    code = str(code)
    if len(code) is not 10:
        raise Exception("Código incorrecto.")
    code_no_sec = get_original_code(code)
    new_code = hash_card_code(code_no_sec, year)
    return int(new_code)

def code_is_valid(code,year):
    """
        Take a 10-digit code (already hashed) that comes from the printed card. Sent by the user.
        We make the inverse hash process and see if it is correct.
    """
    c1 = de_hash_card_code(code,year)
    return int(c1) == int(code)

def get_original_code(code):
    """
        From a 10 digit code, we obtain the original 7 digits.
    """
    if len(code) is not 10:
        raise Exception("Código incorrecto. Debe ser de longitud 10.")
    return code[:2]+code[3:7]+code[9]


# Funcion que usamos para testear funciones de hash.. uso interno solamente.
def test_hashes():
    boolean = True
    list1 = [str(randint(1000000,9999999)) for x in range(1000)]
    for i in list1:
        c1 = hash_func(i,"2017")
        c2 = de_hash_func(c1, "2017")
        boolean = boolean and (c1 == c2)
    return boolean


# ----------------------------------------------------------------------------
#                               ENVIO DE SMS
# ----------------------------------------------------------------------------

# ESTO LO PASAMOS A LA APP "sms"

#def DEPRECATED_enviar_sms(phone,text):
def enviar_sms(phone,text):
    phone = format_phone_2(phone)
    db = sms_db_access(settings.SMS_DB_HOST, settings.SMS_DB_DATABASE, settings.SMS_DB_USERNAME, settings.SMS_DB_PASSWORD)
    db.do_query("insert into outbox (number,text,phone) values (%s,%s,%s)",(phone,text,settings.SMS_DB_NUMBER))
    db.close()


# ----------------------------------------------------------------------------
#                    CALC OF CREDITS RECHARGED
# ----------------------------------------------------------------------------
def calc_amount_recharged(creds):
    if creds <= RECHARGE_FIRST_LIMIT:
        amount_recharged = creds
    elif creds > RECHARGE_FIRST_LIMIT and creds <= RECHARGE_SECOND_LIMIT:
        amount_recharged = creds * RECHARGE_FIRST_STEP
    else:
        amount_recharged = creds * RECHARGE_SECOND_STEP

    return amount_recharged

# ----------------------------------------------------------------------------
#                    OBTAINING PARAMETERS
# ----------------------------------------------------------------------------

def get_setting_param_old(key, defval):
    try:
        return Parameter.objects.get(key=key).value
    except Parameter.DoesNotExist:
        if hasattr(settings,key.upper()):
            return getattr(settings,key.upper())
        else:
            return defval

def get_setting_param(key):
    try:
        par = Parameter.objects.get(key=key)
        if par.typeof == "Char":
            return Parameter.objects.get(key=key).value
        elif par.typeof == "Int":
            return int(Parameter.objects.get(key=key).value)
        elif par.typeof == "Float":
            return float(Parameter.objects.get(key=key).value)
        else:
            raise Exception("Parametro no existente")
    except Parameter.DoesNotExist:
        raise Exception("Parametro no existente")
