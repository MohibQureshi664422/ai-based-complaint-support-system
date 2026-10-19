import csv, io
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, FileResponse
from django.shortcuts import get_object_or_404
from pathlib import Path 
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.exceptions import ValidationError
from .serializers import AttachmentSerializer
from rest_framework import viewsets, serializers
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from .models import Profile, Complaint, Message, History, Notification, STATUSES, Department, Category, Attachment
from .serializers import ComplaintSerializer, MessageSerializer, NotificationSerializer
from .ml import analyze, answer, DEPARTMENTS

def role(u): return 'admin' if u.is_superuser else Profile.objects.get_or_create(user=u)[0].role

def identity(u):
    p=Profile.objects.get_or_create(user=u)[0]
    return {'id':u.id,'username':u.username,'email':u.email,'role':role(u),'department':p.department}

class Credentials(serializers.Serializer):
    username=serializers.CharField(max_length=150)
    password=serializers.CharField(max_length=200,trim_whitespace=False)
    email=serializers.EmailField(required=False)

@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    s=Credentials(data=request.data); s.is_valid(raise_exception=True); d=s.validated_data
    if User.objects.filter(username=d['username']).exists(): return Response({'detail':'Username already exists'},status=400)
    try: validate_password(d['password'],User(username=d['username']))
    except DjangoValidationError as e: return Response({'detail':list(e.messages)},status=400)
    with transaction.atomic():
        u=User.objects.create_user(d['username'],d.get('email',''),d['password']); Profile.objects.create(user=u)
        token=Token.objects.create(user=u)
    return Response({'token':token.key,'user':identity(u)},status=201)

@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    s=Credentials(data=request.data); s.is_valid(raise_exception=True)
    u=authenticate(username=s.validated_data['username'],password=s.validated_data['password'])
    if not u: return Response({'detail':'Invalid username or password'},status=401)
    token,_=Token.objects.get_or_create(user=u)
    return Response({'token':token.key,'user':identity(u)})
@api_view(['POST'])
def logout(request):
    Token.objects.filter(user=request.user).delete(); return Response({'detail':'Logged out'})
@api_view(['GET'])
def me(request): return Response(identity(request.user))
@api_view(['GET'])
def metadata(request): return Response({'categories':list(Category.objects.filter(active=True,department__active=True).values_list('name',flat=True)),'departments':list(Department.objects.filter(active=True).values_list('name',flat=True)),'statuses':STATUSES,'priorities':['Low','Medium','High']})

def routed_analysis(text):
    a=list(analyze(text))
    category=Category.objects.filter(name=a[0],active=True,department__active=True).select_related('department').first()
    if not category: category=Category.objects.filter(name='General Inquiry',active=True,department__active=True).select_related('department').first()
    if not category: raise ValidationError('Enable General Inquiry and its department before accepting complaints.')
    a[0]=category.name; a[2]=category.department.name
    return a

def event(c,body):
    History.objects.create(complaint=c,body=body)
    Notification.objects.create(user=c.user,complaint=c,body=body)

