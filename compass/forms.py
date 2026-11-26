from django import forms
from django.forms import BaseInlineFormSet, inlineformset_factory
from collections import Counter

from .models import CareerPath, QuizChoice, QuizQuestion


class CareerPathForm(forms.ModelForm):
    class Meta:
        model = CareerPath
        fields = ["name", "description"]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "e.g., Coding"}
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Describe the career path and typical focus areas...",
                }
            ),
        }

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        qs = CareerPath.objects.filter(name__iexact=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(
                "A career path with this name already exists."
            )
        return name


class QuizQuestionForm(forms.ModelForm):
    class Meta:
        model = QuizQuestion
        fields = ["text", "order", "is_active"]
        widgets = {
            "text": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter the quiz question...",
                }
            ),
            "order": forms.NumberInput(
                attrs={"class": "form-control", "min": 0}
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean_text(self):
        return self.cleaned_data["text"].strip()


class QuizChoiceForm(forms.ModelForm):
    class Meta:
        model = QuizChoice
        fields = ["text", "career_path"]
        widgets = {
            "text": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Choice option text...",
                }
            ),
            "career_path": forms.Select(attrs={"class": "form-select"}),
        }

    def clean_text(self):
        return self.cleaned_data["text"].strip()


class BaseQuizChoiceFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return

        active_choices = 0
        for form in self.forms:
            if self.can_delete and self._should_delete_form(form):
                continue
            if form.cleaned_data and form.cleaned_data.get("text"):
                active_choices += 1

        if active_choices < 2:
            raise forms.ValidationError(
                "Each question must have at least 2 answer choices."
            )


def get_choice_formset_class(extra=4):
    return inlineformset_factory(
        QuizQuestion,
        QuizChoice,
        form=QuizChoiceForm,
        formset=BaseQuizChoiceFormSet,
        extra=extra,
        can_delete=True,
    )





QuizChoiceCreateFormSet = get_choice_formset_class(extra=4)
QuizChoiceEditFormSet = get_choice_formset_class(extra=1)


class QuizTakeForm(forms.Form):
    def __init__(self, *args, questions=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.questions = list(questions or [])
        for question in self.questions:
            choices = [
                (str(choice.pk), choice.text)
                for choice in question.choices.all()
            ]
            self.fields[f"question_{question.pk}"] = forms.ChoiceField(
                label=question.text,
                choices=choices,
                widget=forms.RadioSelect(attrs={"class": "form-check-input"}),
                required=True,
                error_messages={
                    "required": "Please select an answer for this question."
                },
            )

    def get_selected_pairs(self):
        choice_ids = [
            int(self.cleaned_data[f"question_{q.pk}"])
            for q in self.questions
        ]
        choices_by_id = QuizChoice.objects.select_related(
            "career_path", "question"
        ).in_bulk(choice_ids)
        return [
            (q, choices_by_id[int(self.cleaned_data[f"question_{q.pk}"])])
            for q in self.questions
        ]


def calculate_career_breakdown(selected_choices):
    careers = list(CareerPath.objects.order_by("name"))
    if not selected_choices or not careers:
        return None, []

    counts = {career.pk: 0 for career in careers}
    for choice in selected_choices:
        if choice.career_path_id in counts:
            counts[choice.career_path_id] += 1

    total = len(selected_choices)
    ranked = sorted(
        careers,
        key=lambda career: (-counts[career.pk], career.name),
    )
    breakdown = [
        {
            "career": career,
            "count": counts[career.pk],
            "percentage": round((counts[career.pk] / total) * 100, 1),
        }
        for career in ranked
    ]
    return ranked[0], breakdown
