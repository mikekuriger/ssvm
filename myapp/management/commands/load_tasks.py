# myapp/management/commands/load_tasks.py
from django.core.management.base import BaseCommand
from myapp.tasks import check_queued_deployments, send_failure_alert
from background_task.models import Task

class Command(BaseCommand):
    help = 'Load and schedule tasks into the database'

    def handle(self, *args, **kwargs):
        # Clear existing tasks to prevent duplicates
        Task.objects.all().delete()
        
        Task.objects.filter(task_name='myapp.tasks.check_queued_deployments').delete()
        Task.objects.filter(task_name='myapp.tasks.send_failure_alert').delete()
        Task.objects.filter(task_name='myapp.tasks.send_approval_alert').delete()

        # Register and schedule tasks
        check_queued_deployments(repeat=60)  # 60 seconds
        send_approval_alert(repeat=60)
        send_failure_alert(repeat=86400)       # Daily
        
        
        self.stdout.write(self.style.SUCCESS('Successfully loaded and scheduled tasks.'))