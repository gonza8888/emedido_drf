from django.contrib import admin
from .models import RuleMethod
from django import forms

class RuleForm(forms.ModelForm):
    class Meta:
        model = RuleMethod
        fields = '__all__'

    def clean_stage(self):
        # ----- Check that stage belong to selected action ----- #
        # TODO : Do something better and reactive, filter dropdown not 
        # to give users all possibilities. Done like this for speed
        action = self.cleaned_data.get('action')
        stage = self.cleaned_data.get('stage')
        if action == "Park":
            if not (0 <= stage <= 200):
                raise forms.ValidationError("Staged selected does not blone to Parking")
        elif action == "Faults":
            if not (201 <= stage <= 400):
                raise forms.ValidationError("Staged selected does not blone to Faults")
        elif action == "Actives":
            if not (401 <= stage <= 600):
                raise forms.ValidationError("Staged selected does not blone to Actives")
        else:
            # Este error se da cuando no tenemos todos los choices de ACTIONS
            # del models.py de las reglas, en este if aca arriba.
            raise forms.ValidationError("Internal error on rule's admin.")

        return self.cleaned_data['stage']

    def clean_method(self):
        action = self.cleaned_data.get('action')
        method = self.cleaned_data.get('method')
        if action == "Park":
            if not (0 <= method <= 200):
                raise forms.ValidationError("Method selected does not belong to action Park")
        elif action == "Faults":
            if not (201 <= method <= 400):
                raise forms.ValidationError("Method selected does not belong to action Faults")
        elif action == "Actives":
            if not (401 <= method <= 600):
                raise forms.ValidationError("Method selected does not belong to action Actives")
        else:
            raise forms.ValidationError("Internal error in rule's admin. Report this to responsables of developing the system.")
        return self.cleaned_data['method']

class RuleMethodAdmin(admin.ModelAdmin):
    form = RuleForm
    filter_horizontal = ('mutexes',) # Better many2many look and feel in admin
    list_display = ('id','action','desc','id_mutexes','zones_code')
    # Que campos linkean al objeto en cuestion, no solo la 1er col
    list_display_links = ('id','action','desc')

    def action(self,obj):
        return "%s" % (obj.action)
    def desc(self,obj):
        return "%s" % (obj.description)
    desc.short_description = 'Descripcion'


# Register your models here.
admin.site.register(RuleMethod,RuleMethodAdmin)
