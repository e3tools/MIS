from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.contrib import messages
from django.views.generic import DetailView, TemplateView, ListView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from cosomis.constants import OBSTACLES_FOCUS_GROUP, GOALS_FOCUS_GROUP
from cosomis.mixins import PageMixin
from django.http import Http404
import pandas as pd
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils.translation import gettext_lazy as _
from django.core.paginator import Paginator

from no_sql_client import NoSQLClient

from cdd_db.models import Facilitator
from administrativelevels.models import AdministrativeLevel, GeographicalUnit, CVD
from administrativelevels.libraries import convert_file_to_dict, download_file
from administrativelevels import functions as administrativelevels_functions
from subprojects.models import VillageObstacle, VillageGoal, VillagePriority, Component
from .forms import GeographicalUnitForm, CVDForm, AdministrativeLevelForm
from usermanager.permissions import (
    CDDSpecialistPermissionRequiredMixin, SuperAdminPermissionRequiredMixin,
    AdminPermissionRequiredMixin
)


class VillageDetailView(PageMixin, LoginRequiredMixin, DetailView):
    """Class to present the detail page of one village"""

    model = AdministrativeLevel
    template_name = 'village_detail.html'
    context_object_name = 'village'
    title = _('Village')
    active_level1 = 'financial'
    breadcrumb = [
        {
            'url': '',
            'title': title
        },
    ]
    nsc_class = NoSQLClient

    def get_context_data(self, **kwargs):
        context = super(VillageDetailView, self).get_context_data(**kwargs)
        obj = self.get_object()
        if obj.type != "Village":  # Verify if the administrativeLevel type is Village
            raise Http404
        facilitator = Facilitator.objects.get(id=obj.facilitator_id)
        nsc = self.nsc_class()
        database = nsc.get_db(facilitator.no_sql_db_name)

        context.update(self._get_population_data(database))
        context.update(self._get_planning_status(database, obj))
        context.update(self._get_attachments(database, obj))
        context.update(self._get_project_cycle(database, obj))

        context.update({
            'facilitator': facilitator.name if facilitator.name is not None else facilitator.email
        })

        return context

    def _get_population_data(self, db):

        total_participants = self._get_form_value(tag='total_participants', data_base=db)

        total_men = "%s (%s%%)" % (
            self._get_form_value(tag='total_men', data_base=db),
            str(self._format_number_user_friendly(
                self._get_form_value(tag='total_men', data_base=db) * 100 / total_participants))
        )
        total_women = "%s (%s%%)" % (
            self._get_form_value(tag='total_women', data_base=db),
            str(self._format_number_user_friendly(
                self._get_form_value(tag='total_women', data_base=db) * 100 / total_participants))
        )
        younger_35 = "%s (%s%%)" % (
            self._get_form_value(tag='younger_35', data_base=db),
            str(self._format_number_user_friendly(
                self._get_form_value(tag='younger_35', data_base=db) * 100 / total_participants))
        )
        older_65 = "%s (%s%%)" % (
            self._get_form_value(tag='older_65', data_base=db),
            str(self._format_number_user_friendly(
                self._get_form_value(tag='older_65', data_base=db) * 100 / total_participants))
        )
        total_handicapped = "%s (%s%%)" % (
            self._get_form_value(tag='total_handicapped', data_base=db),
            str(self._format_number_user_friendly(
                self._get_form_value(tag='total_handicapped', data_base=db) * 100 / total_participants))
        )
        total_farmers = "%s (%s%%)" % (
            self._get_form_value(tag='total_farmers', data_base=db),
            str(self._format_number_user_friendly(
                self._get_form_value(tag='total_farmers', data_base=db) * 100 / total_participants))
        )
        total_breeders = "%s (%s%%)" % (
            self._get_form_value(tag='total_breeders', data_base=db),
            str(self._format_number_user_friendly(
                self._get_form_value(tag='total_breeders', data_base=db) * 100 / total_participants))
        )
        number_ethnic = "%s (%s%%)" % (
            self._get_form_value(tag='number_ethnic', data_base=db),
            str(self._format_number_user_friendly(
                self._get_form_value(tag='number_ethnic', data_base=db) * 100 / total_participants))
        )
        return {
            'total': total_participants,
            'manages': self._get_form_value(tag='families_nuclei', data_base=db),
            'men_women': "%s / %s" % (total_men, total_women),
            'youth': younger_35,
            'elderly_people': older_65,
            'handicapped': total_handicapped,
            'farmers_breeders': "%s / %s" % (total_farmers, total_breeders),
            'languages': self._get_form_value(tag='languages', data_base=db),
            'ethnic_minorities': number_ethnic,
            'number_ethnic': number_ethnic
        }

    def _get_planning_status(self, db, obj):
        count = 1
        while True:
            try:
                activity_document = db.get_query_result(
                    {
                        "type": "activity",
                        "order": count,
                        "administrative_level_id": obj.no_sql_db_id
                    }
                )[0]
            except Exception as e:
                print(e)
                break
            if len(activity_document) > 0 and activity_document[0]["completed_tasks"] < activity_document[0][
                "total_tasks"]:
                activity = activity_document[0]
                break
            else:
                count += 1

        phase_document = db.get_query_result(
            {
                "_id": activity['phase_id'],
                "type": "phase",
                "administrative_level_id": obj.no_sql_db_id
            }
        )[0]
        task_document = db.get_query_result(
            {
                "type": "task",
                "order": activity['completed_tasks'] + 1,
                "activity_id": activity["_id"]
            }
        )[0]

        return {
            "phase": phase_document[0]['name'],
            "activity": activity['name'],
            "task": task_document[0]['name'],
            "completed": self._format_number_user_friendly(activity['completed_tasks'] * 100 / activity['total_tasks']),
            "priorities_identified": "",
            "submission": ""
        }

    def _get_attachments(self, db, obj):
        attachments = list()
        attachments_documents = db.get_query_result(
            {
                "type": "task",
                "administrative_level_id": obj.no_sql_db_id,
                "$not": {
                    "attachments": []
                }
            }
        )[0]
        for attachments_document in attachments_documents:
            attachments += attachments_document["attachments"]
        return {
            "attachments": [i for i in attachments if "image" in i['type']]
        }

    def _get_project_cycle(self, db, obj):

        phases = db.get_query_result(
            {
                "type": "phase"
            }
        )

        resp = {
            'phases': list()
        }

        for phase in phases:
            activities = db.get_query_result(
                {
                    "type": "activity",
                    "phase_id": phase['_id']
                }
            )
            activities_list = list()
            for activity in activities:
                tasks = db.get_query_result(
                    {
                        "type": "task",
                        "activity_id": activity['_id']
                    }
                )
                tasks_list = list()
                for task in tasks:
                    tasks_list.append({
                        'name': task['name'],
                        'slug': task['_id'],
                        'status': "Completed" if task['completed'] else "Due"
                    })

                activities_list.append({
                    'name': activity['name'],
                    'id': activity['_id'],
                    'tasks': tasks_list
                })

            resp['phases'].append({
                'name': phase['name'],
                'id': phase['_id'],
                'activities': activities_list
            })

        return resp

    def _get_form_value(self, tag, data_base):
        from_document = data_base.get_query_result(
            {
                "mis_tags": {
                    "$elemMatch": {
                        "tag": tag
                    }
                }
            }
        )[0]
        tag_list = from_document[0]['mis_tags']
        form_label = [i['form_input'] for i in tag_list if i['tag'] == tag][0]
        try:
            return from_document[0]['form_response'][0][form_label]
        except KeyError:
            return ''

    def _format_number_user_friendly(self, num: float):
        return int(num) if num.is_integer() else num


