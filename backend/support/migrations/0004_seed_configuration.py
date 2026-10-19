from django.db import migrations
DEFAULTS={'Technical Issue':'IT Support','Billing/Payment':'Accounts','Account Problem':'Account Support','Service Complaint':'Customer Service','Staff Complaint':'Human Resources','Product Issue':'Product Support','General Inquiry':'Help Desk'}
def seed(apps,schema_editor):
    Department=apps.get_model('support','Department'); Category=apps.get_model('support','Category')
    for name,depname in DEFAULTS.items():
        dep,_=Department.objects.get_or_create(name=depname)
        Category.objects.get_or_create(name=name,defaults={'department':dep})
class Migration(migrations.Migration):
    dependencies=[('support','0003_department_alter_complaint_category_and_more')]
    operations=[migrations.RunPython(seed,migrations.RunPython.noop)]
