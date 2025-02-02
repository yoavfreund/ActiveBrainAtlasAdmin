from neuroglancer.atlas import get_centers_dict
from brain.models import Animal
import json
from django.conf import settings
from django.contrib import admin, messages
from django.forms import TextInput
from django.urls import reverse, path
from django.utils.html import format_html, escape
from django.template.response import TemplateResponse
from brain.admin import AtlasAdminModel, ExportCsvMixin
from pygments import highlight
from pygments.lexers import JsonLexer
from pygments.formatters import HtmlFormatter
from django.utils.safestring import mark_safe
from django.contrib.auth import get_user_model
from neuroglancer.models import InputType, LAUREN_ID, LayerData, UrlModel, Structure, Points, Transformation, COL_LENGTH, ATLAS_RAW_SCALE, \
    ATLAS_Z_BOX_SCALE, Z_LENGTH
import plotly.express as px
from plotly.offline import plot
from django.db import models
from neuroglancer.dash_view import dash_scatter_view
from neuroglancer.forms import LayerForm
import plotly.express as px
import numpy as np
import pandas as pd
from timeit import default_timer as timer
from neuroglancer.com_box_plot import prepare_table_for_plot,add_trace,get_common_structure
from plotly.subplots import make_subplots
from neuroglancer.models import UrlModel, LayerData,ComBoxplot, LAUREN_ID
from plotly.subplots import make_subplots



def datetime_format(dtime):
    return dtime.strftime("%d %b %Y %H:%M")


@admin.register(UrlModel)
class UrlModelAdmin(admin.ModelAdmin):
    formfield_overrides = {
        models.CharField: {'widget': TextInput(attrs={'size':'100'})},
    }
    list_display = ('animal', 'open_neuroglancer', 'open_multiuser', 'person', 'updated')
    ordering = ['-vetted', '-updated']
    readonly_fields = ['pretty_url', 'created', 'user_date', 'updated']
    exclude = ['url']
    list_filter = ['updated', 'created', 'vetted']
    search_fields = ['url', 'comments']

    def pretty_url(self, instance):
            """Function to display pretty version of our data"""

            # Convert the data to sorted, indented JSON
            response = json.dumps(instance.url, sort_keys=True, indent=2)
            # Truncate the data. Alter as needed
            #response = response[:5000]
            # Get the Pygments formatter
            formatter = HtmlFormatter(style='colorful')
            # Highlight the data
            response = highlight(response, JsonLexer(), formatter)
            # Get the stylesheet
            style = "<style>" + formatter.get_style_defs() + "</style><br>"
            # Safe the output
            return mark_safe(style + response)

    pretty_url.short_description = 'Formatted URL'    


    def open_neuroglancer(self, obj):
        host = "https://activebrainatlas.ucsd.edu/ng"
        if settings.DEBUG:
            host = "http://127.0.0.1:8080"

        comments = escape(obj.comments)
        links = f'<a target="_blank" href="{host}?id={obj.id}">{comments}</a>'
        return format_html(links)

    def open_multiuser(self, obj):
        host = "https://activebrainatlas.ucsd.edu/ng_multi"
        if settings.DEBUG:
            host = "http://127.0.0.1:8080"

        comments = "Testing"
        links = f'<a target="_blank" href="{host}?id={obj.id}&amp;multi=1">{comments}</a>'
        return format_html(links)


    open_neuroglancer.short_description = 'Neuroglancer'
    open_neuroglancer.allow_tags = True
    open_multiuser.short_description = 'Multi-User'
    open_multiuser.allow_tags = True
 
