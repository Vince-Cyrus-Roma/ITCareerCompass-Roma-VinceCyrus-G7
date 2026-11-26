from django.urls import path

from .views import (
    AdminPanelView,
    CareerPathCreateView,
    CareerPathDeleteView,
    CareerPathUpdateView,
    DashboardView,
    QuestionCreateView,
    QuestionDeleteView,
    QuestionUpdateView,
    QuizAttemptDeleteView,
    QuizResultView,
    QuizTakeView,
)

urlpatterns = [
    path("", DashboardView.as_view(), name="dashboard"),
    path("admin-panel/", AdminPanelView.as_view(), name="admin_panel"),
    path("admin-panel/careers/new/", CareerPathCreateView.as_view(), name="career_create"),
    path(
        "admin-panel/careers/<int:pk>/edit/",
        CareerPathUpdateView.as_view(),
        name="career_update",
    ),
    path(
        "admin-panel/careers/<int:pk>/delete/",
        CareerPathDeleteView.as_view(),
        name="career_delete",
    ),
    path(
        "admin-panel/questions/new/",
        QuestionCreateView.as_view(),
        name="question_create",
    ),
    path(
        "admin-panel/questions/<int:pk>/edit/",
        QuestionUpdateView.as_view(),
        name="question_update",
    ),
    path(
        "admin-panel/questions/<int:pk>/delete/",
        QuestionDeleteView.as_view(),
        name="question_delete",
    ),
    path("quiz/", QuizTakeView.as_view(), name="quiz_take"),
    path("quiz/results/<int:pk>/", QuizResultView.as_view(), name="quiz_result"),
    path(
        "quiz/results/<int:pk>/delete/",
        QuizAttemptDeleteView.as_view(),
        name="attempt_delete",
    ),

]
