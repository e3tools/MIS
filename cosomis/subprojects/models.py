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
    cvd = models.ForeignKey(CVD, null=True, blank=True, on_delete=models.CASCADE)
    location_subproject_realized = models.ForeignKey(AdministrativeLevel, null=True, blank=True, on_delete=models.CASCADE, related_name='location_subproject_realized')
    canton = models.ForeignKey(AdministrativeLevel, null=True, blank=True, on_delete=models.CASCADE) #canton subprojects (rural track)
    link_to_subproject = models.ForeignKey('Subproject', null=True, blank=True, on_delete=models.CASCADE) #To link the subprojects that the cantons or CVD link to make
    list_of_villages_crossed_by_the_track_or_electrification = models.ManyToManyField(AdministrativeLevel, default=[], blank=True, related_name="cantonal_subprojects")

    number = models.IntegerField(null=True, blank=True)
    intervention_unit = models.IntegerField(null=True, blank=True)
    facilitator_name = models.CharField(max_length=255, null=True, blank=True)
    wave = models.CharField(max_length=2, null=True, blank=True)
    lot = models.CharField(max_length=2, null=True, blank=True)
    subproject_sector = models.CharField(max_length=100)
    type_of_subproject = models.CharField(max_length=100)
    full_title_of_approved_subproject = models.TextField()
    works_type = models.CharField(max_length=100, null=True, blank=True)
    estimated_cost = models.FloatField(null=True, blank=True)
    level_of_achievement_donation_certificate = models.CharField(max_length=50, null=True, blank=True)
    approval_date_cora = models.DateField(null=True, blank=True)
    date_of_signature_of_contract_for_construction_supervisors = models.DateField(null=True, blank=True)
    amount_of_the_contract_for_construction_supervisors = models.FloatField(null=True, blank=True)
    date_signature_contract_controllers_in_SES = models.DateField(null=True, blank=True)
    amount_of_the_controllers_contract_in_SES = models.FloatField(null=True, blank=True)
    convention = models.CharField(max_length=255, null=True, blank=True)
    contract_number_of_work_companies = models.CharField(max_length=15, null=True, blank=True)
    name_of_the_awarded_company_works_companies = models.CharField(max_length=255, null=True, blank=True)
    date_signature_contract_work_companies = models.DateField(null=True, blank=True)
    contract_amount_work_companies = models.FloatField(null=True, blank=True)
    name_of_company_awarded_efme = models.CharField(max_length=255, null=True, blank=True)
    date_signature_contract_efme = models.DateField(null=True, blank=True)
    contract_companies_amount_for_efme = models.DateField(null=True, blank=True)
    date_signature_contract_facilitator = models.DateField(null=True, blank=True)
    amount_of_the_facilitator_contract = models.FloatField(null=True, blank=True)
    launch_date_of_the_construction_site_in_the_village = models.DateField(null=True, blank=True)
    current_level_of_physical_realization_of_the_work = models.CharField(max_length=100, null=True, blank=True)
    length_of_the_track = models.FloatField(null=True, blank=True)
    depth_of_drilling = models.FloatField(null=True, blank=True)
    drilling_flow_rate = models.FloatField(null=True, blank=True)
    current_status_of_the_site = models.CharField(max_length=100, null=True, blank=True)
    expected_duration_of_the_work = models.FloatField(null=True, blank=True)
    expected_end_date_of_the_contract = models.DateField(null=True, blank=True)
    total_contract_amount_paid = models.FloatField(null=True, blank=True)
    amount_of_the_care_and_maintenance_fund_expected_to_be_mobilized = models.FloatField(null=True, blank=True)
    care_and_maintenance_amount_on_village_account = models.FloatField(null=True, blank=True)
    existence_of_maintenance_and_upkeep_plan_developed_by_community = models.BooleanField(default=False)
    date_of_technical_acceptance_of_work_contracts = models.DateField(null=True, blank=True)
    technical_acceptance_date_for_efme_contracts = models.DateField(null=True, blank=True)
    date_of_provisional_acceptance_of_work_contracts = models.DateField(null=True, blank=True)
    provisional_acceptance_date_for_efme_contracts = models.DateField(null=True, blank=True)
    official_handover_date_of_the_microproject_to_the_community = models.DateField(null=True, blank=True)
    official_handover_date_of_the_microproject_to_the_sector = models.DateField(null=True, blank=True)
    comments = models.TextField(null=True, blank=True)
    
    target_female_beneficiaries = models.IntegerField(null=True, blank=True)
    target_male_beneficiaries = models.IntegerField(null=True, blank=True)
    target_youth_beneficiaries = models.IntegerField(null=True, blank=True)

    population = models.IntegerField(null=True, blank=True)
    direct_beneficiaries_men = models.IntegerField(null=True, blank=True)
    direct_beneficiaries_women = models.IntegerField(null=True, blank=True)
    indirect_beneficiaries_men = models.IntegerField(null=True, blank=True)
    indirect_beneficiaries_women = models.IntegerField(null=True, blank=True)

    component = models.ForeignKey('Component', null=True, on_delete=models.CASCADE)
    priorities = models.ManyToManyField('VillagePriority', default=[], blank=True, related_name='priorities_covered')
    ranking = models.IntegerField(null=True, blank=True)

    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True)


    def get_cantons_names(self):
        if self.location_subproject_realized:
            return self.location_subproject_realized.parent.name
        elif self.canton: 
            cantons = self.canton.name
            subprojects_link_objects = self.subproject_set.get_queryset()
            if subprojects_link_objects:
                cantons += "/"
            for i in range(len(subprojects_link_objects)):
                cantons += subprojects_link_objects[i].canton.name
                if i+1 < len(subprojects_link_objects):
                    cantons += "/"
            return cantons
        return None

    def get_canton(self):
        if self.location_subproject_realized:
            return self.location_subproject_realized.parent
        elif self.canton:
            return self.canton

        return None
    
    def get_village(self):
        if self.location_subproject_realized:
            return self.location_subproject_realized
        elif self.canton:
            a = AdministrativeLevel()
            a.name = "CCD"
            return a

        return None

    def get_location(self):
        cantons_names = self.get_cantons_names()
        canton = self.get_canton()
        location = ""
        if canton:
            location = canton.parent.parent.parent.name + ", " + canton.parent.parent.name + ", " + canton.parent.name
        if cantons_names:
            location += ", " + cantons_names
        if self.location_subproject_realized:
            location += ", " + self.location_subproject_realized.name
        return location

    def get_location_commune(self):
        cantons_names = self.get_cantons_names()
        canton = self.get_canton()
        location = ""
        if canton:
            location = canton.parent.parent.parent.name + ", " + canton.parent.parent.name + ", " + canton.parent.name
        
        return location


    def get_estimated_cost(self):
        estimated_cost = self.estimated_cost
        for o in self.subproject_set.get_queryset():
            estimated_cost += o.estimated_cost
        return estimated_cost

    def get_estimated_cost_str(self):
        estimated_cost_str = ""
        estimated_cost_str += str(self.estimated_cost)
        subproject_link_objects = self.subproject_set.get_queryset()
        if subproject_link_objects:
            for o in self.subproject_set.get_queryset():
                estimated_cost_str += " + " + str(o.estimated_cost)
            return str(self.get_estimated_cost()) + f' ({estimated_cost_str})'
        
        return estimated_cost_str


    def get_all_images(self, order=False):
        if order:
            return sorted(self.subprojectimage_set.get_queryset(), key=lambda o: o.order)
        return self.subprojectimage_set.get_queryset()
    
    def get_principal_image(self):
        for img in self.get_all_images():
            if img.principal:
                return img
        return None

    def __str__(self):
        return self.full_title_of_approved_subproject


class VulnerableGroup(BaseModel):
    name = models.CharField(max_length=255)
    description = models.TextField()
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


class SubprojectImage(BaseModel):
    subproject = models.ForeignKey(Subproject, null=True, blank=True, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    url = models.CharField(max_length=255)
    order = models.IntegerField(default=0)
    principal = models.BooleanField(default=False)
    date_taken = models.DateField()
