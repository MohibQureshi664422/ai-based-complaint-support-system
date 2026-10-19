from django.db import models
from django.contrib.auth.models import User
from .ml import DEPARTMENTS
STATUSES=['Submitted','Under Review','Assigned','In Progress','Resolved','Closed']
class Profile(models.Model):
    user=models.OneToOneField(User,on_delete=models.CASCADE,related_name='profile')
    role=models.CharField(max_length=10,choices=[(r,r) for r in ['user','staff','admin']],default='user')
    department=models.CharField(max_length=50,blank=True)
class Complaint(models.Model):
    user=models.ForeignKey(User,on_delete=models.CASCADE,related_name='complaints')
    is_archived=models.BooleanField(default=False)
    title=models.CharField(max_length=150)
    description=models.TextField(max_length=10000)
    category=models.CharField(max_length=50)
    priority=models.CharField(max_length=10,choices=[(p,p) for p in ['Low','Medium','High']])
    department=models.CharField(max_length=50)
    sentiment=models.CharField(max_length=20)
    confidence=models.FloatField()
    status=models.CharField(max_length=20,choices=[(s,s) for s in STATUSES],default='Submitted')
    assigned_to=models.ForeignKey(User,on_delete=models.SET_NULL,null=True,blank=True,related_name='assigned_complaints')
    created=models.DateTimeField(auto_now_add=True)
    updated=models.DateTimeField(auto_now=True)
class Message(models.Model):
    complaint=models.ForeignKey(Complaint,on_delete=models.CASCADE,related_name='messages')
    user=models.ForeignKey(User,on_delete=models.CASCADE)
    body=models.TextField(max_length=5000)
    created=models.DateTimeField(auto_now_add=True)
class History(models.Model):
    complaint=models.ForeignKey(Complaint,on_delete=models.CASCADE,related_name='history')
    body=models.TextField()
    created=models.DateTimeField(auto_now_add=True)
class Notification(models.Model):
    user=models.ForeignKey(User,on_delete=models.CASCADE)
    complaint=models.ForeignKey(Complaint,on_delete=models.CASCADE)
    body=models.TextField()
    created=models.DateTimeField(auto_now_add=True)

class Department(models.Model):
    name=models.CharField(max_length=50,unique=True)
    active=models.BooleanField(default=True)
class Category(models.Model):
    name=models.CharField(max_length=50,unique=True)
    department=models.ForeignKey(Department,on_delete=models.PROTECT)
    active=models.BooleanField(default=True)
class Attachment(models.Model):
    complaint=models.ForeignKey(Complaint,on_delete=models.CASCADE,related_name='attachments')
    file=models.FileField(upload_to='private_attachments/%Y/%m/')
    name=models.CharField(max_length=200)
    created=models.DateTimeField(auto_now_add=True)
