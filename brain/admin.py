from django.contrib import admin
from django.forms import TextInput, Textarea, Select, DateInput, DateTimeInput, NumberInput
from django.db import models
import csv
from django.http import HttpResponse
from django.utils.html import format_html
from django.urls import reverse
from django.urls import path
from django.template.response import TemplateResponse
from django.db import connection

from brain.models import Animal, Histology, Injection, Virus, InjectionVirus, OrganicLabel, ScanRun, Slide, SlideCziToTif, Section

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
    list_filter = ('created', )
    fields = []
    actions = ["export_as_csv"]
    class Media:
        css = {
            'all': ('css/admin.css',)
        }
    

class AnimalAdmin(AtlasAdminModel, ExportCsvMixin):
    list_display = ('prep_id', 'performance_center', 'comments', 'created', 'create_section')
    search_fields = ('prep_id',)
    ordering = ['prep_id']
    exclude = ('created',)

    def create_section(self, obj):
            return format_html(
                '<a class="button" href="{}">Create Sections</a>&nbsp;',
                reverse('admin:account-deposit', args=[obj.pk]),
            )
            
    create_section.short_description = 'Sections'
    create_section.allow_tags = True    
    
class HistologyAdmin(AtlasAdminModel, ExportCsvMixin):
    list_display = ('prep_id', 'label', 'performance_center')
    search_fields = ('prep_id',)
    ordering = ['prep_id', 'label']
    exclude = ('created',)

    def prep_id(self, instance):
        return instance.prep.prep_id

class InjectionAdmin(AtlasAdminModel, ExportCsvMixin):
    list_display = ('prep_id', 'performance_center', 'anesthesia', 'comments', 'created')
    search_fields = ('prep_id',)
    ordering = ['created']

    def prep_id(self, instance):
        return instance.prep.prep_id

class VirusAdmin(AtlasAdminModel, ExportCsvMixin):
    list_display = ('virus_name', 'virus_type', 'type_details', 'created')
    search_fields = ('virus_name',)
    ordering = ['virus_name']


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
    search_fields = ('label_id',)
    ordering = ['label_id', 'label_type', 'type_details', 'created']

class ScanRunAdmin(AtlasAdminModel, ExportCsvMixin):
    list_display = ('prep_id', 'performance_center', 'machine','comments', 'created')
    search_fields = ('prep_id',)
    ordering = ['prep_id', 'performance_center', 'machine','comments', 'created']

    def prep_id(self, instance):
        return instance.prep.prep_id

class SlideAdmin(AtlasAdminModel, ExportCsvMixin):
    list_display = ('prep_id', 'file_name', 'slide_status', 'scene_qc_1', 'scene_qc_2', 'scene_qc_3', 'scene_qc_4')
    search_fields = ['scan_run__prep__prep_id']
    ordering = ['file_name', 'created']

    def prep_id(self, instance):
        return instance.scan_run.prep.prep_id


class IsIncludedFilter(admin.SimpleListFilter):
    title = 'Include?'
    parameter_name = 'include_tif'

    def lookups(self, request, model_admin):
        return (
            ('Good', 'Good'),
            ('Bad', 'Bad'),
        )
        
        
    def queryset(self, request, queryset):
        value = self.value()
        if value == 'Good':
            return queryset.filter(include_tif = 1)
        elif value == 'Bad':
            return queryset.exclude(include_tif = 2)
        return queryset

class SlideCziToTifAdmin(AtlasAdminModel, ExportCsvMixin):
    list_display = ('file_name', 'include_tif','section_number', 'scene_number', 'channel','width','height','file_size')
    search_fields = ('file_name',)
    ordering = ['section_number']
    list_filter = (IsIncludedFilter, )


class SectionAdmin(AtlasAdminModel, ExportCsvMixin):
    list_display = ('prep_id', 'section_qc', 'ch_1_path', 'ch_2_path', 'ch_3_path', 'ch_4_path')
    list_filter = ('prep_id', )
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            # path('<prep_id>', self.admin_site.admin_view(self.process_section),  name='account-deposit',
            path('<prep_id>', self.process_section,  name='account-deposit',
            )
        ]
        return custom_urls + urls

    def process_section(self, request, prep_id, *args, **kwargs):
        cursor = connection.cursor()
        query = "create_sections()"
        param = {"prep_id": prep_id, "orderby": orderby}
        sp = cursor.execute(query, param)
        data = cursor.fetchall()
        cursor.close()

        sections =  self.model._meta.model.objects.filter(prep_id__exact=prep_id)

       context = self.admin_site.each_context(request)
       context['opts'] = self.model._meta
       context['results'] = sections
       context['title'] = 'Sections for {}'.format(prep_id)
       return TemplateResponse(
            request,
            'admin/section/list.html',
            context,
        )

    

admin.site.register(Animal, AnimalAdmin)
admin.site.register(Histology, HistologyAdmin)
admin.site.register(Injection, InjectionAdmin)
admin.site.register(Virus, VirusAdmin )
admin.site.register(InjectionVirus, InjectionVirusAdmin )
admin.site.register(OrganicLabel, OrganicLabelAdmin) 
admin.site.register(ScanRun, ScanRunAdmin)
admin.site.register(Slide, SlideAdmin)
admin.site.register(SlideCziToTif, SlideCziToTifAdmin)
admin.site.register(Section, SectionAdmin)

admin.site.site_header = 'Active Brain Atlas Admin'
admin.site.site_title = "Active Brain Atlas"
admin.site.index_title = "Welcome to Active Brain Atlas Portal"

