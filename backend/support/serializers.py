from rest_framework import serializers
from .models import Complaint, Message, History, Notification, Attachment
class MessageSerializer(serializers.ModelSerializer):
    name=serializers.CharField(source='user.username',read_only=True)
    class Meta:
        model=Message
        fields=['id','name','body','created']
class HistorySerializer(serializers.ModelSerializer):
    class Meta:
        model=History
        fields=['body','created']
class AttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model=Attachment
        fields=['id','name','created']

class ComplaintSerializer(serializers.ModelSerializer):
    attachments=AttachmentSerializer(many=True,read_only=True)
    can_edit=serializers.SerializerMethodField()
    can_delete=serializers.SerializerMethodField()
    def get_can_edit(self,obj):
        u=self.context["request"].user
        return obj.user_id==u.id and obj.status=="Submitted" and obj.assigned_to_id is None and not obj.is_archived
    def get_can_delete(self,obj):
        return self.get_can_edit(obj)
    messages=MessageSerializer(many=True,read_only=True)
    history=HistorySerializer(many=True,read_only=True)
    username=serializers.CharField(source='user.username',read_only=True)
    assigned_name=serializers.CharField(source='assigned_to.username',read_only=True,default='')
    class Meta:
        model=Complaint
        fields=['attachments','can_edit','can_delete','id','title','description','category','priority','department','sentiment','confidence','status','assigned_to','assigned_name','username','created','updated','messages','history']
        read_only_fields=['category','priority','department','sentiment','confidence','status','assigned_to']
    def validate_description(self,v):
        if len(v.strip())<10: raise serializers.ValidationError('Please enter at least 10 characters.')
        return v
class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model=Notification
        fields=['id','complaint','body','created']