class AdministrativeLevelDetailView(PageMixin, LoginRequiredMixin, DetailView):
    """Class to present the detail page of one village"""

    model = AdministrativeLevel
    template_name = 'village_detail.html'
    context_object_name = 'village'
    title = _('Village')
    active_level1 = 'financial'
    breadcrumb = [
        {
            'url': '',
            'title': title
        },
    ]

    def get_context_data(self, **kwargs):
        context = super(AdministrativeLevelDetailView, self).get_context_data(**kwargs)
        _type = self.request.GET.get("type", "Village")
        context['context_object_name'] = _type
        context['title'] = _type
        context['breadcrumb'] = [
            {
                'url': '',
                'title': _type
            },
        ]
        return context


class AdministrativeLevelCreateView(PageMixin, LoginRequiredMixin, AdminPermissionRequiredMixin, CreateView):
    model = AdministrativeLevel
    template_name = 'administrativelevel_create.html'
    context_object_name = 'administrativelevel'
    title = _('Create Administrative level')
    active_level1 = 'administrative_levels'
    breadcrumb = [
        {
            'url': '',
            'title': title
        },
    ]

    def get_parent(self, type: str):
        parent = None
        if type == "Prefecture":
            parent = "Region"
        elif type == "Commune":
            parent = "Prefecture"
        elif type == "Canton":
            parent = "Commune"
        elif type == "Village":
            parent = "Canton"
        return parent

    form_class = AdministrativeLevelForm  # specify the class form to be displayed

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = AdministrativeLevelForm(self.get_parent(self.request.GET.get("type")))
        return context

    def post(self, request, *args, **kwargs):
        form = AdministrativeLevelForm(self.get_parent(self.request.GET.get("type")), request.POST)
        if form.is_valid():
            form.save()
            return redirect('administrativelevels:list')
        return super(AdministrativeLevelCreateView, self).get(request, *args, **kwargs)


