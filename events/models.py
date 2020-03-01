from django.db import models
from django.urls import reverse

from brain.models import Animal

# Create your models here.
class Event(models.Model):
    prep = models.ForeignKey(Animal, models.DO_NOTHING)
    day = models.DateField(u'Date of the event', help_text=u'Date of the event')
    notes = models.TextField(u'Textual Notes', help_text=u'Textual Notes', blank=True, null=True)
    active = models.IntegerField(default = 1, editable = False)
    created = models.DateTimeField(auto_now_add=True)
 
    class Meta:
        db_table = 'schedule'
        verbose_name = u'Scheduling'
        verbose_name_plural = u'Scheduling'
        
    def get_absolute_url(self):
        notes = self.notes[0:10]
        url = reverse('admin:%s_%s_change' % (self._meta.app_label, self._meta.model_name), args=[self.id])
        return u'<a href="%s">%s</a>' % (url, notes)

        