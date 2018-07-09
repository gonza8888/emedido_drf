# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.db import models
from .rules import ACTIONS, STAGES, METHODS

class RuleMethod(models.Model):
    """Each entrance correspondes internally with a function, that can be active or not, depending if it is associated to some model.
        To be executed , it has to be related to that zone. Been related means is active, so it will be exeuted.
        Active means that exists the relation between the rule entrance in the table and the zone.

        Mutex check, can be made in admin for simplicity. Mutex is beacuse there are rules that can not be activated at the same time
        in some zone, for example "no limit time for parking" and "limit time when parking"

        .. _RuleMethod:

        +------------------+------------------+----------------+------------------------------------------------------------+
        | Nombre campo     |       Tipo       | Null permitido |                 Comentario                                 |
        +==================+==================+================+============================================================+
        | method           | IntegerField     |       No       |   Choose which function we will make, key and unique       |
        |                  |                  |                |   as we eill list only one function, then the relations    |
        |                  |                  |                |   we made it between models.                               |
        |                  |                  |                |   I.e., for example in zone model, we will make an M2M     |
        |                  |                  |                | to this model.                                             |
        |                  |                  |                | Also, into each class, we will have a dictionary           |
        |                  |                  |                | where we will map this number with a function, so          |
        |                  |                  |                | with this we deelope an extra security layer, in which only|
        |                  |                  |                | can be exeuted methos that we will have                    |
        +------------------+------------------+----------------+------------------------------------------------------------+
        | action           |    CharField     |       No       |   Action that this functions is related with,              |
        |                  |                  |                |for example : park                                          |
        |                  |                  |                | We an use same function to more than one thing? . This     |
        |                  |                  |                | restriction also we can do it with a dictionary inside     |
        |                  |                  |                | the class, for example inside parking we can have          |
        |                  |                  |                | {'method1':'nombre_foo1','method2':'nombre_foo2'}          |
        |                  |                  |                | And if we have more methods, with that we add security and |
        |                  |                  |                | let only method1 y method2 execute inside that Action      |
        +------------------+------------------+----------------+------------------------------------------------------------+
        | description      |    CharField     |       yes      |  Description of what the function does                     |
        +------------------+------------------+----------------+------------------------------------------------------------+
        | stage            | Small Int        |       No       |  Stage in which it is exec. Can be more than one           |
        |                  |                  |                | instance in a proc. Example: see if you can park, send sms.|
        +------------------+------------------+----------------+------------------------------------------------------------+
        | order            | Small Int        |       No       | Order that is executed into stage.                         |
        |                  |                  |                | For example inside stage credit calculation, we can first  |
        |                  |                  |                | know if it has free credit, and if not calc credit after   |
        +------------------+------------------+----------------+------------------------------------------------------------+
        | mutex            | M2M(RuleMethod)  |   yes          | M2M to ourselves, to relate rules that are mutually        |
        |                  |                  |                | excluyent, i.e, if the relation exists some active rule    |
        |                  |                  |                | the other can not be                                       |
        +------------------+------------------+----------------+------------------------------------------------------------+
        | cut_exec         | Boolean          | No(def False)  | Param to tell that if this rule is executed, we will cut   |
        |                  |                  |                | the chain of exec and return                               |
        +------------------+------------------+----------------+------------------------------------------------------------+
        | pre_exec         | Boolean          | No(def True)   | Param to tell thath: if the rule is exec before main       |
        |                  |                  |                | function , for example in case of parking                  |
        |                  |                  |                | the main func will be save park model                      |
        |                  |                  |                | and a pre_exec rule can be check if there is credit        |
        |                  |                  |                | and post exec (pre_exec=False) will be send sms            |
        +------------------+------------------+----------------+------------------------------------------------------------+

        Can be better, different models and relations between tables. But with this we are happy
    """
    METHODS=METHODS
    ACTIONS=ACTIONS
    STAGES=STAGES

    action = models.CharField('Accion en la cual debe ser ejecutada',max_length=20,choices=ACTIONS)
    method = models.PositiveSmallIntegerField('Metodo',db_index=True,unique=True,choices=METHODS)
    stage = models.PositiveSmallIntegerField('Etapa/Grupo de ejecucion',choices=STAGES)
    order = models.PositiveSmallIntegerField('Orden dentro de la etapa de ejecucion')
    description = models.CharField('Descripcion de la funcionalidad (max 256 carac)',max_length=256)
    mutexes = models.ManyToManyField('self', blank=True) # many2many con esta misma clase, Reglas con las que se es mutuamente excluyente
    cut_exec = models.BooleanField('Si pasa esta regla, termina flujo de ejecucion', default=False)
    pre_exec = models.BooleanField('Ejecutar antes de la funcion ppal.', default=True)

    def __str__(self):
        return '[{ac}] {des}'.format(ac=self.action,des=self.description)

    # Called from admin, if we have function here instead of in admin, the self is the instance
    def id_mutexes(self):
        return ". ".join([str(p.id) for p in self.mutexes.all()])
    def zones_code(self):
        #return "<br/>".join([str(p.code) for p in self.zones.all()])
        return ". ".join([str(p.code) for p in self.zones.all()])

    class Meta:
        app_label = 'rule_callable'