class AdministrativeLevelUpdateView(PageMixin, LoginRequiredMixin, AdminPermissionRequiredMixin, UpdateView):
    model = AdministrativeLevel
    template_name = 'administrativelevel_create.html'
    context_object_name = 'administrativelevel'
    title = _('Update Administrative level')
    active_level1 = 'administrative_levels'
    breadcrumb = [
        {
            'url': '',
            'title': title
        },
    ]

    def get_parent(self, type: str):
        parent = None
        if type == "Prefecture":
            parent = "Region"
        elif type == "Commune":
            parent = "Prefecture"
        elif type == "Canton":
            parent = "Commune"
        elif type == "Village":
            parent = "Canton"
        return parent

    form_class = AdministrativeLevelForm  # specify the class form to be displayed

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        print(self.request.GET.get("type"))
        context['form'] = AdministrativeLevelForm(self.get_parent(self.request.GET.get("type")),
                                                  instance=self.get_object())
        return context

    def post(self, request, *args, **kwargs):
        form = AdministrativeLevelForm(self.get_parent(self.request.GET.get("type")), request.POST,
                                       instance=self.get_object())
        if form.is_valid():
            form.save()
            return redirect('administrativelevels:list')
        return super(AdministrativeLevelUpdateView, self).get(request, *args, **kwargs)


class UploadCSVView(PageMixin, LoginRequiredMixin, AdminPermissionRequiredMixin, TemplateView):
    """Class to upload and save the administrativelevels"""

    template_name = 'upload.html'
    context_object_name = 'Upload'
    title = _("Upload")
    active_level1 = 'administrative_levels'
    breadcrumb = [
        {
            'url': '',
            'title': title
        },
    ]

    def post(self, request, *args, **kwargs):
        datas = {}
        redirect_path = 'administrativelevels:list'
        _type = request.POST.get('_type')
        if _type in ("priority", "subproject"):
            """Upload priorities by csv"""
            redirect_path = "administrativelevels:priorities_priorities"
            try:
                datas = convert_file_to_dict.conversion_file_xlsx_merger_to_dict(
                    request.FILES.get('file'), request.POST.get('sheet_name'),
                    columns_fillna=["Canton", "Villages",
                                    "Sous-projets prioritaire de la sous-composante 1.3 (Besoins des jeunes)"]
                )
            except pd.errors.ParserError as exc:
                datas = convert_file_to_dict.conversion_file_csv_merger_to_dict(
                    request.FILES.get('file'), request.POST.get('sheet_name'),
                    columns_fillna=["Canton", "Villages",
                                    "Sous-projets prioritaire de la sous-composante 1.3 (Besoins des jeunes)"]
                )
            except Exception as exc:
                messages.info(request, _("An error has occurred..."))

            try:
                administrative_level_id = request.POST["administrative_level_id"]
                message, file_path = administrativelevels_functions.save_csv_datas_priorities_in_db(datas,
                                                                                                    administrative_level_id if bool(
                                                                                                        request.POST.get(
                                                                                                            "administrative_level_id_checkbox")) else 0,
                                                                                                    _type)  # call function to save CSV datas in database

                return download_file.download(request, file_path, "text/plain")

                # if message:
                #     messages.info(request, message)
                # return redirect(redirect_path, administrative_level_id=administrative_level_id)
            except Exception as exc:
                raise Http404
        elif _type == "subproject_new":
            """Load Administrative Levels"""
            try:
                datas = convert_file_to_dict.conversion_file_xlsx_to_dict(request.FILES.get('file'),
                                                                          request.POST.get('sheet_name'))
            except pd.errors.ParserError as exc:
                datas = convert_file_to_dict.conversion_file_csv_to_dict(request.FILES.get('file'),
                                                                         request.POST.get('sheet_name'))
            except Exception as exc:
                messages.info(request, _("An error has occurred..."))
            try:
                message, file_path = administrativelevels_functions.save_csv_datas_priorities_in_db(datas, 0,
                                                                                                    _type)  # call function to save CSV datas in database

                return download_file.download(request, file_path, "text/plain")

            except Exception as exc:
                raise Http404

        else:
            """Load Administrative Levels"""
            try:
                datas = convert_file_to_dict.conversion_file_xlsx_to_dict(request.FILES.get('file'))
            except pd.errors.ParserError as exc:
                datas = convert_file_to_dict.conversion_file_csv_to_dict(request.FILES.get('file'))
            except Exception as exc:
                messages.info(request, _("An error has occurred..."))

            message = administrativelevels_functions.save_csv_file_datas_in_db(
                datas)  # call function to save CSV datas in database

        if message:
            messages.info(request, message)

        return redirect(redirect_path)

    def get(self, request, *args, **kwargs):
        context = super(UploadCSVView, self).get(request, *args, **kwargs)
        return context


