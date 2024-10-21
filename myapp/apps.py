from django.apps import AppConfig
from django.conf import settings
from django.utils import timezone
import datetime

class MyappConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "myapp"

    def ready(self):
        # Import tasks to avoid circular imports
        from myapp.tasks import check_queued_deployments, send_failure_alert, send_approval_alert
        from background_task.models import Task
        
        # Dynamically adjust repeat choices for background_task's Task model
        try:    
            # Convert choices to a list, add new choice, and reassign as tuple
            choices = list(Task._meta.get_field('repeat').choices)
            choices.append((10, 'Every 10 Seconds'))
            choices.append((60, 'Every Minute'))
            Task._meta.get_field('repeat').choices = tuple(choices)
        except ImportError:
            # If background_task is not available, handle the error or log as needed
            print("Background Task model not found. Skipping repeat choice customization.")

        # add tasks if they aren't there yet    
        if getattr(settings, 'SCHEDULER_AUTOSTART', False):
            
            now = timezone.now()
            next_min = now.replace(second=0, microsecond=0) + datetime.timedelta(minutes=1)
            next_run = now.replace(hour=6, minute=0, second=0, microsecond=0)
            if now.hour >= 6:
                # If the current time is already past 6 a.m. today, schedule for tomorrow at 6 a.m.
                next_run += datetime.timedelta(days=1)
            
            if not Task.objects.filter(task_name='myapp.tasks.check_queued_deployments').exists():
                check_queued_deployments(repeat=60, run_at=next_min)
                
            if not Task.objects.filter(task_name='myapp.tasks.send_approval_alert').exists():
                send_approval_alert(repeat=60, run_at=next_min)
        
            if not Task.objects.filter(task_name='myapp.tasks.send_failure_alert').exists():
                send_failure_alert(repeat=60*60*24, run_at=next_run)
            
            # if not Task.objects.filter(task_name='myapp.tasks.check_destroying_deployments').exists():
            #     check_destroying_deployments()
        
            
            
            #Delete any pre-existing tasks with the same names
            # Task.objects.filter(task_name='myapp.tasks.check_queued_deployments').delete()
            # Task.objects.filter(task_name='myapp.tasks.send_failure_alert').delete()
            # Task.objects.filter(task_name='myapp.tasks.send_approval_alert').delete()

            # Re-add the tasks
            # check_queued_deployments(repeat=10)
            # send_failure_alert(repeat=60*60*24)
            # send_approval_alert(repeat=10)

