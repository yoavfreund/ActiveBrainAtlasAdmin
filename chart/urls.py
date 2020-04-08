__author__ = 'sayone-30'
from django.conf.urls import url
from .views import TaskView
from django.views.generic import TemplateView

urlpatterns = [
    url(r'^$', TemplateView.as_view(template_name='tasks.html')),
    url(r'^task/(?P<schedule_id>\d+)/$', TaskView.as_view())
]


