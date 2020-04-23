from django import forms
from django.db.models import Max
from django.forms import ModelChoiceField
from brain.models import Animal, Slide, SlideCziToTif


class AnimalForm(forms.Form):
    prep_id = ModelChoiceField(label='Animal',
                               queryset=Animal.objects.all().order_by('prep_id'),
                               required=False,
                               widget=forms.Select(attrs={'onchange': 'id_list.submit();', 'class': 'form-control'}))

    class Meta:
        fields = ('prep_id',)


# helper methods for the slide admin form

def repeat_scene(slide_id, inserts, scene_number):
    print(slide_id, inserts, scene_number)
    tifs = SlideCziToTif.objects.filter(slide_id=slide_id).filter(active=True) \
        .filter(scene_number=scene_number)

    if not tifs:
        tifs = find_closest_neighbor(slide_id, scene_number)

    for insert in range(inserts):
        create_scene(tifs, scene_number)


def create_scene(tifs, scene_number):
    for tif in tifs:  #
        newtif = tif
        newtif.active = True
        newtif.pk = None
        newtif.scene_number = scene_number
        newtif.save()


def find_closest_neighbor(slide_id, scene_number):
    channels = SlideCziToTif.objects.filter(slide_id=slide_id).filter(active=True).aggregate(Max('channel'))
    channels = channels['channel__max']
    tifs = None
    below = SlideCziToTif.objects.filter(slide_id=slide_id).filter(active=True) \
                .filter(scene_number__lt=scene_number).order_by('-scene_number')[:channels]

    above = SlideCziToTif.objects.filter(slide_id=slide_id).filter(active=True) \
                .filter(scene_number__gt=scene_number).order_by('scene_number')[:channels]
    if below.exists():
        tifs = below
    else:
        tifs = above

    return tifs


def set_scene_inactive(slide_id, scene_number):
    tifs = SlideCziToTif.objects.filter(slide_id=slide_id).filter(active=True).filter(scene_number=scene_number)
    for tif in tifs:
        tif.active = False
        tif.save()


def set_end(slide_id, scene_number):
    tifs = SlideCziToTif.objects.filter(slide_id=slide_id).filter(scene_number__gte=scene_number)
    for tif in tifs:
        tif.active = False
        tif.save()


def scene_reorder(slide_id):
    # now get the order of scenes correct
    scenes_tifs = SlideCziToTif.objects.filter(slide_id=slide_id).filter(active=1).order_by('scene_number')
    channels = scenes_tifs.aggregate(Max('channel'))
    channels = channels['channel__max']
    len_tifs = len(scenes_tifs) + 1
    flattened = [item for sublist in [[i] * channels for i in range(1, len_tifs)] for item in sublist]

    for new_scene, tif in zip(flattened, scenes_tifs):  # iterate over the scenes
        tif.scene_number = new_scene
        tif.save()

def scene_reorder(slide_id):
    # now get the order of scenes correct
    scenes_tifs = SlideCziToTif.objects.filter(slide_id=slide_id).filter(active=1).order_by('scene_number')
    channels = scenes_tifs.aggregate(Max('channel'))
    channels = channels['channel__max']
    len_tifs = len(scenes_tifs) + 1
    flattened = [item for sublist in [[i] * channels for i in range(1, len_tifs)] for item in sublist]

    for new_scene, tif in zip(flattened, scenes_tifs):  # iterate over the scenes
        tif.scene_number = new_scene
        tif.save()

def save_slide_model(self, request, obj, form, change):
    scene_numbers = [1, 2, 3, 4, 5, 6]
    qc_1 = form.cleaned_data.get('scene_qc_1')
    qc_2 = form.cleaned_data.get('scene_qc_2')
    qc_3 = form.cleaned_data.get('scene_qc_3')
    qc_4 = form.cleaned_data.get('scene_qc_4')
    qc_5 = form.cleaned_data.get('scene_qc_5')
    qc_6 = form.cleaned_data.get('scene_qc_6')
    # do the QC fields
    OUTOFFOCUS = 1
    BADTISSUE = 2
    END = 3
    qc_values = [qc_1, qc_2, qc_3, qc_4, qc_5, qc_6]
    current_qcs = Slide.objects.values_list('scene_qc_1', 'scene_qc_2', 'scene_qc_3',
                                            'scene_qc_4', 'scene_qc_5',
                                            'scene_qc_6').get(pk=obj.id)

    for qc_value, current_qc, scene_number in zip(qc_values, current_qcs, scene_numbers):
        if qc_value in [OUTOFFOCUS, BADTISSUE] and qc_value != current_qc:
            set_scene_inactive(obj.id, scene_number)

    for qc_value, current_qc, scene_number in zip(qc_values, current_qcs, scene_numbers):
        if qc_value in [OUTOFFOCUS, BADTISSUE] and qc_value != current_qc:
            tifs = find_closest_neighbor(obj.id, scene_number)
            create_scene(tifs, scene_number)

    for qc_value, current_qc, scene_number in zip(qc_values, current_qcs, scene_numbers):
        if qc_value == END and qc_value != current_qc:
            set_end(obj.id, scene_number)

    form_names = ['insert_before_one', 'insert_between_one_two', 'insert_between_two_three',
                  'insert_between_three_four', 'insert_between_four_five', 'insert_between_five_six']
    insert_values = [form.cleaned_data.get(name) for name in form_names]

    moves = sum([value for value in insert_values])
    # scene_count = obj.scenes
    # scenes = range(1, scene_count + 1)
    ## do the inserts
    if moves > 0:
        current_values = Slide.objects.values_list('insert_before_one', 'insert_between_one_two',
                                                   'insert_between_two_three',
                                                   'insert_between_three_four', 'insert_between_four_five',
                                                   'insert_between_five_six').get(pk=obj.id)

        scene_numbers = [1, 2, 3, 4, 5, 6]
        for new, current, scene_number in zip(insert_values, current_values, scene_numbers):
            if current != new:
                repeat_scene(obj.id, new, scene_number)
        scene_reorder(obj.id)

    obj.scenes = SlideCziToTif.objects.filter(slide_id=obj.id).filter(channel_index=0).filter(active=1).count()
    obj.save()