class DownloadCSVView(PageMixin, LoginRequiredMixin, TemplateView):
    """Class to download administrativelevels under excel file"""

    template_name = 'components/download.html'
    context_object_name = 'Download'
    title = _("Download")
    active_level1 = 'administrative_levels'
    breadcrumb = [
        {
            'url': '',
            'title': title
        },
    ]

    def post(self, request, *args, **kwargs):
        file_path = ""
        try:
            file_path = administrativelevels_functions.get_administratives_levels_under_file_excel_or_csv(
                file_type=request.POST.get("file_type"),
                params={"type": request.POST.get("type"), "value_of_type": request.POST.get("value_of_type")}
            )

        except Exception as exc:
            messages.info(request, _("An error has occurred..."))

        if not file_path:
            return redirect('administrativelevels:list')
        else:
            return download_file.download(
                request,
                file_path,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )


class AdministrativeLevelsListView(PageMixin, LoginRequiredMixin, ListView):
    """Display administrative level list"""

    model = AdministrativeLevel
    queryset = []  # AdministrativeLevel.objects.filter(type="Village")
    template_name = 'administrativelevels_list.html'
    context_object_name = 'administrativelevels'
    title = _('Administrative levels')
    active_level1 = 'administrative_levels'
    breadcrumb = [
        {
            'url': '',
            'title': title
        },
    ]

    def get_queryset(self):
        search = self.request.GET.get("search", None)
        page_number = self.request.GET.get("page", None)
        _type = self.request.GET.get("type", "Village")
        if search:
            if search == "All":
                ads = AdministrativeLevel.objects.filter(type=_type)
                return Paginator(ads, ads.count()).get_page(page_number)
            search = search.upper()
            return Paginator(AdministrativeLevel.objects.filter(type=_type, name__icontains=search), 100).get_page(
                page_number)
        else:
            return Paginator(AdministrativeLevel.objects.filter(type=_type), 100).get_page(page_number)

        # return super().get_queryset()

    def get_context_data(self, **kwargs):
        ctx = super(AdministrativeLevelsListView, self).get_context_data(**kwargs)
        ctx['search'] = self.request.GET.get("search", None)
        ctx['type'] = self.request.GET.get("type", "Village")
        return ctx


# Obstacles
class ObstaclesListView(PageMixin, LoginRequiredMixin, TemplateView):
    model = VillageObstacle
    template_name = 'priorities/obstacles.html'
    context_object_name = 'obstacles'
    title = _('Village development priorities - Cycle 1')
    active_level1 = 'financial'
    active_level2 = 'obstacles'
    breadcrumb = [
        {
            'url': '',
            'title': title
        },
    ]
    administrative_level_id = 0
    administrativelevel_village = None

    def get_context_data(self, **kwargs):
        ctx = super(ObstaclesListView, self).get_context_data(**kwargs)
        ctx.setdefault('administrativelevel_village', ObstaclesListView.administrativelevel_village)
        ctx.setdefault('OBSTACLES_FOCUS_GROUP', OBSTACLES_FOCUS_GROUP)

        ctx.setdefault('obstacles', VillageObstacle.objects.filter(
            administrative_level_id=ObstaclesListView.administrative_level_id).order_by('ranking'))

        return ctx

    def get(self, request, *args, **kwargs):
        try:
            ObstaclesListView.administrative_level_id = kwargs['administrative_level_id']
            ObstaclesListView.administrativelevel_village = AdministrativeLevel.objects.get(
                id=ObstaclesListView.administrative_level_id, type="Village")
            context = super(ObstaclesListView, self).get(request, *args, **kwargs)
            # context['obstacles'] = VillageObstacle.objects.filter(administrative_level_id=ObstaclesListView.administrative_level_id)
        except Exception as exc:
            raise Http404
        return context

    def post(self, request, *args, **kwargs):

        group = request.POST.get('group')
        description = request.POST.get('description')
        if group and description:
            '''Add'''
            obstacle = VillageObstacle()
            obstacle.focus_group = group
            obstacle.description = description
            obstacle.administrative_level = ObstaclesListView.administrativelevel_village
            obstacle.meeting_id = 1
            obstacle.save()
            messages.info(request, _("Add successfully!"))
        else:
            '''Edit'''
            for key in request.POST:
                if key and type(key) is str and '-' in key and key[-1].isdigit():
                    try:
                        id_str = key.split('-')[-1]
                        id = int(id_str)
                        group = request.POST.get('group-' + id_str)
                        description = request.POST.get('description-' + id_str)
                        if group and description:
                            obstacle = VillageObstacle.objects.get(id=id)
                            obstacle.focus_group = group
                            obstacle.description = description
                            obstacle.save()
                            messages.info(request, _("Update successfully!"))
                            break
                    except Exception as exc:
                        raise Http404
        if not description:
            messages.info(request, _("The description is required"))

        return self.get(request, *args, **kwargs)


