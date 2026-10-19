from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from support import views
router=DefaultRouter(); router.register('complaints',views.ComplaintViewSet,basename='complaints')
urlpatterns=[path('admin/',admin.site.urls),path('api/',include(router.urls))]+[path('api/'+name+'/',fn) for name,fn in [('register',views.register),('login',views.login),('logout',views.logout),('me',views.me),('metadata',views.metadata),('notifications',views.notifications),('chat',views.chat),('users',views.users),('export',views.export),('configuration',views.configuration),('evaluation',views.evaluation)]]
