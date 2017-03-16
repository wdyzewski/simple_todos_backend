from django.db import models
from django.contrib.auth.models import User
import uuid

class TaskModel(models.Model):
    text = models.CharField(max_length=200)
    created_at = models.DateTimeField()
    owner = models.ForeignKey(User)
    checked = models.BooleanField()
    private = models.BooleanField()

    def __str__(self):
        return 'Task(%s, %s)' % (self.owner.username, self.text[:50])

class SessionToken(models.Model):
    user = models.ForeignKey(User)
    token = models.CharField(max_length=36)

    @classmethod
    def create(cls, user):
        st = cls(user=user)
        st.token = uuid.uuid4()
        return st

    def __str__(self):
        return 'Session(user=%s, token=%s)' % (self.user.username, self.token)