@admin.register(Points)
class PointsAdmin(admin.ModelAdmin):
    list_display = ('animal', 'comments', 'person','show_points', 'updated')
    ordering = ['-created']
    readonly_fields = ['url', 'created', 'user_date', 'updated']
    search_fields = ['comments']
    list_filter = ['created', 'updated','vetted']


    def created_display(self, obj):
        return datetime_format(obj.created)
    created_display.short_description = 'Created'    

    def get_queryset(self, request):
        points = Points.objects.filter(url__layers__contains={'type':'annotation'})
        return points


    def show_points(self, obj):
        display_2dgraph = obj.point_count

        return format_html(
            '<a href="{}">3D Graph</a>&nbsp; <a href="{}">Data</a> <a href="{}" style="{}";>2D Graph</a>&nbsp; ',
            reverse('admin:points-3D-graph', args=[obj.pk]),
            reverse('admin:points-data', args=[obj.pk]),
            reverse('admin:points-2D-graph', args=[obj.pk]),
            display_2dgraph
        )


    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(r'scatter/<pk>', dash_scatter_view, name="points-2D-graph"),
            path('points-3D-graph/<id>', self.view_points_3Dgraph, name='points-3D-graph'),
            path('points-data/<id>', self.view_points_data, name='points-data'),
        ]
        return custom_urls + urls


    def view_points_3Dgraph(self, request, id, *args, **kwargs):
        """
        3d graph
        :param request: http request
        :param id:  id of url
        :param args:
        :param kwargs:
        :return: 3dGraph in a django template
        """
        urlModel = UrlModel.objects.get(pk=id)
        df = urlModel.points
        plot_div = "No points available"
        if df is not None and len(df) > 0:
            self.display_point_links = True
            fig = px.scatter_3d(df, x='X', y='Y', z='Section',
                                color='Layer', opacity=0.7)
            fig.update_layout(
                scene=dict(
                    xaxis=dict(nticks=4, range=[20000, 60000], ),
                    yaxis=dict(nticks=4, range=[10000, 30000], ),
                    zaxis=dict(nticks=4, range=[100, 350], ), ),
                width=1200,
                margin=dict(r=0, l=0, b=0, t=0))
            fig.update_traces(marker=dict(size=2),
                              selector=dict(mode='markers'))

            plot_div = plot(fig, output_type='div', include_plotlyjs=False)


        context = dict(
            self.admin_site.each_context(request),
            title=urlModel.comments,
            chart=plot_div
        )
        return TemplateResponse(request, "points_graph.html", context)

    def view_points_data(self, request, id, *args, **kwargs):
        urlModel = UrlModel.objects.get(pk=id)
        df = urlModel.points
        result = 'No data'
        display = False
        if df is not None and len(df) > 0:
            display = True
            df = df.sort_values(by=['Layer','Section', 'X', 'Y'])
            result = df.to_html(index=False, classes='table table-striped table-bordered', table_id='tab')
        context = dict(
            self.admin_site.each_context(request),
            title=urlModel.comments,
            chart=result,
            display=display,
            opts=UrlModel._meta,
        )
        return TemplateResponse(request, "points_table.html", context)

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Structure)
class StructureAdmin(admin.ModelAdmin, ExportCsvMixin):
    list_display = ('abbreviation', 'description','color','show_hexadecimal','active','created_display')
    ordering = ['abbreviation']
    readonly_fields = ['created']
    list_filter = ['created', 'active']
    #list_filter = (VettedFilter,)
    search_fields = ['abbreviation', 'description']

    def created_display(self, obj):
        return datetime_format(obj.created)
    created_display.short_description = 'Created'    

    def show_hexadecimal(self, obj):
        return format_html('<div style="background:{}">{}</div>',obj.hexadecimal,obj.hexadecimal)

    show_hexadecimal.short_description = 'Hexadecimal'



def atlas_scale_xy(x):
    """
    0.325 is the scale for Neurotrace brains
    This converts the atlas coordinates to neuroglancer XY coordinates
    :param x: x or y coordinate
    :return: an integer that is in neuroglancer scale
    """
    atlas_box_center = COL_LENGTH // 2
    result = (atlas_box_center + x) * (ATLAS_RAW_SCALE / 0.325)
    return int(round(result))

def atlas_scale_section(section):
    """
    scales the z (section) to neuroglancer coordinates
    :param section:
    :return:
    """
    atlas_box_center = Z_LENGTH // 2
    result = atlas_box_center + section * ATLAS_RAW_SCALE/ATLAS_Z_BOX_SCALE
    return int(round(result))

def make_inactive(modeladmin, request, queryset):
    queryset.update(active=False)
make_inactive.short_description = "Mark selected COMs as inactive"

def make_active(modeladmin, request, queryset):
    queryset.update(active=True)
make_active.short_description = "Mark selected COMs as active"


