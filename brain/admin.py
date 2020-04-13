from django.contrib import admin
from django.contrib.admin.views.main import ChangeList
from django.forms import TextInput, Textarea, DateInput, NumberInput
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
from adminsortable.models import Sortable
from adminsortable.admin import SortableAdmin
from adminsortable.admin import NonSortableParentAdmin, SortableStackedInline

from brain.forms import TifForm, TifFormSet
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


class TifInline(admin.TabularInline):
    model = SlideCziToTif
    fields = ('file_name','scene_number', 'active')
    #readonly_fields = ['file_name']
    form = TifForm
    formset = TifFormSet
    extra = 0
    can_delete = False

class SlideAdmin(AtlasAdminModel, ExportCsvMixin):
    list_display = ('prep_id', 'file_name', 'slide_status', 'scene_qc_1', 'scene_qc_2', 'scene_qc_3', 'scene_qc_4', 'scenes')
    search_fields = ['scan_run__prep__prep_id']
    ordering = ['file_name', 'created']
    readonly_fields = ['file_name', 'slide_physical_id','scan_run', 'processed', 'file_size']
    fields = ['file_name', 'scan_run',  'slide_physical_id', 'slide_status',
              'insert_before_one','scene_qc_1',
              'insert_between_one_two','scene_qc_2',
              'insert_between_two_three','scene_qc_3',
              'insert_between_three_four','scene_qc_4',
              'insert_between_four_five','scene_qc_5',
              'insert_between_five_six','scene_qc_6',
              'comments', 'processed']

    """
    inlines = [TifInline, ]
    class Media:
        css = {"all": ("css/admin.css",)}

    def scenes(self, obj):
        tif_list = [tif.file_name for tif in SlideCziToTif.objects\
                .filter(channel=1)\
                .filter(slide_id=obj.id).order_by('scene_number')]
        #tifs = ", ".join(tif_list)
        return len(tif_list)
    scenes.short_description = "Scenes"
    """


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

        ins_1 = form.cleaned_data.get('insert_before_one')
        ins_2 = form.cleaned_data.get('insert_between_one_two')
        ins_3 = form.cleaned_data.get('insert_between_two_three')
        ins_4 = form.cleaned_data.get('insert_between_three_four')
        ins_5 = form.cleaned_data.get('insert_between_four_five')
        ins_6 = form.cleaned_data.get('insert_between_five_six')

        # update slide_czi_to_tif set section_number = section_number + X
        # where section_number >= Y

        scene_1_tifs = SlideCziToTif.objects.filter(slide_id=obj.id).filter(scene_number=1)
        scene_2_tifs = SlideCziToTif.objects.filter(slide_id=obj.id).filter(scene_number=2)
        scene_3_tifs = SlideCziToTif.objects.filter(slide_id=obj.id).filter(scene_number=3)
        scene_4_tifs = SlideCziToTif.objects.filter(slide_id=obj.id).filter(scene_number=4)

        # note, scenes usually range from 1 -> 4
        # insert section at 1st scene and increment the other 3 scenes
        # the data originally comes from the czi metadata. That data always
        # starts at 0 and increments up, sometimes there is no last section
        # You usually want 4 scenes/slide, unless it is the last.
        if ins_1 == 1 and not scene_4_tifs:
            # scene 1 is missing
            for tif in scene_3_tifs:
                tif.scene_number = 4
                tif.save()
            for tif in scene_2_tifs:
                tif.scene_number = 3
                tif.save()
            for tif in scene_1_tifs:
                newtif = tif
                newtif.pk = None
                tif.scene_number = 2
                tif.save()
                newtif.save()

        scene_1_tifs = SlideCziToTif.objects.filter(slide_id=obj.id).filter(scene_number=1)
        scene_2_tifs = SlideCziToTif.objects.filter(slide_id=obj.id).filter(scene_number=2)
        scene_3_tifs = SlideCziToTif.objects.filter(slide_id=obj.id).filter(scene_number=3)
        scene_4_tifs = SlideCziToTif.objects.filter(slide_id=obj.id).filter(scene_number=4)
        # clone 1st scene to #2 and increment 3 and 4
        # insert section at 2nd scene and increment the other scenes
        if ins_2 == 1 and not scene_4_tifs:
            # scene 2 is missing
            for tif in scene_3_tifs:
                tif.scene_number = 4
                tif.save()
            for tif in scene_2_tifs:
                tif.scene_number = 3
                tif.save()
            for tif in scene_1_tifs:
                newtif = tif
                newtif.pk = None
                newtif.scene_number = 2
                newtif.save()

        scene_1_tifs = SlideCziToTif.objects.filter(slide_id=obj.id).filter(scene_number=1)
        scene_2_tifs = SlideCziToTif.objects.filter(slide_id=obj.id).filter(scene_number=2)
        scene_3_tifs = SlideCziToTif.objects.filter(slide_id=obj.id).filter(scene_number=3)
        scene_4_tifs = SlideCziToTif.objects.filter(slide_id=obj.id).filter(scene_number=4)

        # clone 2nd scene to #3 and increment 3
        # insert section at 3rd scene
        if ins_3 == 1 and not scene_4_tifs:
            # scene 3 is missing
            for tif in scene_3_tifs:
                tif.scene_number = 4
                tif.save()
            for tif in scene_2_tifs:
                tif.scene_number = 3
                tif.save()
                newtif = tif
                newtif.pk = None
                newtif.scene_number = 2
                newtif.save()

        tifs = SlideCziToTif.objects.filter(slide_id=obj.id).order_by('scene_number')
        for tif in tifs:
            if qc_1 == 'End' and tif.scene_number == 1:
                tif.last_scene = 1
            if qc_2 == 'End' and tif.scene_number == 2:
                tif.last_scene = 1
            if qc_3 == 'End' and tif.scene_number == 3:
                tif.last_scene = 1
            if qc_4 == 'End' and tif.scene_number == 4:
                tif.last_scene = 1
            if qc_5 == 'End' and tif.scene_number == 5:
                tif.last_scene = 1
            if qc_6 == 'End' and tif.scene_number == 6:
                tif.last_scene = 1
            tif.save()

        obj.scenes = SlideCziToTif.objects.filter(slide_id=obj.id).filter(channel_index=0).count()
        obj.save()



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
        orderby = str(animal.section_direction)
        section_order = 'section_number'
        if orderby.upper() == 'DESC':
            section_order = '-section_number'
        with connection.cursor() as cursor:
            cursor.callproc('create_sections', [prep_id, orderby])
        """
        bad_ids =  Section.objects.values_list('id', flat=True)\
            .filter(prep_id__exact=prep_id).filter(section_qc='Replaced')\
            .order_by(section_order)
        if bad_ids:
            all_sections = Section.objects.filter(prep_id__exact=prep_id).order_by(section_order)
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

        """
        RawSection.objects.filter(prep_id__exact=prep_id).delete()
        sections =  Section.objects.filter(prep_id__exact=prep_id).order_by('section_number')

        i = 0

        def create_raw_row(i, prep_id, file_name, channel):
            rawsection = RawSection()
            rawsection.prep_id = prep_id
            rawsection.source_file = file_name
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

