from django.contrib import admin
from django.forms import TextInput, Textarea, Select, DateInput, DateTimeInput, NumberInput
from django.db import models
import csv
from django.http import HttpResponse
from brain.models import Animal, Histology, Injection, Virus, InjectionVirus, OrganicLabel, ScanRun, Slide, SlideCziToTif

class ExportCsvMixin:
    def export_as_csv(self, request, queryset):

        meta = self.model._meta
        field_names = [field.name for field in meta.fields]

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}.csv'.format(meta)
        writer = csv.writer(response)

        writer.writerow(field_names)
        for obj in queryset:
            row = writer.writerow([getattr(obj, field) for field in field_names])

        return response

    export_as_csv.short_description = "Export Selected"

class AtlasAdminModel(admin.ModelAdmin):
    formfield_overrides = {
        models.CharField: {'widget': TextInput(attrs={'size':'20'})},
        models.DateTimeField: {'widget': DateInput(attrs={'size':'20'})},
        models.DateField: {'widget': DateTimeInput(attrs={'size':'20','type':'date'})},
        models.IntegerField: {'widget': NumberInput(attrs={'size':'20'})},
        models.TextField: {'widget': Textarea(attrs={'rows':4, 'cols':40})},
    }
    class Media:
        css = {
            'all': ('css/admin.css',)
        }
    

class AnimalAdmin(AtlasAdminModel, ExportCsvMixin):
    list_display = ('prep_id', 'performance_center', 'comments', 'created')
    fields = []
    search_fields = ('prep_id',)
    ordering = ['prep_id']
    actions = ["export_as_csv"]
    exclude = ('created',)
    
class HistologyAdmin(AtlasAdminModel, ExportCsvMixin):
    list_display = ('prep_id', 'label', 'performance_center')
    fields = []
    search_fields = ('prep_id',)
    ordering = ['prep_id', 'label']
    actions = ["export_as_csv"]
    exclude = ('created',)


    def prep_id(self, instance):
        return instance.prep.prep_id

class InjectionAdmin(AtlasAdminModel, ExportCsvMixin):
    list_display = ('prep_id', 'performance_center', 'anesthesia', 'comments', 'created')
    fields = []
    search_fields = ('prep_id',)
    ordering = ['created']
    actions = ["export_as_csv"]
    
    def prep_id(self, instance):
        return instance.prep.prep_id

class VirusAdmin(AtlasAdminModel, ExportCsvMixin):
    list_display = ('virus_name', 'virus_type', 'type_details', 'created')
    fields = []
    search_fields = ('virus_name',)
    ordering = ['virus_name']
    actions = ["export_as_csv"]


class InjectionVirusAdmin(AtlasAdminModel):
    list_display = ('prep_id', 'injection_comments', 'virus_name', 'created')
    fields = ['injection', 'virus']
    search_fields = ('prep_id',)
    ordering = ['created']
    
    def prep_id(self, instance):
        return instance.injection.prep.prep_id
    
    def injection_comments(self, instance):
        return instance.injection.comments
    
    def virus_name(self, instance):
        return instance.virus.virus_name


class OrganicLabelAdmin(AtlasAdminModel, ExportCsvMixin):
    list_display = ('label_id', 'label_type', 'type_details', 'created')
    fields = []
    search_fields = ('label_id',)
    ordering = ['label_id', 'label_type', 'type_details', 'created']
    actions = ["export_as_csv"]

class ScanRunAdmin(AtlasAdminModel, ExportCsvMixin):
    list_display = ('prep_id', 'performance_center', 'machine','comments', 'created')
    fields = []
    search_fields = ('prep_id',)
    ordering = ['prep_id', 'performance_center', 'machine','comments', 'created']
    actions = ["export_as_csv"]
    
    def prep_id(self, instance):
        return instance.prep.prep_id

class SlideAdmin(AtlasAdminModel, ExportCsvMixin):
    list_display = ('prep_id', 'file_name', 'slide_status', 'scene_qc_1', 'scene_qc_2', 'scene_qc_3', 'scene_qc_4')
    fields = []
    search_fields = ['scan_run__prep__prep_id']
    ordering = ['file_name', 'created']
    actions = ["export_as_csv"]
    
    def prep_id(self, instance):
        return instance.scan_run.prep.prep_id

class SlideCziToTifAdmin(AtlasAdminModel, ExportCsvMixin):
    list_display = ('file_name', 'include_tif','section_number', 'scene_number', 'channel','width','height','file_size')
    fields = []
    search_fields = ('file_name',)
    ordering = ['section_number']
    actions = ["export_as_csv"]
    
    

admin.site.register(Animal, AnimalAdmin)
admin.site.register(Histology, HistologyAdmin)
admin.site.register(Injection, InjectionAdmin)
admin.site.register(Virus, VirusAdmin )
admin.site.register(InjectionVirus, InjectionVirusAdmin )
admin.site.register(OrganicLabel, OrganicLabelAdmin) 
admin.site.register(ScanRun, ScanRunAdmin)
admin.site.register(Slide, SlideAdmin)
admin.site.register(SlideCziToTif, SlideCziToTifAdmin)

admin.site.site_header = 'Active Brain Atlas Admin'
admin.site.site_title = "Active Brain Atlas"
admin.site.index_title = "Welcome to Active Brain Atlas Portal"

