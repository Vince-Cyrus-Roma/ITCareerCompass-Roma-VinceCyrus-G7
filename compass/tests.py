from io import StringIO

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from .models import CareerPath, QuizAnswer, QuizAttempt, QuizChoice, QuizQuestion

User = get_user_model()


class CompassAdminCrudTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username="student",
            password="StrongPass123!",
            role=User.Role.STUDENT,
        )
        self.admin = User.objects.create_user(
            username="admin_user",
            password="StrongPass123!",
            role=User.Role.ADMIN,
        )
        self.coding = CareerPath.objects.create(
            name="Coding", description="Software engineering"
        )
        self.design = CareerPath.objects.create(
            name="UI/UX Design", description="Product and interface design"
        )

    def test_admin_panel_requires_admin_role(self):
        self.client.force_login(self.student)
        for url_name in ["admin_panel", "career_create", "question_create"]:
            response = self.client.get(reverse(url_name))
            self.assertEqual(response.status_code, 403)

        self.client.force_login(self.admin)
        response = self.client.get(reverse("admin_panel"))
        self.assertEqual(response.status_code, 200)

    def test_career_path_crud_and_duplicate_validation(self):
        self.client.force_login(self.admin)
        # Case-insensitive duplicate blocked
        response = self.client.post(
            reverse("career_create"),
            {"name": "coding", "description": "Duplicate"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(CareerPath.objects.count(), 2)

        # Create valid career
        response = self.client.post(
            reverse("career_create"),
            {"name": "Networking", "description": "Routers and infrastructure"},
        )
        self.assertRedirects(response, reverse("admin_panel"))
        networking = CareerPath.objects.get(name="Networking")

        # Update career
        response = self.client.post(
            reverse("career_update", args=[networking.pk]),
            {"name": "Networking", "description": "Cloud & campus networks"},
        )
        self.assertRedirects(response, reverse("admin_panel"))
        networking.refresh_from_db()
        self.assertEqual(networking.description, "Cloud & campus networks")

        # Delete career
        response = self.client.post(reverse("career_delete", args=[networking.pk]))
        self.assertRedirects(response, reverse("admin_panel"))
        self.assertFalse(CareerPath.objects.filter(pk=networking.pk).exists())

    def test_question_and_choices_crud_and_protected_career(self):
        self.client.force_login(self.admin)

        # Reject question with fewer than 2 choices
        bad_payload = {
            "text": "What do you prefer?",
            "order": 1,
            "is_active": "on",
            "choices-TOTAL_FORMS": "4",
            "choices-INITIAL_FORMS": "0",
            "choices-MIN_NUM_FORMS": "0",
            "choices-MAX_NUM_FORMS": "1000",
            "choices-0-text": "Write APIs",
            "choices-0-career_path": str(self.coding.pk),
            "choices-1-text": "",
            "choices-1-career_path": "",
            "choices-2-text": "",
            "choices-2-career_path": "",
            "choices-3-text": "",
            "choices-3-career_path": "",
        }
        response = self.client.post(reverse("question_create"), bad_payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(QuizQuestion.objects.count(), 0)

        # Create question with 2 valid choices
        good_payload = {
            **bad_payload,
            "choices-1-text": "Design wireframes",
            "choices-1-career_path": str(self.design.pk),
        }
        response = self.client.post(reverse("question_create"), good_payload)
        self.assertRedirects(response, reverse("admin_panel"))
        question = QuizQuestion.objects.get()
        self.assertEqual(question.created_by, self.admin)
        self.assertEqual(question.choices.count(), 2)

        # ProtectedError handled cleanly when deleting referenced CareerPath
        response = self.client.post(reverse("career_delete", args=[self.coding.pk]))
        self.assertRedirects(response, reverse("admin_panel"))
        self.assertTrue(CareerPath.objects.filter(pk=self.coding.pk).exists())

        # Update question
        c1, c2 = list(question.choices.order_by("id"))
        update_payload = {
            "text": "Which task excites you most?",
            "order": 2,
            "is_active": "on",
            "choices-TOTAL_FORMS": "3",
            "choices-INITIAL_FORMS": "2",
            "choices-MIN_NUM_FORMS": "0",
            "choices-MAX_NUM_FORMS": "1000",
            "choices-0-id": str(c1.pk),
            "choices-0-question": str(question.pk),
            "choices-0-text": "Build web apps",
            "choices-0-career_path": str(self.coding.pk),
            "choices-1-id": str(c2.pk),
            "choices-1-question": str(question.pk),
            "choices-1-text": "Design UI prototypes",
            "choices-1-career_path": str(self.design.pk),
            "choices-2-id": "",
            "choices-2-question": str(question.pk),
            "choices-2-text": "",
            "choices-2-career_path": "",
        }
        response = self.client.post(
            reverse("question_update", args=[question.pk]), update_payload
        )
        self.assertRedirects(response, reverse("admin_panel"))
        question.refresh_from_db()
        self.assertEqual(question.text, "Which task excites you most?")
        self.assertEqual(question.order, 2)

        # Delete question
        response = self.client.post(reverse("question_delete", args=[question.pk]))
        self.assertRedirects(response, reverse("admin_panel"))
        self.assertEqual(QuizQuestion.objects.count(), 0)

    def test_quiz_answer_clean_validates_choice_belongs_to_question(self):
        q1 = QuizQuestion.objects.create(text="Q1", order=1)
        q2 = QuizQuestion.objects.create(text="Q2", order=2)
        c1 = QuizChoice.objects.create(
            question=q1, text="C1", career_path=self.coding
        )
        c2 = QuizChoice.objects.create(
            question=q2, text="C2", career_path=self.design
        )
        attempt = QuizAttempt.objects.create(user=self.student)

        bad_answer = QuizAnswer(attempt=attempt, question=q1, choice=c2)
        with self.assertRaises(ValidationError):
            bad_answer.full_clean()

        good_answer = QuizAnswer(attempt=attempt, question=q1, choice=c1)
        good_answer.full_clean()

    def test_seed_quiz_command_is_idempotent(self):
        out = StringIO()
        call_command("seed_quiz", stdout=out)
        self.assertEqual(CareerPath.objects.count(), 4)
        self.assertEqual(QuizQuestion.objects.count(), 6)
        self.assertEqual(QuizChoice.objects.count(), 24)

        call_command("seed_quiz", stdout=out)
        self.assertEqual(CareerPath.objects.count(), 4)
        self.assertEqual(QuizQuestion.objects.count(), 6)
        self.assertEqual(QuizChoice.objects.count(), 24)
