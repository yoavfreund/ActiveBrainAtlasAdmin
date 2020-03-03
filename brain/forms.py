from django import forms
from django.forms import ModelChoiceField
from brain.models import Animal


class AnimalForm(forms.Form):
    prep_id = ModelChoiceField(label='Animal',queryset=Animal.objects.all().order_by('prep_id'), required=False,widget=forms.Select(attrs={'onchange': 'id_list.submit();','class':'form-control'}))
