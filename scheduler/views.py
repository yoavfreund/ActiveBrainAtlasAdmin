from django.contrib.auth.models import User, Group
from rest_framework import viewsets
from rest_framework import permissions

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from scheduler.serializers import UserSerializer, LocationSerializer, ScheduleSerializer
from scheduler.models import Location, Schedule

class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]


class LocationViewSet(viewsets.ModelViewSet):
    queryset = Location.objects.all()
    serializer_class = LocationSerializer
    permission_classes = [permissions.IsAuthenticated]

class ScheduleViewSet(viewsets.ModelViewSet):
    queryset = Schedule.objects.all()
    serializer_class = ScheduleSerializer
    permission_classes = [permissions.IsAuthenticated]


@login_required
def home(request):
    return render(request, 'scheduler/home.html')