class ComplaintViewSet(viewsets.ModelViewSet):
    serializer_class=ComplaintSerializer
    http_method_names=['get','post','patch','delete','head','options']
    def get_queryset(self):
        qs=Complaint.objects.filter(is_archived=False).select_related('user','assigned_to').prefetch_related('messages__user','history').order_by('-id')
        r=role(self.request.user)
        if r=='user': qs=qs.filter(user=self.request.user)
        elif r=='staff':
            department=self.request.user.profile.department
            qs=qs.filter(Q(assigned_to=self.request.user)|Q(assigned_to__isnull=True,department=department))
        search=self.request.query_params.get('search',''); status=self.request.query_params.get('status','')
        if search: qs=qs.filter(Q(title__icontains=search)|Q(description__icontains=search))
        if status: qs=qs.filter(status=status)
        return qs
    @transaction.atomic
    def perform_create(self,serializer):
        a=routed_analysis(serializer.validated_data['title']+' '+serializer.validated_data['description'])
        c=serializer.save(user=self.request.user,category=a[0],priority=a[1],department=a[2],sentiment=a[3],confidence=a[4])
        event(c,'Submitted and routed to '+c.department)
    def editable(self,c,user):
        return c.user_id==user.id and c.status=='Submitted' and c.assigned_to_id is None and not c.is_archived
    @transaction.atomic
    def partial_update(self,request,*args,**kwargs):
        c=self.get_object()
        if not self.editable(c,request.user):
            return Response({'detail':'Only the owner can edit a Submitted, unassigned complaint.'},status=403)
        if set(request.data)-{'title','description'}:
            return Response({'detail':'Only title and description can be edited.'},status=400)
        serializer=self.get_serializer(c,data=request.data,partial=True)
        serializer.is_valid(raise_exception=True)
        title=serializer.validated_data.get('title',c.title)
        description=serializer.validated_data.get('description',c.description)
        a=routed_analysis(title+' '+description)
        c=serializer.save(category=a[0],priority=a[1],department=a[2],sentiment=a[3],confidence=a[4])
        event(c,'Complaint edited by owner; analysis refreshed and routed to '+c.department)
        return Response(self.get_serializer(Complaint.objects.get(pk=c.pk)).data)
    @transaction.atomic
    def destroy(self,request,*args,**kwargs):
        c=self.get_object()
        if not self.editable(c,request.user):
            return Response({'detail':'Only the owner can delete a Submitted, unassigned complaint.'},status=403)
        c.is_archived=True; c.save(update_fields=['is_archived','updated'])
        History.objects.create(complaint=c,body='Archived by owner (soft delete)',created=c.updated)
        return Response(status=204)
    @action(detail=True,methods=['post'],parser_classes=[MultiPartParser,FormParser])
    def upload(self,request,pk=None):
        c=self.get_object()
        if not self.editable(c,request.user): return Response({'detail':'Owner uploads are allowed only while Submitted and unassigned.'},status=403)
        f=request.FILES.get('file')
        if not f: return Response({'detail':'Select a file.'},status=400)
        if f.size>5*1024*1024: return Response({'detail':'Maximum size is 5 MB.'},status=400)
        suffix=Path(f.name).suffix.lower(); header=f.read(12); f.seek(0)
        signatures={'.pdf':header.startswith(b'%PDF-'),'.png':header.startswith(b'\x89PNG\r\n\x1a\n'),'.jpg':header.startswith(b'\xff\xd8\xff'),'.jpeg':header.startswith(b'\xff\xd8\xff')}
        if not signatures.get(suffix,False): return Response({'detail':'Only valid PDF, PNG or JPEG files are accepted.'},status=400)
        if c.attachments.count()>=3: return Response({'detail':'Maximum 3 attachments per complaint.'},status=400)
        a=Attachment.objects.create(complaint=c,file=f,name=Path(f.name).name[:200])
        event(c,'Supporting file uploaded: '+a.name)
        return Response(AttachmentSerializer(a).data,status=201)
    @action(detail=True,methods=['get'],url_path=r'attachments/(?P<attachment_id>[0-9]+)')
    def download(self,request,pk=None,attachment_id=None):
        c=self.get_object(); a=get_object_or_404(Attachment,pk=attachment_id,complaint=c)
        return FileResponse(a.file.open('rb'),as_attachment=True,filename=a.name)
    @action(detail=True,methods=['post'])
    @transaction.atomic
    def reply(self,request,pk=None):
        c=self.get_object()
        s=MessageSerializer(data=request.data); s.is_valid(raise_exception=True)
        m=s.save(complaint=c,user=request.user)
        event(c,'New response from '+request.user.username)
        if request.user==c.user and c.assigned_to: Notification.objects.create(user=c.assigned_to,complaint=c,body='User replied to #'+str(c.id))
        return Response(MessageSerializer(m).data,status=201)
    @action(detail=True,methods=['post'])
    @transaction.atomic
    def review(self,request,pk=None):
        c=self.get_object()
        if role(request.user) not in ['staff','admin']: return Response({'detail':'Staff only'},status=403)
        class Review(serializers.Serializer):
            status=serializers.ChoiceField(choices=STATUSES)
            category=serializers.ChoiceField(choices=list(Category.objects.filter(active=True,department__active=True).values_list('name',flat=True)))
            priority=serializers.ChoiceField(choices=['Low','Medium','High'])
            assigned_to=serializers.IntegerField(allow_null=True,required=False)
        s=Review(data=request.data); s.is_valid(raise_exception=True); d=s.validated_data
        department=Category.objects.get(name=d['category']).department.name
        assigned=c.assigned_to_id
        if role(request.user)=='admin': assigned=d.get('assigned_to',assigned)
        elif 'assigned_to' in d: return Response({'detail':'Only admin can assign staff'},status=403)
        if assigned and not User.objects.filter(id=assigned,is_active=True,profile__role='staff',profile__department=department).exists():
            return Response({'detail':'Select active staff in the matching department or unassign first'},status=400)
        c.status=d['status']; c.category=d['category']; c.priority=d['priority']; c.department=department; c.assigned_to_id=assigned; c.save()
        event(c,'Reviewed by '+request.user.username+': '+c.status+' / '+c.category+' / '+c.priority)
        if c.assigned_to: Notification.objects.create(user=c.assigned_to,complaint=c,body='Complaint #'+str(c.id)+' assigned or updated')
        return Response(self.get_serializer(c).data)

