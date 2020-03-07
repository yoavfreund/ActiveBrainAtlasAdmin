from django.contrib import admin
from .models import Resource, Roles, Schedule, Task
from treebeard.admin import TreeAdmin
from treebeard.forms import movenodeform_factory
# Register your models here.

class TaskAdmin(TreeAdmin):
    form = movenodeform_factory(Task)

admin.site.register(Roles)
admin.site.register(Resource)
admin.site.register(Schedule)
admin.site.register(Task)
