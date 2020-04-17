from django import forms
from django.db.models import Max
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

def save_slide_model(self, request, obj, form, change):
    slide_status = form.cleaned_data.get('slide_status')
    qc_1 = form.cleaned_data.get('scene_qc_1')
    qc_2 = form.cleaned_data.get('scene_qc_2')
    qc_3 = form.cleaned_data.get('scene_qc_3')
    qc_4 = form.cleaned_data.get('scene_qc_4')
    qc_5 = form.cleaned_data.get('scene_qc_5')
    qc_6 = form.cleaned_data.get('scene_qc_6')

    form_names = ['insert_before_one', 'insert_between_one_two', 'insert_between_two_three', \
                  'insert_between_three_four', 'insert_between_four_five', 'insert_between_five_six']
    inserts = [form.cleaned_data.get(name) for name in form_names]

    # note, scenes usually range from 1 -> 4
    # insert X amount of scenes/sections at point X
    # insert before one, copy  current one in two to position 1
    # mv 2 to 3, 3 to 4
    scenes_tifs = [SlideCziToTif.objects.filter(slide_id=obj.id).filter(scene_number=scene) for scene in
                   [1, 2, 3, 4]]
    scenes_tifs = [scene_tif for scene_tif in scenes_tifs if len(scene_tif) > 0]
    for scene_index, insert in enumerate(inserts):
        if (insert > 0):
            print('len scenes and i and insert', len(scenes_tifs), scene_index, insert)
            if scene_index < len(scenes_tifs):
                print('len is ok, but not sure if there are tifs at this scene')
                for j in range(insert):
                    for tif in scenes_tifs[scene_index]: # repeat tifs in scene i
                        print('len is ok and found tifs at this scene')
                        newtif = tif
                        newtif.pk = None
                        newtif.save()
            else:
                print('scenes_tifs at i NOT OK')
                for j in range(insert):
                    for tif in scenes_tifs[-1]: # repeat tifs in scene i
                        print('len is ok and found tifs at prior scene')
                        newtif = tif
                        newtif.pk = None
                        newtif.save()


    scenes_tifs = SlideCziToTif.objects.filter(slide_id=obj.id).order_by('scene_number')
    channels = scenes_tifs.aggregate(Max('channel'))
    channels = channels['channel__max']
    len_tifs = len(scenes_tifs) + 1
    flattened = [item for sublist in [[i] * channels for i in range(1, len_tifs)] for item in sublist]

    for new_scene, tif in zip(flattened, scenes_tifs): # iterate over the scenes
        tif.scene_number = new_scene
        tif.save()


    # check if end is checked
    tifs = SlideCziToTif.objects.filter(slide_id=obj.id).order_by('scene_number')
    for tif in tifs:
        if qc_1 == 'End' and tif.scene_number == 1:
            tif.active = 0
        if qc_2 == 'End' and tif.scene_number == 2:
            tif.active = 0
        if qc_3 == 'End' and tif.scene_number == 3:
            tif.active = 0
        if qc_4 == 'End' and tif.scene_number == 4:
            tif.active = 0
        if qc_5 == 'End' and tif.scene_number == 5:
            tif.active = 0
        if qc_6 == 'End' and tif.scene_number == 6:
            tif.active = 0
        tif.save()

    obj.scenes = SlideCziToTif.objects.filter(slide_id=obj.id).filter(channel_index=0).filter(active=1).count()
    obj.save()



def save_slide_modelXXX(self, request, obj, form, change):
    slide_status = form.cleaned_data.get('slide_status')
    qc_1 = form.cleaned_data.get('scene_qc_1')
    qc_2 = form.cleaned_data.get('scene_qc_2')
    qc_3 = form.cleaned_data.get('scene_qc_3')
    qc_4 = form.cleaned_data.get('scene_qc_4')
    qc_5 = form.cleaned_data.get('scene_qc_5')
    qc_6 = form.cleaned_data.get('scene_qc_6')

    form_names = ['insert_before_one', 'insert_between_one_two', 'insert_between_two_three', \
                  'insert_between_three_four', 'insert_between_four_five', 'insert_between_five_six']
    inserts = [form.cleaned_data.get(name) for name in form_names]

    # note, scenes usually range from 1 -> 4
    # insert X amount of scenes/sections at point X
    # insert before one, copy  current one in two to position 1
    # mv 2 to 3, 3 to 4
    scenes_tifs = [SlideCziToTif.objects.filter(slide_id=obj.id).filter(scene_number=scene) for scene in
                   [1, 2, 3, 4]]
    scenes_tifs = [scene_tif for scene_tif in scenes_tifs if len(scene_tif) > 0]
    for i, insert in enumerate(inserts):
        if (insert > 0):
            for j in range(insert):
                print('len scenes and i and insert', len(scenes_tifs), i, insert)
                if i < len(scenes_tifs):
                    print('len is ok, but not sure if there are tifs at this scene')
                    if scenes_tifs[i] is not None:
                        print('scenes_tifs at i OK')
                        for tif in scenes_tifs[i]: # repeat tifs in scene i
                            print('len is ok and found tifs at this scene')
                            newtif = tif
                            newtif.pk = None
                            newtif.save()
                    else:
                        print('scenes_tifs at i NOT OK')
                        for tif in scenes_tifs[-1]: # repeat tifs in scene i
                            print('len is ok and found tifs at prior scene')
                            newtif = tif
                            newtif.pk = None
                            newtif.save()


    scenes_tifs = SlideCziToTif.objects.filter(slide_id=obj.id).order_by('scene_number')
    channels = scenes_tifs.aggregate(Max('channel'))
    channels = channels['channel__max']
    len_tifs = len(scenes_tifs) + 1
    flattened = [item for sublist in [[i] * channels for i in range(1, len_tifs)] for item in sublist]

    for new_scene, tif in zip(flattened, scenes_tifs): # iterate over the scenes
        tif.scene_number = new_scene
        tif.save()


    # check if end is checked
    tifs = SlideCziToTif.objects.filter(slide_id=obj.id).order_by('scene_number')
    for tif in tifs:
        if qc_1 == 'End' and tif.scene_number == 1:
            tif.active = 0
        if qc_2 == 'End' and tif.scene_number == 2:
            tif.active = 0
        if qc_3 == 'End' and tif.scene_number == 3:
            tif.active = 0
        if qc_4 == 'End' and tif.scene_number == 4:
            tif.active = 0
        if qc_5 == 'End' and tif.scene_number == 5:
            tif.active = 0
        if qc_6 == 'End' and tif.scene_number == 6:
            tif.active = 0
        tif.save()

    obj.scenes = SlideCziToTif.objects.filter(slide_id=obj.id).filter(channel_index=0).filter(active=1).count()
    obj.save()
