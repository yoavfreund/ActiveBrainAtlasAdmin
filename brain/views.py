from django.shortcuts import render
from brain.models import Animal, ScanRun, Slide, SlideCziToTif
from brain.forms import AnimalForm

# from url initial page
def image_list(request):
    prep_id = request.GET.get('prep_id')
    if not prep_id:
        prep_id = 'DK43'
    
    form = AnimalForm()  # A form bound to the GET data
    animals = Animal.objects.filter(prep_id=prep_id).order_by('prep_id')
    animal = Animal.objects.get(prep_id=prep_id)
    scans = ScanRun.objects.filter(prep_id=prep_id).order_by('created')
    slides = Slide.objects.filter(scan_run_id__in=[1,2]).order_by('file_name')
    tiffs = SlideCziToTif.objects.filter(slide_id__in=[1,2]).order_by('file_name')

    return render(request, 'list.html',{'animals': animals,
                                        'animal': animal, 
                                        'scans': scans, 
                                        'slides': slides, 
                                        'tiffs': tiffs,
                                        'form': form, 
                                        'animal_title':prep_id})

