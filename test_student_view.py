import sys
import os
import django
import traceback
from datetime import date, datetime

sys.path.append('services/classhub')
sys.path.append('services/common')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
os.environ["DJANGO_SECRET_KEY"] = "test"
os.environ["DJANGO_DEBUG"] = "1"
django.setup()

from django.test import RequestFactory
from django.contrib.auth.models import AnonymousUser
from hub.views.student import student_home
from hub.models import Class, StudentIdentity

factory = RequestFactory()
request = factory.get('/student')
request.user = AnonymousUser()

# Create a dummy class and student
try:
    cls = Class.objects.first()
    student = StudentIdentity.objects.first()
    request.student = student
    request.classroom = cls

    response = student_home(request)
    print("Response status:", response.status_code)
    if response.status_code == 500:
        print(response.content)
except Exception as e:
    traceback.print_exc()
