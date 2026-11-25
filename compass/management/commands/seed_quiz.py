from django.core.management.base import BaseCommand
from django.db import transaction

from compass.models import CareerPath, QuizChoice, QuizQuestion


CAREER_PATHS = [
    (
        "Coding",
        "Software development, algorithms, backend/frontend engineering, and building applications.",
    ),
    (
        "UI/UX Design",
        "User research, wireframing, prototyping, visual design, and crafting intuitive interfaces.",
    ),
    (
        "Networking",
        "Network architecture, routing and switching, cloud infrastructure, and connectivity.",
    ),
    (
        "Cybersecurity",
        "Threat analysis, penetration testing, defensive security, and protecting systems and data.",
    ),
]

STARTER_QUESTIONS = [
    (
        1,
        "Which class project sounds most exciting to build?",
        {
            "Coding": "Build a full-stack web or mobile application from scratch.",
            "UI/UX Design": "Design an interactive prototype and conduct usability testing.",
            "Networking": "Configure routers, VLANs, and a reliable campus network.",
            "Cybersecurity": "Audit an app for vulnerabilities and write a security report.",
        },
    ),
    (
        2,
        "When a system breaks, what is your first instinct?",
        {
            "Coding": "Read the stack trace and debug the source code.",
            "UI/UX Design": "Check where users got confused in the workflow.",
            "Networking": "Inspect traffic, DNS, and server connectivity.",
            "Cybersecurity": "Check logs for unauthorized access or suspicious activity.",
        },
    ),
    (
        3,
        "Which skill would you like to master first?",
        {
            "Coding": "Data structures, APIs, and clean architecture.",
            "UI/UX Design": "Design systems, typography, and user journey mapping.",
            "Networking": "TCP/IP, firewall rules, and cloud networking.",
            "Cybersecurity": "Ethical hacking, cryptography, and incident response.",
        },
    ),
    (
        4,
        "What kind of work output gives you the most satisfaction?",
        {
            "Coding": "Shipping clean, well-tested features that solve real problems.",
            "UI/UX Design": "Turning complex tasks into effortless, attractive screens.",
            "Networking": "Keeping distributed systems fast, reachable, and resilient.",
            "Cybersecurity": "Hardening defenses and preventing data breaches.",
        },
    ),
    (
        5,
        "Which toolset are you most curious to explore?",
        {
            "Coding": "Python, JavaScript, Git, and automated test frameworks.",
            "UI/UX Design": "Figma, wireframing kits, and accessibility checkers.",
            "Networking": "Wireshark, Cisco Packet Tracer, and Linux networking tools.",
            "Cybersecurity": "Nmap, Burp Suite, SIEM dashboards, and threat labs.",
        },
    ),
    (
        6,
        "In a team hackathon, which role would you pick?",
        {
            "Coding": "Backend or frontend developer writing the core logic.",
            "UI/UX Design": "Product designer shaping the user flow and interface.",
            "Networking": "Infrastructure lead managing deployment and server uptime.",
            "Cybersecurity": "Security lead reviewing auth, input handling, and data safety.",
        },
    ),
]


class Command(BaseCommand):
    help = "Seed default IT career paths and starter quiz questions."

    @transaction.atomic
    def handle(self, *args, **options):
        careers = {}
        created_careers = 0
        for name, description in CAREER_PATHS:
            career, created = CareerPath.objects.get_or_create(
                name=name, defaults={"description": description}
            )
            if not created and not career.description:
                career.description = description
                career.save(update_fields=["description"])
            careers[name] = career
            if created:
                created_careers += 1

        created_questions = 0
        for order, text, choices_map in STARTER_QUESTIONS:
            question, created = QuizQuestion.objects.get_or_create(
                text=text,
                defaults={"order": order, "is_active": True},
            )
            if created:
                created_questions += 1
            for career_name, choice_text in choices_map.items():
                QuizChoice.objects.get_or_create(
                    question=question,
                    career_path=careers[career_name],
                    defaults={"text": choice_text},
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Seed complete: {created_careers} career paths and "
                f"{created_questions} starter questions added."
            )
        )
