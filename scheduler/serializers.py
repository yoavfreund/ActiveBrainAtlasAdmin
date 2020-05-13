from django.contrib.auth.models import User
from rest_framework import serializers

from scheduler.models import Location, Schedule



class UserSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = User
        fields = ['url', 'username', 'email', 'groups']


class LocationSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = Location
        fields = ['room', 'description']




class ScheduleSerializer(serializers.ModelSerializer):
    location = LocationSerializer(many=False, read_only=True)
    user = UserSerializer(many=False, read_only=True)
    location_id = serializers.PrimaryKeyRelatedField(queryset=Location.objects.all(), write_only=True,
                                                     source='location')
    user_id = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), write_only=True,
                                                     source='user')

    class Meta:
        model = Schedule
        fields = ['start_time', 'end_time', 'location', 'user', 'location_id', 'user_id']

