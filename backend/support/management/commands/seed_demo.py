from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from support.models import Profile
class Command(BaseCommand):
    help='Create local demonstration accounts (does not reset existing passwords)'
    def handle(self,*args,**kwargs):
        for name,role,department in [('admin','admin',''),('staff','staff','IT Support'),('customer','user','')]:
            u,created=User.objects.get_or_create(username=name,defaults={'email':name+'@demo.local'})
            if created: u.set_password('DemoPass123!'); u.save()
            Profile.objects.get_or_create(user=u,defaults={'role':role,'department':department})
        self.stdout.write('Demo: admin / staff / customer, password DemoPass123!')
