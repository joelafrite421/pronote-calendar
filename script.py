import datetime
import os
import requests
from zoneinfo import ZoneInfo
from icalendar import Calendar, Event
import pronotepy
import pronotepy.ent

PRONOTE_URL = os.environ.get("PRONOTE_URL")
USERNAME = os.environ.get("PRONOTE_USERNAME")
PASSWORD = os.environ.get("PRONOTE_PASSWORD")
ENT = pronotepy.ent.ent_ecollege78
CHILD_NAME = "Luce"
FREE_USER = os.getenv("FREE_USER")
FREE_PASS = os.getenv("FREE_PASS")

def main():
    if not all([PRONOTE_URL, USERNAME, PASSWORD]):
        print("Erreur : secrets manquants.")
        return

    client = pronotepy.ParentClient(
        PRONOTE_URL, username=USERNAME, password=PASSWORD, ent=ENT
    )
    if not client.logged_in:
        print("Échec de connexion.")
        return

    children = [
        c for c in client.children if CHILD_NAME.lower() in c.name.lower()
    ]
    target_child = children[0] if children else client.children[0]
    client.set_child(target_child)

    cal = Calendar()
    cal.add("prodid", "-//Pronote Calendar//FR")
    cal.add("version", "2.0")
    cal.add("x-wr-timezone", "Europe/Paris")

    paris_tz = ZoneInfo("Europe/Paris")
    today = datetime.date.today()

    for i in range(7):
        day = today + datetime.timedelta(days=i)
        lessons = client.lessons(day)

        for lesson in sorted(lessons, key=lambda x: x.start):
            if lesson.canceled:
                continue

            e = Event()
            e.add("summary", lesson.subject.name)

            # Pronote fournit l'heure en heure locale française (ex: 09:20).
            # On lui associe directement le fuseau Europe/Paris sans la traiter comme de l'UTC.
            start_dt = lesson.start
            end_dt = lesson.end

            if start_dt.tzinfo is None:
                start_paris = start_dt.replace(tzinfo=paris_tz)
            else:
                start_paris = start_dt.astimezone(paris_tz)

            if end_dt.tzinfo is None:
                end_paris = end_dt.replace(tzinfo=paris_tz)
            else:
                end_paris = end_dt.astimezone(paris_tz)

            # Transmettre à icalendar avec le fuseau Paris
            e.add("dtstart", start_paris)
            e.add("dtend", end_paris)

            details = []
            if lesson.classroom:
                e.add("location", f"Salle {lesson.classroom}")
            if lesson.teacher_name:
                details.append(f"Professeur : {lesson.teacher_name}")

            if details:
                e.add("description", "\n".join(details))

            cal.add_component(e)

    with open("luce.ics", "wb") as f:
        f.write(cal.to_ical())

    print("Fichier luce.ics généré avec succès.")


if __name__ == "__main__":
    main()
