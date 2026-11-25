from django.contrib import admin
from .models import (
    CareerPath,
    QuizAnswer,
    QuizAttempt,
    QuizChoice,
    QuizQuestion,
)


class QuizChoiceInline(admin.TabularInline):
    model = QuizChoice
    extra = 4


class QuizAnswerInline(admin.TabularInline):
    model = QuizAnswer
    extra = 0
    readonly_fields = ("question", "choice")


@admin.register(CareerPath)
class CareerPathAdmin(admin.ModelAdmin):
    list_display = ("name", "description")
    search_fields = ("name",)


@admin.register(QuizQuestion)
class QuizQuestionAdmin(admin.ModelAdmin):
    list_display = ("order", "text", "is_active", "created_by")
    list_filter = ("is_active",)
    search_fields = ("text",)
    inlines = [QuizChoiceInline]


@admin.register(QuizChoice)
class QuizChoiceAdmin(admin.ModelAdmin):
    list_display = ("text", "question", "career_path")
    list_filter = ("career_path",)
    search_fields = ("text", "question__text")


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ("user", "top_career", "created_at", "updated_at")
    list_filter = ("top_career", "created_at")
    search_fields = ("user__username",)
    inlines = [QuizAnswerInline]


@admin.register(QuizAnswer)
class QuizAnswerAdmin(admin.ModelAdmin):
    list_display = ("attempt", "question", "choice")
    list_filter = ("question",)
