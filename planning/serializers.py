from rest_framework import serializers
from .models import Sprint

class SprintSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sprint
        fields = '__all__'

class SprintSerializer(serializers.ModelSerializer):
    # Додаємо кастомні поля, які будуть обчислюватися "на льоту"
    tasks_total = serializers.SerializerMethodField()
    tasks_completed = serializers.SerializerMethodField()

    class Meta:
        model = Sprint
        # Явно вказуємо всі поля, щоб додати наші нові (або можна залишити '__all__',
        # DRF автоматично підтягне MethodField, але так надійніше і чистіше)
        fields = [
            'id', 'project', 'name', 'goal',
            'start_date', 'end_date', 'status', 'actual_end_date',
            'tasks_total', 'tasks_completed',
            'created_at'
        ]
        # Захищаємо поля від ручного редагування при створенні/оновленні
        read_only_fields = ['status', 'actual_end_date', 'created_at', 'tasks_total', 'tasks_completed']

    def get_tasks_total(self, obj):
        """Рахує загальну кількість задач у цьому спринті"""
        return obj.tasks.count()

    def get_tasks_completed(self, obj):
        """Рахує тільки задачі зі статусом 'done'"""
        return obj.tasks.filter(status='done').count()

class SprintCompleteSerializer(serializers.Serializer):
    """
    Серіалізатор для екшену 'Завершити спринт'.
    Якщо передано move_to_sprint_id, невиконані задачі перейдуть туди.
    Якщо не передано — задачі повернуться в Backlog (sprint=None).
    """
    move_to_sprint_id = serializers.IntegerField(required=False, allow_null=True)

    def validate_move_to_sprint_id(self, value):
        # Якщо фронтенд передав якийсь ID, перевіряємо, чи існує такий спринт
        if value is not None:
            if not Sprint.objects.filter(id=value).exists():
                raise serializers.ValidationError("Спринт для перенесення задач з таким ID не знайдено.")
        return value