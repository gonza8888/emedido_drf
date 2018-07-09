# -*- coding: utf-8 -*-

# Este lo hacemos asi para mostrarlo lindo en el __str__
ACTIONS=(
('Parking','Parking'),
('Actives','Actives')
('Actives','Actives'),
#('Infracciones','Infracciones'),
#('Multa','Multa'),
)

################################################################################
################################################################################
################################################################################

##### CONSTANTES PARA IMPORTAR METODOS EN OTROS ARCHIVOS

# -------------- Estacionamientos
FREEPARK=2
MAXTIME=3
MAXTIME_NO=4
NOTIFYSU=5
#--------------- Faltas
TOW=202
FAULT_ACTIVE=203
#--------------- Actives
GRACETIME=401
#PENALTY_NOTIF=401

# Do not change maping!
METHODS=(
(1,'Credits by institution'),
(FREEPARK,'Free for all'),
(MAXTIME,'Time limit'),
(MAXTIME_NO,'No time limit'),
(NOTIFYSU,'Notif asociated users'),
(6,'Distance in time from last park'),
(7,'Unique park in zone'),
(8,'Unique park in block'),
(9,'Unique park in day'),
(TOW,'Call tow automatically'),
(GRACETIME,'Grace time activated'),
(FAULT_ACTIVE,'Fault system active in zone'),
)

#------------------------------------------------------------------------------#
#------------------------------------------------------------------------------#
#--------------------------- STAGES -------------------------------------------#
#------------------------------------------------------------------------------#
#------------------------------------------------------------------------------#

# For not, we will five an order to groups (ACTIONS) with this.
# Park,  1 to 200
# Faults,   201 to 400
# Actives,  401 to 600

# -------------- Parkings
S_PERM=1
S_CREDIT=2
S_TIME=3
S_NOTIF=4
# ------------- Faults
S_VALIDATION=201
S_FAULT=202
# ------------- Actives
S_ACTIVE_VALIDATION=401

STAGES=(
(S_PERM,'[1] Permissions'),
(S_CREDIT,'[2] Credits'),
(S_TIME,'[3] Times'),
(S_NOTIF,'[4] Notifi'),
(S_VALIDATION,'[1] Validations'),
(S_FAULT,'[2] Create Fault'),
(S_ACTIVE_VALIDATION,'[1] User active validations'),
)

