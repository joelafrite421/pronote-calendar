import datetime
import os
from zoneinfo import ZoneInfo
from icalendar import Calendar, Event
import pronotepy
import pronotepy.ent

PRONOTE_URL = os.environ.get("PRONOTE_URL")
USERNAME = os.environ.get("PRONOTE_USERNAME")
PASSWORD = os.environ.get("PRONOTE_PASSWORD")
ENT = pronotepy.ent.ent_ecollege78
CHILD_NAME = "Luce"


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

    today = datetime.date.today()

    for i in range(7):
        day = today + datetime.timedelta(days=i)
        lessons = client.lessons(day)

        for lesson in sorted(lessons, key=lambda x: x.start):
            if lesson.canceled:
                continue

            # Création systématique de l'événement
            e = Event()
            e.add("summary", lesson.subject.name)

            # Correction du décalage horaire (+2h observées dans les tests précédents)
            # On retire 2 heures à la valeur transmise par pronotepy pour obtenir 09:20 au lieu de 11:20
            dtstart_corrected = lesson.start.replace(tzinfo=None) - datetime.timedelta(hours=2)
            dtend_corrected = lesson.end.replace(tzinfo=None) - datetime.timedelta(hours=2)

            e.add("dtstart", dtstart_corrected)
            e.add("dtend", dtend_corrected)

            details = []
            if lesson.classroom:
                e.add("location", f"Salle {lesson.classroom}")
            if lesson.teacher_name:
                details.append(f"Professeur : {lesson.teacher_name}")

            if details:
                e.add("description", "\n".join(details))

            # Ajout à l'intérieur de la boucle
            cal.add_component(e)

    with open("luce.ics", "wb") as f:
        f.write(cal.to_ical())

    print("Fichier luce.ics généré avec succès.")


if __name__ == "__main__":
    main()