@login_required
def obstacle_delete(request, obstacle_id):
    """Function to delete one obstacle"""
    administrative_level_id = 0
    try:
        obstacle = VillageObstacle.objects.get(id=obstacle_id)
        administrative_level_id = obstacle.administrative_level_id
        obstacle.delete()
        messages.info(request, _("Obstacle delete successfully"))
    except Exception as exc:
        raise Http404

    return redirect('administrativelevels:priorities_obstacles', administrative_level_id=administrative_level_id)


# Goals
class GoalsListView(PageMixin, LoginRequiredMixin, TemplateView):
    model = VillageGoal
    template_name = 'priorities/goals.html'
    context_object_name = 'goals'
    title = _('Village development priorities - Cycle 1')
    active_level1 = 'financial'
    active_level2 = 'goals'
    breadcrumb = [
        {
            'url': '',
            'title': title
        },
    ]
    administrative_level_id = 0
    administrativelevel_village = None

    def get_context_data(self, **kwargs):
        ctx = super(GoalsListView, self).get_context_data(**kwargs)
        ctx.setdefault('administrativelevel_village', GoalsListView.administrativelevel_village)
        ctx.setdefault('GOALS_FOCUS_GROUP', GOALS_FOCUS_GROUP)

        ctx.setdefault('goals', VillageGoal.objects.filter(
            administrative_level_id=GoalsListView.administrative_level_id).order_by('ranking'))

        return ctx

    def get(self, request, *args, **kwargs):
        try:
            GoalsListView.administrative_level_id = kwargs['administrative_level_id']
            GoalsListView.administrativelevel_village = AdministrativeLevel.objects.get(
                id=GoalsListView.administrative_level_id, type="Village")
            context = super(GoalsListView, self).get(request, *args, **kwargs)
            # context['goals'] = VillageGoal.objects.filter(administrative_level_id=GoalsListView.administrative_level_id)
        except Exception as exc:
            raise Http404
        return context

    def post(self, request, *args, **kwargs):

        group = request.POST.get('group')
        description = request.POST.get('description')
        if group and description:
            '''Add'''
            goal = VillageGoal()
            goal.focus_group = group
            goal.description = description
            goal.administrative_level = GoalsListView.administrativelevel_village
            goal.meeting_id = 1
            goal.save()
            messages.info(request, _("Add successfully!"))
        else:
            '''Edit'''
            for key in request.POST:
                if key and type(key) is str and '-' in key and key[-1].isdigit():
                    try:
                        id_str = key.split('-')[-1]
                        id = int(id_str)
                        group = request.POST.get('group-' + id_str)
                        description = request.POST.get('description-' + id_str)
                        if group and description:
                            goal = VillageGoal.objects.get(id=id)
                            goal.focus_group = group
                            goal.description = description
                            goal.save()
                            messages.info(request, _("Update successfully!"))
                            break
                    except Exception as exc:
                        raise Http404
        if not description:
            messages.info(request, _("The description is required"))

        return self.get(request, *args, **kwargs)


@login_required
def goal_delete(request, goal_id):
    """Function to delete one goal"""
    administrative_level_id = 0
    try:
        goal = VillageGoal.objects.get(id=goal_id)
        administrative_level_id = goal.administrative_level_id
        goal.delete()
        messages.info(request, _("Goal delete successfully"))
    except Exception as exc:
        raise Http404

    return redirect('administrativelevels:priorities_goals', administrative_level_id=administrative_level_id)


