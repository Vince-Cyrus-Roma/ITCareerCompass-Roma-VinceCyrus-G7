from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db import transaction
from django.db.models import Count, ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, TemplateView, UpdateView

from accounts.models import CustomUser

from .forms import (
    CareerPathForm,
    QuizChoiceCreateFormSet,
    QuizChoiceEditFormSet,
    QuizQuestionForm,
)
from .models import CareerPath, QuizAttempt, QuizQuestion


class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_admin_role


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["member_count"] = CustomUser.objects.count()
        context["is_admin"] = self.request.user.is_admin_role
        context["active_question_count"] = QuizQuestion.objects.filter(
            is_active=True
        ).count()
        return context


class AdminPanelView(AdminRequiredMixin, TemplateView):
    template_name = "dashboard/admin_panel.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        career_paths = CareerPath.objects.annotate(
            choice_count=Count("choices", distinct=True),
            attempt_count=Count("top_attempts", distinct=True),
        ).order_by("name")
        questions = (
            QuizQuestion.objects.select_related("created_by")
            .prefetch_related("choices__career_path")
            .all()
        )
        context.update(
            {
                "career_paths": career_paths,
                "questions": questions,
                "career_count": career_paths.count(),
                "question_count": questions.count(),
                "active_question_count": questions.filter(is_active=True).count(),
                "attempt_count": QuizAttempt.objects.count(),
                "student_count": CustomUser.objects.filter(
                    role=CustomUser.Role.STUDENT
                ).count(),
            }
        )
        return context


class CareerPathCreateView(AdminRequiredMixin, SuccessMessageMixin, CreateView):
    model = CareerPath
    form_class = CareerPathForm
    template_name = "compass/career_form.html"
    success_url = reverse_lazy("admin_panel")
    success_message = "Career path created."


class CareerPathUpdateView(AdminRequiredMixin, SuccessMessageMixin, UpdateView):
    model = CareerPath
    form_class = CareerPathForm
    template_name = "compass/career_form.html"
    success_url = reverse_lazy("admin_panel")
    success_message = "Career path updated."


class CareerPathDeleteView(AdminRequiredMixin, DeleteView):
    model = CareerPath
    template_name = "compass/career_confirm_delete.html"
    success_url = reverse_lazy("admin_panel")

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        try:
            self.object.delete()
            messages.success(request, f'Career path "{self.object.name}" deleted.')
        except ProtectedError:
            messages.error(
                request,
                f'Cannot delete "{self.object.name}" because quiz choices still reference it.',
            )
        return redirect(self.success_url)


class BaseQuestionManageView(AdminRequiredMixin, View):
    template_name = "compass/question_form.html"

    def render_forms(self, request, form, formset, question=None):
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "formset": formset,
                "question": question,
                "has_career_paths": CareerPath.objects.exists(),
            },
        )

    def save_forms(self, request, form, formset, is_create=False):
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                question = form.save(commit=False)
                if is_create:
                    question.created_by = request.user
                question.save()
                formset.instance = question
                formset.save()
            action = "created" if is_create else "updated"
            messages.success(request, f"Quiz question {action}.")
            return True
        messages.error(request, "Please fix the errors below before saving.")
        return False


class QuestionCreateView(BaseQuestionManageView):
    def get(self, request):
        form = QuizQuestionForm()
        formset = QuizChoiceCreateFormSet()
        return self.render_forms(request, form, formset)

    def post(self, request):
        form = QuizQuestionForm(request.POST)
        formset = QuizChoiceCreateFormSet(request.POST)
        if self.save_forms(request, form, formset, is_create=True):
            return redirect("admin_panel")
        return self.render_forms(request, form, formset)


class QuestionUpdateView(BaseQuestionManageView):
    def get(self, request, pk):
        question = get_object_or_404(QuizQuestion, pk=pk)
        form = QuizQuestionForm(instance=question)
        formset = QuizChoiceEditFormSet(instance=question)
        return self.render_forms(request, form, formset, question=question)

    def post(self, request, pk):
        question = get_object_or_404(QuizQuestion, pk=pk)
        form = QuizQuestionForm(request.POST, instance=question)
        formset = QuizChoiceEditFormSet(request.POST, instance=question)
        if self.save_forms(request, form, formset, is_create=False):
            return redirect("admin_panel")
        return self.render_forms(request, form, formset, question=question)


class QuestionDeleteView(AdminRequiredMixin, DeleteView):
    model = QuizQuestion
    template_name = "compass/question_confirm_delete.html"
    success_url = reverse_lazy("admin_panel")

    def form_valid(self, form):
        messages.success(self.request, "Quiz question deleted.")
        return super().form_valid(form)
