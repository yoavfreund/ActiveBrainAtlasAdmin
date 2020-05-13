from django import forms
from django.core.exceptions import ValidationError

from scheduler.models import Schedule
"""
class ScheduleAdminForm(forms.ModelForm):
    class Meta:
        model = Schedule

    def clean(self):
        cleaned_data = self.cleaned_data
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        location = cleaned_data.get('location')

        department = cleaned_data.get('department')
        isDepartmentSuggested = cleaned_data.get('isDepartmentSuggested')
        if department == None and not isDepartmentSuggested:
            raise forms.ValidationError(u"You haven't set a valid department. Do you want to continue?")
        return cleaned_data
"""


def save_schedule_model(self, request, obj, form, change):
    start_time = form.cleaned_data.get('start_time')
    end_time = form.cleaned_data.get('end_time')
    location = form.cleaned_data.get('location')

    obj.person = request.user
    already = set()
    schedules = Schedule.objects.order_by('start_time')
    for schedule in schedules:
        start = isScheduleInTimePeriod(schedule.start_time, schedule.end_time, obj.start_time)
        end = isScheduleInTimePeriod(schedule.start_time, schedule.end_time, obj.end_time)
        if start or end:
            already.add(schedule)

    occupied = list(already)
    if len(occupied) > 0 and location.room == occupied[0].location.room:
        print('cannot save already have a person there')
        # raise ValidationError("Dates are incorrect")
    else:
        #super().save_model(request, obj, form, change)
        obj.save()


def isScheduleInTimePeriod(startTime, endTime, scheduleTime):
    if startTime < endTime:
        return scheduleTime >= startTime and scheduleTime <= endTime
    else:  # Over midnight
        return scheduleTime >= startTime or scheduleTime <= endTime
