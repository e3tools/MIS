from django.contrib import admin
from .models import AdministrativeLevel, GeographicalUnit, CVD

# Register your models here.
admin.site.register([
    AdministrativeLevel,
    GeographicalUnit,
    CVD
])
