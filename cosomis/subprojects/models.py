from email.policy import default
from django.db import models
from administrativelevels.models import AdministrativeLevel, CVD


class BaseModel(models.Model):
    created_date = models.DateTimeField(auto_now_add = True, blank=True, null=True)
    updated_date = models.DateTimeField(auto_now = True, blank=True, null=True)

    class Meta:
        abstract = True
    
    def save_and_return_object(self):
        super().save()
        return self


# Create your models here.
class Subproject(BaseModel):
    short_name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    # administrative_level = models.ForeignKey(AdministrativeLevel, null=False, on_delete=models.CASCADE)
    cvds = models.ManyToManyField(CVD, default=[], blank=True, related_name='cvds_subprojects')
    # created_date = models.DateTimeField(auto_now_add=True)
    # updated_date = models.DateTimeField(auto_now=True)
    target_female_beneficiaries = models.IntegerField()
    target_male_beneficiaries = models.IntegerField()
    target_youth_beneficiaries = models.IntegerField()
    component = models.ForeignKey('Component', null=True, on_delete=models.CASCADE)
    priorities = models.ManyToManyField('VillagePriority', default=[], blank=True, related_name='priorities_covered')
    ranking = models.IntegerField(default=0)
    allocation = models.FloatField(null=True, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True)

    def __str__(self):
        return self.short_name


class VulnerableGroup(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    administrative_level = models.ForeignKey(AdministrativeLevel, null=False, on_delete=models.CASCADE)

    def __str__(self):
        return self.name



class VillageObstacle(BaseModel):
    administrative_level = models.ForeignKey(AdministrativeLevel, on_delete=models.CASCADE)
    focus_group = models.CharField(max_length=255)
    description = models.TextField()
    meeting = models.ForeignKey('VillageMeeting', on_delete=models.CASCADE)
    ranking = models.IntegerField(default=0)

    def __str__(self):
        return self.description


class VillageGoal(BaseModel):
    administrative_level = models.ForeignKey(AdministrativeLevel, on_delete=models.CASCADE)
    focus_group = models.CharField(max_length=255)
    description = models.TextField()
    meeting = models.ForeignKey('VillageMeeting', on_delete=models.CASCADE)
    ranking = models.IntegerField(default=0)

    def __str__(self):
        return self.description


class VillagePriority(BaseModel):
    administrative_level = models.ForeignKey(AdministrativeLevel, on_delete=models.CASCADE)
    component = models.ForeignKey('Component', null=True, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    proposed_men = models.IntegerField(null=True, blank=True)
    proposed_women = models.IntegerField(null=True, blank=True)
    estimated_cost = models.FloatField(null=True, blank=True)
    estimated_beneficiaries = models.IntegerField(null=True, blank=True)
    climate_changing_contribution = models.TextField(null=True, blank=True)
    eligibility = models.BooleanField(blank=True, null=True)
    sector = models.CharField(max_length=255, null=True, blank=True)
    parent = models.ForeignKey('VillagePriority', null=True, blank=True, on_delete=models.CASCADE)
    meeting = models.ForeignKey('VillageMeeting', on_delete=models.CASCADE)
    ranking = models.IntegerField(default=0)

    def __str__(self):
        return self.name


class TypeMain(BaseModel):
    village_priority = models.ForeignKey(VillagePriority, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    value = models.CharField(max_length=255)

    def __str__(self):
        return "{} : {}".format(self.name, self.value)


class VillageMeeting(BaseModel):
    description = models.TextField()
    date_conducted = models.DateTimeField()
    administrative_level = models.ForeignKey(AdministrativeLevel, on_delete=models.CASCADE)
    type = models.CharField(max_length=255)
    ranking = models.IntegerField(default=0)

    def __str__(self):
        return self.description


class Component(BaseModel):
    name = models.CharField(max_length=255)
    parent = models.ForeignKey('Component', null=True, blank=True, on_delete=models.CASCADE)
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name