# Priorities
class PrioritiesListView(PageMixin, LoginRequiredMixin, TemplateView):
    model = VillagePriority
    template_name = 'priorities/priorities.html'
    context_object_name = 'priorities'
    title = _('Village development priorities - Cycle 1')
    active_level1 = 'financial'
    active_level2 = 'eligible_priorities'
    breadcrumb = [
        {
            'url': '',
            'title': title
        },
    ]
    administrative_level_id = 0
    administrativelevel_village = None

    def get_context_data(self, **kwargs):
        ctx = super(PrioritiesListView, self).get_context_data(**kwargs)
        ctx.setdefault('administrativelevel_village', PrioritiesListView.administrativelevel_village)
        ctx.setdefault('components', Component.objects.all())
        ctx.setdefault('goals',
                       VillageGoal.objects.filter(administrative_level=PrioritiesListView.administrativelevel_village))

        ctx.setdefault('priorities', VillagePriority.objects.filter(
            administrative_level_id=PrioritiesListView.administrative_level_id).order_by('ranking'))

        return ctx

    def get(self, request, *args, **kwargs):
        try:
            PrioritiesListView.administrative_level_id = kwargs['administrative_level_id']
            PrioritiesListView.administrativelevel_village = AdministrativeLevel.objects.get(
                id=PrioritiesListView.administrative_level_id, type="Village")
            context = super(PrioritiesListView, self).get(request, *args, **kwargs)
            # context['priorities'] = VillagePriority.objects.filter(administrative_level_id=PrioritiesListView.administrative_level_id)

        except Exception as exc:
            raise Http404
        return context

    def post(self, request, *args, **kwargs):

        component_id = request.POST.get('component')
        proposed_men = request.POST.get('proposed_men')
        proposed_women = request.POST.get('proposed_women')
        estimated_cost = request.POST.get('estimated_cost')
        climate_changing_contribution = request.POST.get('climate_changing_contribution')
        if component_id and climate_changing_contribution:
            '''Add'''
            priority = VillagePriority()
            priority.component_id = int(component_id)
            priority.proposed_men = int(proposed_men) if proposed_men else 0
            priority.proposed_women = int(proposed_women) if proposed_women else 0
            priority.estimated_cost = float(estimated_cost) if estimated_cost else 0.0
            priority.climate_changing_contribution = climate_changing_contribution
            priority.administrative_level = PrioritiesListView.administrativelevel_village
            priority.meeting_id = 1
            priority.save()
            messages.info(request, _("Add successfully!"))
        else:
            '''Edit'''
            for key in request.POST:
                if key and type(key) is str and '-' in key and key[-1].isdigit():
                    try:
                        id_str = key.split('-')[-1]
                        id = int(id_str)
                        component_id = int(request.POST.get('component-' + id_str))
                        proposed_men = request.POST.get('proposed_men-' + id_str)
                        proposed_women = request.POST.get('proposed_women-' + id_str)
                        estimated_cost = request.POST.get('estimated_cost-' + id_str)
                        climate_changing_contribution = request.POST.get('climate_changing_contribution-' + id_str)
                        if component_id and climate_changing_contribution:
                            priority = VillagePriority.objects.get(id=id)
                            priority.component_id = component_id
                            priority.proposed_men = int(proposed_men) if proposed_men else 0
                            priority.proposed_women = int(proposed_women) if proposed_women else 0
                            priority.estimated_cost = float(estimated_cost) if estimated_cost else 0.0
                            priority.climate_changing_contribution = climate_changing_contribution
                            priority.save()
                            messages.info(request, _("Update successfully!"))
                            break
                    except Exception as exc:
                        raise Http404

        if not component_id or not climate_changing_contribution:
            messages.info(request, _("Choice one component and give the description!"))

        return self.get(request, *args, **kwargs)


@login_required
def priority_delete(request, priority_id):
    """Function to delete one priority"""
    administrative_level_id = 0
    try:
        priority = VillagePriority.objects.get(id=priority_id)
        administrative_level_id = priority.administrative_level_id
        priority.delete()
        messages.info(request, _("Priority delete successfully"))
    except Exception as exc:
        raise Http404

    return redirect('administrativelevels:priorities_priorities', administrative_level_id=administrative_level_id)


