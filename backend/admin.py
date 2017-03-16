from django.contrib import admin
from .models import TaskModel, SessionToken

# Register your models here.
admin.site.register(TaskModel)
admin.site.register(SessionToken)