@admin.register(Transformation)
class TransformationAdmin(AtlasAdminModel):
    list_display = ('prep_id', 'person', 'input_type', 'com_name','active','created', 'com_count')
    ordering = ['com_name']
    readonly_fields = ['created', 'updated']
    list_filter = ['created', 'active']
    search_fields = ['prep_id', 'com_name']

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "prep":
            kwargs["queryset"] = Animal.objects.filter(layerdata__active=True).distinct().order_by()
        if db_field.name == "person":
            UserModel = get_user_model()
            com_users = LayerData.objects.values_list('person', flat=True).distinct().order_by()
            kwargs["queryset"] = UserModel.objects.filter(id__in=com_users)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def com_count(self, obj):
        count = LayerData.objects.filter(prep_id=obj.prep_id)\
            .filter(input_type=obj.input_type).filter(layer='COM')\
            .filter(person_id=obj.person_id).filter(active=True).count()
        return count

    com_count.short_description = "Active COMS"

    def save_model(self, request, obj, form, change):
        obj.user = request.user
        count = LayerData.objects.filter(prep=obj.prep)\
            .filter(input_type=obj.input_type).filter(layer='COM')\
            .filter(person=obj.person).filter(active=True).count()        
        if count < 1:
            messages.add_message(request, messages.WARNING, 'There no COMs associated with that animal/user/input type combination. Please correct it.')
            return
        else:
            super().save_model(request, obj, form, change)
            LayerData.objects.filter(prep=obj.prep)\
                .filter(input_type=obj.input_type).filter(layer='COM')\
                .filter(person=obj.person).filter(active=True).update(transformation=obj)

@admin.register(InputType)
class InputTypeAdmin(AtlasAdminModel):
    list_display = ('id', 'input_type', 'description', 'active','created')
    ordering = ['id']
    readonly_fields = ['created', 'updated']
    list_filter = ['created', 'active']
    search_fields = ['input_type', 'description']

@admin.register(LayerData)
class LayerDataAdmin(AtlasAdminModel):
    list_display = ('prep_id', 'structure','x_f','y_f', 'z_f', 'active','updated', 'input_type')
    ordering = ['prep', 'layer']
    excluded_fields = ['created', 'updated']
    list_filter = ['created', 'active','input_type']
    search_fields = ['prep__prep_id', 'structure__abbreviation', 'layer']
    #change_form_template = "add_annotation.html"
    #form = LayerForm


    def save_model(self, request, obj, form, change):
        obj.person = request.user
        super().save_model(request, obj, form, change)

    def x_f(self, obj):
        number = int(obj.x)
        #if 'atlas' in str(obj.prep_id).lower():
        #    number = atlas_scale_xy(obj.x)
        return format_html(f"<div style='text-align:right;'>{number}</div>")
    def y_f(self, obj):
        number = int(obj.y)
        #if 'atlas' in str(obj.prep_id).lower():
        #    number = atlas_scale_xy(obj.y)
        return format_html(f"<div style='text-align:right;'>{number}</div>")
    def z_f(self, obj):
        number = int(obj.section)
        #if 'atlas' in str(obj.prep_id).lower():
        #    number = atlas_scale_section(obj.section)
        return format_html(f"<div style='text-align:right;'>{number}</div>")

    x_f.short_description = "X"
    y_f.short_description = "Y"
    z_f.short_description = "Z"

@admin.register(ComBoxplot)
class ComBoxplotAdmin(admin.ModelAdmin):
    change_list_template = "alignment.html"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        INPUT_TYPE_MANUAL = 1
        INPUT_TYPE_CORRECTED = 2
        brains = list(LayerData.objects.filter(active=True)\
            .filter(input_type__id=INPUT_TYPE_CORRECTED)\
            .filter(layer='COM')\
            .filter(active=True)\
            .exclude(prep_id__in=['Atlas'])\
            .values_list('prep_id', flat=True).distinct().order_by('prep_id'))
        atlas_centers = get_centers_dict('atlas', input_type_id=INPUT_TYPE_MANUAL, person_id=LAUREN_ID)
        common_structures = get_common_structure(brains)
        common_structures.remove('4N_L')
        common_structures.remove('10N_L')

        fig = make_subplots(
            rows=1, cols=1,
            subplot_titles=("Rigid Alignment Error on Original COMs", "Rigid Alignment Error After Correction"))
        
        df1 = prepare_table_for_plot(atlas_centers, common_structures,
            brains,
            person_id=2,
            input_type_id=INPUT_TYPE_MANUAL)
        #print(df1.query("structure == '10N_L'").head())
        
        
        add_trace(df1,fig,1)
        fig.update_xaxes(tickangle=45, showticklabels = True)
        fig.update_layout(
            autosize=False,
            width=800,
            height=500,
            margin=dict(l=10, r=10, b=10, t=10, pad=4),
            paper_bgcolor="LightSteelBlue",
        )  
        gantt_div = plot(fig, output_type='div', include_plotlyjs=False)
        title = 'Rigid Alignment Error for ' + ", ".join(brains)
        extra_context = extra_context or {"gantt_div": gantt_div, 'title':title}

        # Call the superclass changelist_view to render the page
        return super().changelist_view(request, extra_context=extra_context)


