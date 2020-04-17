import random

from django.contrib import admin
from plotly.offline import plot
import plotly.graph_objects as go


from .models import Task, ProgressLookup, Resource, Roles, TaskView


# Register your models here.


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name')
    ordering = ['last_name']


@admin.register(Roles)
class RolesAdmin(admin.ModelAdmin):
    list_display = ('name',)
    ordering = ['name']


@admin.register(ProgressLookup)
class ProgressLookupAdmin(admin.ModelAdmin):
    list_display = ('ordinal', 'description', 'category', 'script')
    search_fields = ('description',)
    ordering = ['ordinal']


@admin.register(Task)
class ProgressDataAdmin(admin.ModelAdmin):
    list_display = ('prep_id', 'task', 'is_complete')
    search_fields = ('prep',)
    ordering = ['prep', 'lookup']

    def is_complete(self, instance):
        return instance.completed == 1

    is_complete.boolean = True

    def task(self, instance):
        return instance.lookup.description

    def prep_id(self, instance):
        return instance.prep.prep_id

    def ordinal(self, instance):
        return instance.lookup.ordinal


@admin.register(TaskView)
class TaskViewAdmin(admin.ModelAdmin):
    list_display = ('prep_id', 'percent_complete')
    change_list_template = "admin/task_view.html"
    ordering = ['prep_id']
    readonly_fields = ['prep_id', 'percent_complete']


    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_actions(self, request):
        actions = super(TaskViewAdmin, self).get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

# add url to view more detail

    def changelist_view(self, request, extra_context=None):
        # Aggregate new subscribers per day
        tasks = TaskView.objects.order_by('prep_id').all()
        lookups = ProgressLookup.objects.order_by('ordinal').all()

        lookup_list = []
        id_list = []
        for i, look in enumerate(lookups):
            lookup_list.append(look.description)
            id_list.append(i)

        x = []
        y = []
        for row in tasks:
            y.append(row.prep_id)
            x.append(row.complete)

        limit = len(lookup_list)
        get_colors = lambda n: list(map(lambda i: "#" + "%06x" % random.randint(0, 0xFFFFFF), range(n)))
        colors = get_colors(len(x))
        fig = go.Figure(data=[go.Bar(x=x, y=y, orientation='h', marker=dict(color=colors) )])
        fig.update_layout(xaxis_showgrid=True, yaxis_showgrid=True, height=600)
        fig.update_xaxes(ticks='outside',tickwidth=2, tickangle=45, tickcolor='crimson', ticklen=10, range=[0,limit])

        fig.update_layout(autosize=True, xaxis=dict(tickmode='array', tickvals=id_list, ticktext=lookup_list),
                          margin=dict(l=20, r=20, t=20, b=280),
                          paper_bgcolor="LightSteelBlue",
                          )
        gantt_div = plot(fig, output_type='div', include_plotlyjs=False)
        # Serialize and attach the workflow data to the template context
        extra_context = extra_context or {"gantt_div": gantt_div, 'title':'Pipeline Progress by Animal'}

        # Call the superclass changelist_view to render the page
        return super().changelist_view(request, extra_context=extra_context)
