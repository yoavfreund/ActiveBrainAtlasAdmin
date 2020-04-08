from django.contrib import admin
from django.forms import TextInput, Textarea, Select, DateInput, DateTimeInput, NumberInput
from django.db import models
import csv
import pandas as pd
from django.http import HttpResponse
from django.utils.html import format_html
from django.urls import reverse
from django.urls import path
from django.template.response import TemplateResponse
from django.db import connection
from django.contrib.admin.widgets import AdminDateWidget

from brain.models import (Animal, Histology, Injection, Virus, InjectionVirus,
                          OrganicLabel, ScanRun, Slide, SlideCziToTif,
                          RawSection, Section)

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
        # models.DateField: {'widget': DateTimeInput(attrs={'size':'20','type':'date'})},
        models.DateField: {'widget': AdminDateWidget(attrs={'size':'20'})},
        models.IntegerField: {'widget': NumberInput(attrs={'size':'20'})},
        models.TextField: {'widget': Textarea(attrs={'rows':4, 'cols':40})},
    }

    def is_active(self, instance):
        return instance.active == 1

    is_active.boolean = True

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
                '<a class="button" href="{}">Create</a>&nbsp;',
                reverse('admin:section-creation', args=[obj.pk]),
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
    readonly_fields = ['scan_run']

    def save_model(self, request, obj, form, change):
        obj.user = request.user
        super().save_model(request, obj, form, change)
        slide_status = form.cleaned_data.get('slide_status')
        qc_1 = form.cleaned_data.get('scene_qc_1')
        qc_2 = form.cleaned_data.get('scene_qc_2')
        qc_3 = form.cleaned_data.get('scene_qc_3')
        qc_4 = form.cleaned_data.get('scene_qc_4')
        qc_5 = form.cleaned_data.get('scene_qc_5')
        qc_6 = form.cleaned_data.get('scene_qc_6')
        scene_numbers = []

        def set_bad_tifs(scene_number):
            tifs = SlideCziToTif.objects.filter(slide_id=obj.id).filter(scene_number__in=scene_number)
            for tif in tifs:
                tif.active = 0
                tif.save()

        if qc_1 is not None:
            scene_numbers.append(1)
        if qc_2 is not None:
            scene_numbers.append(2)
        if qc_3 is not None:
            scene_numbers.append(3)
        if qc_4 is not None:
            scene_numbers.append(4)
        if qc_5 is not None:
            scene_numbers.append(5)
        if qc_6 is not None:
            scene_numbers.append(6)

        set_bad_tifs(scene_numbers)


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
    list_display = ('file_name', 'image_tag', 'histogram', 'is_active', 'scene_number', 'channel','file_size_mb')
    search_fields = ('file_name',)
    ordering = ['section_number']
    readonly_fields = ['slide','scene_number', 'section_number','channel', 'file_size', 'processing_duration', 'width','height']
    list_per_page = 25
    class Media:
        css = {
            'all': ('admin/css/thumbnail.css',)
        }

class SectionAdmin(AtlasAdminModel, ExportCsvMixin):
    list_display = ('prep_id', 'section_qc', 'ch_1_path', 'ch_2_path', 'ch_3_path', 'ch_4_path')
    list_filter = ('prep_id', )
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<prep_id>', self.process_section,  name='section-creation',
            )
        ]
        return custom_urls + urls

    def process_section(self, request, prep_id, *args, **kwargs):
        animal = Animal.objects.get(pk=prep_id)
        orderby = animal.section_direction
        with connection.cursor() as cursor:
            cursor.callproc('create_sections', [prep_id, orderby])

        bad_ids =  Section.objects.values_list('id', flat=True).filter(prep_id__exact=prep_id).filter(section_qc='Replace')
        junk = ""
        if bad_ids:
            all_sections = Section.objects.filter(prep_id__exact=prep_id)
            data = all_sections.values('id','ch_1_path', 'ch_2_path','ch_3_path','ch_4_path')
            df = pd.DataFrame.from_records(data)
            df.set_index(['id'], inplace=True)
            df.fillna(method='bfill', inplace=True)
            df.fillna(method='ffill', inplace=True)
            for index, row in df.iterrows():
                if index in bad_ids:
                    section = Section.objects.get(id=index)
                    section.ch_1_path = row['ch_1_path']
                    section.ch_2_path = row['ch_2_path']
                    section.ch_3_path = row['ch_3_path']
                    section.ch_4_path = row['ch_4_path']
                    section.save()
                    junk += "<p>{} {}</p>".format(index, row['ch_1_path'])

        RawSection.objects.filter(prep_id__exact=prep_id).delete()
        sections =  Section.objects.filter(prep_id__exact=prep_id).order_by('section_number')
        i = 0

        def create_raw_row(i, prep_id, file_name, channel):
            rawsection = RawSection()
            rawsection.prep_id = prep_id
            rawsection.source_file = file_name
            rawsection.destination_file = '{}_C{}.tif'.format(str(i), str(channel))
            rawsection.section_number = i
            rawsection.channel = channel
            rawsection.save()

        for i, section in enumerate(sections):
            if section.ch_1_path is not None:
                create_raw_row(i, prep_id, section.ch_1_path, 1)
            if section.ch_2_path is not None:
                create_raw_row(i, prep_id, section.ch_2_path, 2)
            if section.ch_3_path is not None:
                create_raw_row(i, prep_id, section.ch_3_path, 3)
            if section.ch_4_path is not None:
                create_raw_row(i, prep_id, section.ch_4_path, 4)

        cursor.close()

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

