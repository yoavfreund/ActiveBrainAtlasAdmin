from django.shortcuts import render
from brain.models import Animal, Slide, SlideCziToTif
from brain.forms import AnimalForm

# from url initial page
def image_list(request):
    prep_id = request.GET.get('prep_id')
    if not prep_id:
        prep_id = 'DK43'
    
    form = AnimalForm()  # A form bound to the GET data
    datarows = Animal.objects.filter(prep_id=prep_id).order_by('prep_id')
    prep_id = Animal.objects.get(prep_id=prep_id)

    return render(request, 'list.html',{'datarows': datarows, 'form':form, 'animal_title':prep_id})