# ====================== Geographical unit=========================================
class GeographicalUnitListView(PageMixin, LoginRequiredMixin, ListView):
    """Display geographical unit list"""

    model = GeographicalUnit
    queryset = []  # GeographicalUnit.objects.all()
    template_name = 'geographical_unit_list.html'
    context_object_name = 'geographicalunits'
    title = _('Geographical units')
    active_level1 = 'administrative_levels'
    breadcrumb = [
        {
            'url': '',
            'title': title
        },
    ]

    # def get_queryset(self):
    #     return super().get_queryset()
    def get_queryset(self):
        search = self.request.GET.get("search", None)
        page_number = self.request.GET.get("page", None)
        if search:
            gs = GeographicalUnit.objects.all()
            if search == "All":
                return Paginator(gs, gs.count()).get_page(page_number)
            search = search.upper()
            _gs = []
            for g in gs:
                if search in g.get_name():
                    _gs.append(g)
            return Paginator(_gs, 100).get_page(page_number)
        else:
            return Paginator(GeographicalUnit.objects.all(), 100).get_page(page_number)

    def get_context_data(self, **kwargs):
        ctx = super(GeographicalUnitListView, self).get_context_data(**kwargs)
        ctx['search'] = self.request.GET.get("search", None)
        return ctx


class GeographicalUnitCreateView(PageMixin, LoginRequiredMixin, AdminPermissionRequiredMixin, CreateView):
    model = GeographicalUnit
    template_name = 'geographical_unit_create.html'
    context_object_name = 'geographicalunit'
    title = _('Create geographical unit')
    active_level1 = 'administrative_levels'
    breadcrumb = [
        {
            'url': '',
            'title': title
        },
    ]

    form_class = GeographicalUnitForm  # specify the class form to be displayed

    def post(self, request, *args, **kwargs):
        form = GeographicalUnitForm(request.POST)
        if form.is_valid():
            # cvds = form.cleaned_data['cvds']
            villages = form.cleaned_data['villages']

            unit = form.save(commit=False)
            # length_str = str(len(GeographicalUnit.objects.all())+1)
            try:
                length_str = str(GeographicalUnit.objects.all().last().pk + 1)
            except Exception as exc:
                length_str = "1"
            # import zlib
            # unit.unique_code = str(zlib.adler32(str(('0'*(9-len(length_str)))+length_str).encode('utf-8')))[:6]
            unit.unique_code = ('0' * (9 - len(length_str))) + length_str
            unit = unit.save_and_return_object()

            for village_id in villages:
                try:
                    village = AdministrativeLevel.objects.get(id=int(village_id))
                    village.geographical_unit = unit
                    village.save()
                except Exception as exc:
                    print(exc)

            return redirect('administrativelevels:geographical_units_list')
        return super(GeographicalUnitCreateView, self).get(request, *args, **kwargs)


class GeographicalUnitUpdateView(PageMixin, LoginRequiredMixin, AdminPermissionRequiredMixin, UpdateView):
    model = GeographicalUnit
    template_name = 'geographical_unit_create.html'
    context_object_name = 'geographicalunit'
    title = _('Update geographical unit')
    active_level1 = 'administrative_levels'
    breadcrumb = [
        {
            'url': '',
            'title': title
        },
    ]

    form_class = GeographicalUnitForm  # specify the class form to be displayed

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = GeographicalUnitForm(initial={
            "villages": [
                cat for cat in self.get_object().get_villages().values_list("id", flat=True)
            ]
        }, instance=self.get_object())

        # context['villages'] = self.get_object().geographical_unit.get_villages()

        return context

    def post(self, request, *args, **kwargs):
        form = GeographicalUnitForm(request.POST, instance=self.get_object())
        if form.is_valid():
            # cvds = form.cleaned_data['cvds']
            villages = form.cleaned_data['villages']

            unit = form.save(commit=False)
            unit = unit.save_and_return_object()
            unit.administrativelevel_set.clear()
            unit = unit.save_and_return_object()

            for village_id in villages:
                try:
                    village = AdministrativeLevel.objects.get(id=int(village_id))
                    village.geographical_unit = unit
                    village.save()
                except Exception as exc:
                    print(exc)

            # for cvd_id in cvds:
            #     try:
            #         cvd = CVD.objects.get(id=int(cvd_id))
            #         cvd.geographical_unit = unit
            #         cvd.save()
            #     except Exception as exc:
            #         print(exc)

            return redirect('administrativelevels:geographical_units_list')
        return super(GeographicalUnitUpdateView, self).get(request, *args, **kwargs)


