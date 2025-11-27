from rest_framework import serializers
from .models import ProjectActivityLog


class ActivityLogSerializer(serializers.ModelSerializer):
    actor_name = serializers.ReadOnlyField(source='actor.get_full_name')

    class Meta:
        model = ProjectActivityLog
        fields = ['id', 'actor_name', 'action_type', 'target', 'timestamp']