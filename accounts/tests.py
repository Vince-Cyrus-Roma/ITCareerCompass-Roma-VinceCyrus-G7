from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class AccountTests(TestCase):
    def test_signup_creates_student_user(self):
        response = self.client.post(
            reverse("signup"),
            {
                "username": "student1",
                "email": "student1@example.com",
                "first_name": "Ana",
                "last_name": "Cruz",
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
            },
        )
        self.assertRedirects(response, reverse("login"))
        user = User.objects.get(username="student1")
        self.assertEqual(user.role, User.Role.STUDENT)
        self.assertFalse(user.is_admin_role)

    def test_superuser_defaults_to_admin_role(self):
        admin = User.objects.create_superuser(
            username="root", email="root@example.com", password="StrongPass123!"
        )
        self.assertEqual(admin.role, User.Role.ADMIN)
        self.assertTrue(admin.is_admin_role)

    def test_profile_requires_login_and_updates_user(self):
        self.assertRedirects(
            self.client.get(reverse("profile")),
            f"{reverse('login')}?next={reverse('profile')}",
        )
        user = User.objects.create_user(
            username="student2", password="StrongPass123!"
        )
        self.client.force_login(user)
        response = self.client.post(
            reverse("profile"),
            {
                "first_name": "Updated",
                "last_name": "Name",
                "email": "updated@example.com",
            },
        )
        self.assertRedirects(response, reverse("profile"))
        user.refresh_from_db()
        self.assertEqual(user.first_name, "Updated")
        self.assertEqual(user.email, "updated@example.com")
