from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class CareerPath(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class QuizQuestion(models.Model):
    text = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="created_questions")

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.text


class QuizChoice(models.Model):
    question = models.ForeignKey(
        QuizQuestion, on_delete=models.CASCADE, related_name="choices")
    text = models.CharField(max_length=255)
    career_path = models.ForeignKey(
        CareerPath, on_delete=models.PROTECT, related_name="choices")

    def __str__(self):
        return f"{self.text} -> {self.career_path}"


class QuizAttempt(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="quiz_attempts")
    top_career = models.ForeignKey(
        CareerPath, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="top_attempts")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} - {self.created_at:%Y-%m-%d}"


class QuizAnswer(models.Model):
    attempt = models.ForeignKey(
        QuizAttempt, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(QuizQuestion, on_delete=models.CASCADE)
    choice = models.ForeignKey(QuizChoice, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("attempt", "question")

    def clean(self):
        super().clean()
        if (
            self.choice_id
            and self.question_id
            and self.choice.question_id != self.question_id
        ):
            raise ValidationError(
                {"choice": "Selected choice does not belong to the specified question."}
            )