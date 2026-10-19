from django.contrib import admin
from .models import Profile, Complaint, Message, History, Notification, Department, Category, Attachment
for model in [Profile,Complaint,Message,History,Notification,Department,Category,Attachment]: admin.site.register(model)
