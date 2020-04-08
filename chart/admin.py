from django.contrib import admin
from .models import Task, ProgressLookup, Resource, Roles
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


