from django import forms
from django.forms import ModelChoiceField, BaseInlineFormSet
from brain.models import Animal, SlideCziToTif


class AnimalForm(forms.Form):


    prep_id = ModelChoiceField(label='Animal',
                               queryset=Animal.objects.all().order_by('prep_id'),
                               required=False,
                               widget=forms.Select(attrs={'onchange': 'id_list.submit();','class':'form-control'}))

    class Meta:
        fields = ('prep_id',)

class TifFormSet(BaseInlineFormSet):
    def get_form_kwargs(self, index):
        kwargs = super().get_form_kwargs(index)
        kwargs['parent_object'] = self.instance
        return kwargs

class TifForm(forms.ModelForm):
    MY_CHOICES = [('Bad tissue', 'Bad tissue'), ('Out-of-Focus', 'Out-of-Focus')]
    def __init__(self, *args, parent_object, **kwargs):
       super(TifForm, self).__init__(*args, **kwargs)
       print(parent_object.id)
       queryset = SlideCziToTif.objects.filter(slide_id=parent_object.id)
       if self.instance.id:
           CHOICES_INCLUDING_DB_VALUE = [(self.instance.id, self.instance.file_name)] + queryset
           self.fields['file_name'] = forms.ChoiceField(
                choices=CHOICES_INCLUDING_DB_VALUE)
       else:
           self.fields['file_name'] = forms.ModelChoiceField(queryset=queryset)