@api_view(['GET'])
def notifications(request): return Response(NotificationSerializer(Notification.objects.filter(user=request.user,complaint__is_archived=False).order_by('-id'),many=True).data)
@api_view(['POST'])
def chat(request):
    class Question(serializers.Serializer): question=serializers.CharField(max_length=1000)
    s=Question(data=request.data); s.is_valid(raise_exception=True)
    return Response({'answer':answer(s.validated_data['question'])})
@api_view(['GET','POST'])
def users(request):
    if role(request.user)!='admin': return Response({'detail':'Admin only'},status=403)
    if request.method=='POST':
        class Edit(serializers.Serializer):
            id=serializers.IntegerField()
            role=serializers.ChoiceField(choices=['user','staff','admin'])
            department=serializers.ChoiceField(choices=['',*Department.objects.filter(active=True).values_list('name',flat=True)])
            active=serializers.BooleanField()
        s=Edit(data=request.data); s.is_valid(raise_exception=True); d=s.validated_data
        if d['id']==request.user.id: return Response({'detail':'Cannot edit your own account here'},status=400)
        if d['role']=='staff' and not d['department']: return Response({'detail':'Staff need a department'},status=400)
        try: u=User.objects.get(id=d['id'],is_superuser=False)
        except User.DoesNotExist: return Response({'detail':'User not found or protected'},status=404)
        with transaction.atomic():
            p=Profile.objects.get_or_create(user=u)[0]; p.role=d['role']; p.department=d['department']; p.save()
            u.is_active=d['active']; u.save()
            if not u.is_active: Token.objects.filter(user=u).delete()
    return Response([{**identity(u),'active':u.is_active} for u in User.objects.all().order_by('id')])
@api_view(['GET'])
def export(request):
    if role(request.user)!='admin': return Response({'detail':'Admin only'},status=403)
    out=io.StringIO(); w=csv.writer(out); w.writerow(['ID','Title','Category','Priority','Department','Status'])
    for c in Complaint.objects.filter(is_archived=False):
        values=[c.id,c.title,c.category,c.priority,c.department,c.status]
        w.writerow(["'"+v if isinstance(v,str) and v.startswith(('=','+','-','@')) else v for v in values])
    response=HttpResponse(out.getvalue(),content_type='text/csv'); response['Content-Disposition']='attachment; filename="complaints.csv"'; return response

@api_view(['GET','POST'])
def configuration(request):
    if role(request.user)!='admin': return Response({'detail':'Admin only'},status=403)
    if request.method=='POST':
        class Setting(serializers.Serializer):
            kind=serializers.ChoiceField(choices=['department','category'])
            name=serializers.CharField(max_length=50)
            active=serializers.BooleanField(default=True)
            department=serializers.IntegerField(required=False)
        s=Setting(data=request.data); s.is_valid(raise_exception=True); d=s.validated_data
        if d['kind']=='department' and not d['active'] and Category.objects.filter(name='General Inquiry',department__name=d['name']).exists(): return Response({'detail':'The General Inquiry department must remain active.'},status=400)
        if d['kind']=='department': Department.objects.update_or_create(name=d['name'],defaults={'active':d['active']})
        else:
            dep=get_object_or_404(Department,id=d.get('department'))
            if d['name']=='General Inquiry' and (not d['active'] or not dep.active): return Response({'detail':'General Inquiry must remain active in an active department.'},status=400)
            Category.objects.update_or_create(name=d['name'],defaults={'active':d['active'],'department':dep})
    return Response({'departments':list(Department.objects.values()),'categories':list(Category.objects.values())})

@api_view(['GET'])
def evaluation(request):
    if role(request.user)!='admin': return Response({'detail':'Admin only'},status=403)
    import json
    from django.conf import settings
    path=settings.BASE_DIR/'evaluation_report.json'
    if not path.exists(): return Response({'detail':'Run python evaluate.py on the backend to generate metrics.'},status=404)
    return Response(json.loads(path.read_text()))