class GeographicalUnitDetailView(PageMixin, LoginRequiredMixin, DetailView):
    """Class to present the detail page of one geographical unit"""
    model = GeographicalUnit
    template_name = 'geographical_unit_detail.html'
    context_object_name = 'geographicalunit'
    title = _('Geographical unit')
    active_level1 = 'financial'
    breadcrumb = [
        {
            'url': reverse_lazy('administrativelevels:geographical_units_list'),
            'title': _('Geographical units')
        },
        {
            'url': '',
            'title': title
        },
    ]


# ======================================CVD==============================================

class CVDListView(PageMixin, LoginRequiredMixin, ListView):
    """Display geographical unit list"""

    model = CVD
    queryset = []  # CVD.objects.filter()
    template_name = 'cvds_list.html'
    context_object_name = 'cvds'
    title = _('CVD')
    active_level1 = 'administrative_levels'
    breadcrumb = [
        {
            'url': '',
            'title': title
        },
    ]

    # def get_queryset(self):
    #     return super().get_queryset()
    def get_queryset(self):
        search = self.request.GET.get("search", None)
        page_number = self.request.GET.get("page", None)
        if search:
            if search == "All":
                cs = CVD.objects.all()
                return Paginator(cs, cs.count()).get_page(page_number)
            search = search.upper()
            return Paginator(CVD.objects.filter(name__icontains=search), 100).get_page(page_number)
        else:
            return Paginator(CVD.objects.all(), 100).get_page(page_number)

    def get_context_data(self, **kwargs):
        ctx = super(CVDListView, self).get_context_data(**kwargs)
        ctx['search'] = self.request.GET.get("search", None)
        return ctx


class CVDCreateView(PageMixin, LoginRequiredMixin, AdminPermissionRequiredMixin, CreateView):
    model = CVD
    template_name = 'cvd_create.html'
    context_object_name = 'cvd'
    title = _('Create CVD')
    active_level1 = 'administrative_levels'
    breadcrumb = [
        {
            'url': '',
            'title': title
        },
    ]

    form_class = CVDForm  # specify the class form to be displayed

    def post(self, request, *args, **kwargs):
        form = CVDForm(request.POST)
        if form.is_valid():
            villages = form.cleaned_data['villages']

            cvd = form.save(commit=False)
            # length_str = str(len(CVD.objects.all())+1)
            try:
                length_str = str(CVD.objects.all().last().pk + 1)
            except Exception as exc:
                length_str = "1"
            cvd.unique_code = ('0' * (9 - len(length_str))) + length_str
            cvd = cvd.save_and_return_object()

            for village_id in villages:
                try:
                    village = AdministrativeLevel.objects.get(id=int(village_id))
                    village.cvd = cvd
                    village.save()
                except Exception as exc:
                    print(exc)

            return redirect('administrativelevels:cvds_list')
        return super(CVDCreateView, self).get(request, *args, **kwargs)


class CVDUpdateView(PageMixin, LoginRequiredMixin, AdminPermissionRequiredMixin, UpdateView):
    model = CVD
    template_name = 'cvd_create.html'
    context_object_name = 'cvd'
    title = _('Update CVD')
    active_level1 = 'administrative_levels'
    breadcrumb = [
        {
            'url': '',
            'title': title
        },
    ]

    form_class = CVDForm  # specify the class form to be displayed

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = CVDForm(initial={
            "villages": [
                cat for cat in self.get_object().get_villages().values_list("id", flat=True)
            ]
        }, instance=self.get_object())

        # context['villages'] = self.get_object().geographical_unit.get_villages()

        return context

    def post(self, request, *args, **kwargs):
        form = CVDForm(request.POST, instance=self.get_object())
        if form.is_valid():
            villages = form.cleaned_data['villages']

            cvd = form.save(commit=False)
            cvd = cvd.save_and_return_object()
            cvd.administrativelevel_set.clear()
            cvd = cvd.save_and_return_object()

            for village_id in villages:
                try:
                    village = AdministrativeLevel.objects.get(id=int(village_id))
                    village.cvd = cvd
                    village.save()
                except Exception as exc:
                    print(exc)

            return redirect('administrativelevels:cvds_list')
        return super(CVDUpdateView, self).get(request, *args, **kwargs)


class CVDDetailView(PageMixin, LoginRequiredMixin, DetailView):
    """Class to present the detail page of one CVD"""
    model = CVD
    template_name = 'cvd_detail.html'
    context_object_name = 'cvd'
    title = _('CVD')
    active_level1 = 'financial'
    breadcrumb = [
        {
            'url': reverse_lazy('administrativelevels:cvds_list'),
            'title': _('CVD')
        },
        {
            'url': '',
            'title': title
        },
    ]
