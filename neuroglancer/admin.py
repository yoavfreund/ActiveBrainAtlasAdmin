from django.conf import settings
from django.contrib import admin
from django.forms import TextInput
from django.urls import reverse, path
from django.utils.html import format_html, escape
from django.template.response import TemplateResponse
import neuroglancer.dash_apps
import neuroglancer.dash_point_table

from neuroglancer.models import UrlModel, Structure, Points, CenterOfMass, COL_LENGTH, ROW_LENGTH, ATLAS_RAW_SCALE, \
    ATLAS_Z_BOX_SCALE, Z_LENGTH
import plotly.express as px
from plotly.offline import plot
from django.db import models
from neuroglancer.dash_view import dash_scatter_view

def datetime_format(dtime):
    return dtime.strftime("%d %b %Y %H:%M")



@admin.register(UrlModel)
class UrlModelAdmin(admin.ModelAdmin):
    formfield_overrides = {
        models.CharField: {'widget': TextInput(attrs={'size':'100'})},
    }
    list_display = ('animal', 'open_neuroglancer', 'open_multiuser', 'person', 'updated_display')
    ordering = ['-vetted', '-updated']
    readonly_fields = ['url', 'created', 'user_date', 'updated']
    list_filter = ['created', 'vetted']
    search_fields = ['url', 'comments']
    #user_id = None

    #def get_queryset(self, request):
    #    self.user_id = request.user.id
    #    return super(UrlModelAdmin, self).get_queryset(request)

    def updated_display(self, obj):
        return datetime_format(obj.updated)
    updated_display.short_description = 'Updated'    


    def open_oldneuroglancer(self, obj):
        host = "https://activebrainatlas.ucsd.edu/ng/"
        return format_html('<a target="_blank" href="{}?id={}&amp;#!{}">Long URL</a>',
                           host, obj.id, escape(obj.url))

    def open_neuroglancer(self, obj):
        host = "https://activebrainatlas.ucsd.edu/ng_test/"
        if settings.DEBUG:
            host = "http://127.0.0.1:8080"

        comments = escape(obj.comments)
        links = f'<a target="_blank" href="{host}?id={obj.id}&amp;multi=0">{comments}</a>'
        return format_html(links)

    def open_multiuser(self, obj):
        host = "https://activebrainatlas.ucsd.edu/ng_multi"

        comments = escape(obj.comments)
        links = f'<a target="_blank" href="{host}?id={obj.id}&amp;multi=1">{comments}</a>'
        #links = f'<a target="_blank" href="{host}/{obj.id}/1">{comments}</a>'
        return format_html(links)


    open_oldneuroglancer.short_description = 'Long URL'
    open_oldneuroglancer.allow_tags = True
    open_neuroglancer.short_description = 'Neuroglancer'
    open_neuroglancer.allow_tags = True
    open_multiuser.short_description = 'Multi-User'
    open_multiuser.allow_tags = True
 
@admin.register(Points)
class PointsAdmin(admin.ModelAdmin):
    list_display = ('animal', 'comments', 'person','show_points', 'created_display', 'updated_display')
    ordering = ['-created']
    readonly_fields = ['url', 'created', 'user_date', 'updated']
    search_fields = ['comments']

    def updated_display(self, obj):
        return datetime_format(obj.updated)
    updated_display.short_description = 'Updated'    

    def created_display(self, obj):
        return datetime_format(obj.created)
    created_display.short_description = 'Created'    

    def get_queryset(self, request):
        points = Points.objects.filter(url__contains='annotations')
        points = points.filter(url__contains='point')
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
            display=display
        )
        return TemplateResponse(request, "points_table.html", context)

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Structure)
class StructureAdmin(admin.ModelAdmin):
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


def altas_scale_xy(x):
    """
    0.325 is the scale for Neurotrace brains
    This converts the atlas coordinates to neuroglancer XY coordinates
    :param x: x or y coordinate
    :return: an integer that is in neuroglancer scale
    """
    atlas_box_center = COL_LENGTH // 2
    result = (atlas_box_center + x) * (ATLAS_RAW_SCALE / 0.325)
    return int(round(result))

def altas_scale_section(section):
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

@admin.register(CenterOfMass)
class CenterOfMassAdmin(admin.ModelAdmin):
    list_display = ('prep_id', 'structure','x_f','y_f', 'z_f', 'active','updated_display', 'person', 'input_type')
    ordering = ['prep_id', 'structure']
    readonly_fields = ['created']
    list_filter = ['created', 'active']
    search_fields = ('prep__prep_id',)
    actions = [make_inactive, make_active]

    def x_f(self, obj):
        number = int(obj.x)
        if 'atlas' in str(obj.prep_id).lower():
            number = altas_scale_xy(obj.x)
        return format_html(f"<div style='text-align:right;'>{number}</div>")
    def y_f(self, obj):
        number = int(obj.y)
        if 'atlas' in str(obj.prep_id).lower():
            number = altas_scale_xy(obj.y)
        return format_html(f"<div style='text-align:right;'>{number}</div>")
    def z_f(self, obj):
        number = int(obj.section)
        if 'atlas' in str(obj.prep_id).lower():
            number = altas_scale_section(obj.section)
        return format_html(f"<div style='text-align:right;'>{number}</div>")

    x_f.short_description = "X"
    y_f.short_description = "Y"
    z_f.short_description = "Z"


    def updated_display(self, obj):
        return datetime_format(obj.updated)
    updated_display.short_description = 'Updated'    
