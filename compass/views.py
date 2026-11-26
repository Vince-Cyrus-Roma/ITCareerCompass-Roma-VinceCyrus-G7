from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db import transaction
from django.db.models import Count, ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, TemplateView, UpdateView, DetailView

from accounts.models import CustomUser

from .forms import (
    CareerPathForm,
    QuizChoiceCreateFormSet,
    QuizChoiceEditFormSet,
    QuizQuestionForm,
    QuizTakeForm,
    calculate_career_breakdown
)
from .models import CareerPath, QuizAnswer, QuizAttempt, QuizQuestion

class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_admin_role


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_attempts = QuizAttempt.objects.filter(
            user=self.request.user
        ).select_related("top_career")
        context["member_count"] = CustomUser.objects.count()
        context["is_admin"] = self.request.user.is_admin_role
        context["active_question_count"] = QuizQuestion.objects.filter(
            is_active=True, choices__isnull=False
        ).distinct().count()
        context["user_attempts"] = user_attempts
        context["latest_attempt"] = user_attempts.first()
        context["attempt_count"] = user_attempts.count()
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


class StudentRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return not self.request.user.is_admin_role

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            messages.error(self.request, "Only Students can take the quiz.")
            return redirect("dashboard")
        return super().handle_no_permission() 


class QuizTakeView(StudentRequiredMixin, View):
    template_name = "compass/quiz_take.html"

    def get_questions(self):
        return (
            QuizQuestion.objects.filter(is_active=True, choices__isnull=False)
            .distinct()
            .prefetch_related("choices")
        )

    def get(self, request):
        questions = list(self.get_questions())
        if not questions:
            messages.warning(request, "The quiz has no questions yet. Please check back later.")
            return redirect("dashboard")
        form = QuizTakeForm(questions=questions)
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        questions = list(self.get_questions())
        form = QuizTakeForm(request.POST, questions=questions)
        if form.is_valid():
            pairs = form.get_selected_pairs()
            with transaction.atomic():
                attempt = QuizAttempt.objects.create(user=request.user)
                QuizAnswer.objects.bulk_create(
                    [
                        QuizAnswer(attempt=attempt, question=q, choice=c)
                        for q, c in pairs
                    ]
                )
                top_career, _ = calculate_career_breakdown(
                    [c for _, c in pairs]
                )
                attempt.top_career = top_career
                attempt.save()
            messages.success(request, "Quiz submitted! Here are your results.")
            return redirect("quiz_result", pk=attempt.pk)
        messages.error(request, "Please answer every question before submitting.")
        return render(request, self.template_name, {"form": form})

class QuizResultView(LoginRequiredMixin, DetailView):
    model = QuizAttempt
    template_name = "compass/quiz_result.html"
    context_object_name = "attempt"

    def get_queryset(self):
        qs = QuizAttempt.objects.select_related("user", "top_career")
        if self.request.user.is_admin_role:
            return qs
        return qs.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        answers = list(
            self.object.answers.select_related("question", "choice__career_path")
        )
        _, breakdown = calculate_career_breakdown([a.choice for a in answers])
        context["answers"] = answers
        context["breakdown"] = breakdown
        return context

class QuizAttemptDeleteView(LoginRequiredMixin, DeleteView):
    model = QuizAttempt
    template_name = "compass/attempt_confirm_delete.html"
    success_url = reverse_lazy("dashboard")

    def get_queryset(self):
        return QuizAttempt.objects.filter(user=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, "Quiz attempt deleted.")
        return super().form_valid(form)

        