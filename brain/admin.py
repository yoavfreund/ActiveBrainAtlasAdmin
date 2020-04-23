from django.contrib import admin
from django.db.models import Max
from django.forms import TextInput, Textarea, DateInput, NumberInput, forms
from django.db import models
import csv
from django.http import HttpResponse
from django.utils.html import format_html
from django.urls import reverse
from django.urls import path
from django.template.response import TemplateResponse
from django.db import connection
from django.contrib.admin.widgets import AdminDateWidget

from brain.forms import save_slide_model
from brain.models import (Animal, Histology, Injection, Virus, InjectionVirus,
                          OrganicLabel, ScanRun, Slide, SlideCziToTif, Section, RawSection)


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

2
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


class TifInline(admin.TabularInline):
    model = SlideCziToTif
    fields = ('file_name','scene_number')
    readonly_fields = ['file_name', 'scene_number']
    ordering = ['-active', 'scene_number']
    extra = 0
    can_delete = False

    def get_queryset(self, request):
        qs = super(TifInline, self).get_queryset(request)
        return qs.filter(active=1).filter(channel=1)

    def has_add_permission(self, request, obj=None):
        return False




class SlideAdmin(AtlasAdminModel, ExportCsvMixin):
    list_display = ('prep_id', 'file_name', 'slide_status', 'scene_qc_1', 'scene_qc_2', 'scene_qc_3', 'scene_qc_4', 'scene_count')
    search_fields = ['scan_run__prep__prep_id']
    ordering = ['file_name', 'created']
    fields = ['file_name', 'scan_run',  'slide_physical_id', 'slide_status', 'rescan_number',
              'insert_before_one','scene_qc_1',
              'insert_between_one_two','scene_qc_2',
              'insert_between_two_three','scene_qc_3',
              'insert_between_three_four','scene_qc_4',
              'insert_between_four_five','scene_qc_5',
              'insert_between_five_six','scene_qc_6',
              'comments', 'processed']
    readonly_fields = ['file_name', 'slide_physical_id','scan_run', 'processed', 'rescan_number', 'file_size']

    inlines = [TifInline, ]

    class Media:
        css = {"all": ("css/admin.css",)}

    def scene_count(self, obj):
        count = SlideCziToTif.objects.filter(slide_id=obj.id).filter(channel=1).filter(active=1).count()
        return count

    scene_count.short_description = "Active Scenes"

    def save_model(self, request, obj, form, change):
        obj.user = request.user
        save_slide_model(self, request, obj, form, change)
        super().save_model(request, obj, form, change)


    def has_delete_permission(self, request, obj=None):
        return False



    def prep_id(self, instance):
        return instance.scan_run.prep.prep_id


class SlideCziToTifAdmin(AtlasAdminModel, ExportCsvMixin):
    list_display = ('file_name', 'histogram', 'is_active', 'scene_number', 'channel','file_size_mb')
    search_fields = ('file_name',)
    ordering = ['file_name']
    readonly_fields = ['slide','scene_number', 'channel', 'file_size', 'processing_duration', 'width','height']
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
        histology = Histology.objects.get(prep_id=prep_id)
        section_order = 'section_number'
        orderby = histology.side_sectioned_first
        with connection.cursor() as cursor:
            cursor.callproc('create_sections', [prep_id, orderby])
        cursor.close()

        if orderby == 'DESC':
            sections =  Section.objects.filter(prep_id__exact=prep_id)\
                .order_by('-slide_physical_id', '-scene_number')
            raw_sections = RawSection.objects.filter(prep_id__exact=prep_id)\
                .order_by('-section_number', 'channel')
        else:
            sections = Section.objects.filter(prep_id__exact=prep_id)\
                .order_by('slide_physical_id', 'scene_number')
            raw_sections = RawSection.objects.filter(prep_id__exact=prep_id)\
                .order_by('section_number', 'channel')

        # fix section number in raw_sections to increment every 3
        channels = raw_sections.aggregate(Max('channel'))
        channels = channels['channel__max']

        if channels > 0:
            new_section_number = 0
            for i, rsection in enumerate(raw_sections):
                if i % channels == 0:
                    new_section_number += 1
                rsection.section_number = new_section_number
                rsection.save()

        context = self.admin_site.each_context(request)
        context['opts'] = self.model._meta
        context['results'] = sections
        context['counter'] = 1
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

