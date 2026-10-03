from zoneinfo import ZoneInfo
import datetime
import os
from ics import Calendar, Event
import pronotepy
import pronotepy.ent

# Récupération des secrets injectés par GitHub Actions
PRONOTE_URL = os.environ.get("PRONOTE_URL")
USERNAME = os.environ.get("PRONOTE_USERNAME")
PASSWORD = os.environ.get("PRONOTE_PASSWORD")
ENT = pronotepy.ent.ent_ecollege78
CHILD_NAME = "Luce"


def main():
    if not all([PRONOTE_URL, USERNAME, PASSWORD]):
        print("Erreur : secrets manquants dans l'environnement.")
        return

    print("Connexion à Pronote...")
    client = pronotepy.ParentClient(
        PRONOTE_URL, username=USERNAME, password=PASSWORD, ent=ENT
    )

    if not client.logged_in:
        print("Échec de connexion.")
        return

    # Sélection de Luce
    children = [
        c for c in client.children if CHILD_NAME.lower() in c.name.lower()
    ]
    target_child = children[0] if children else client.children[0]
    client.set_child(target_child)

    cal = Calendar()
    today = datetime.date.today()

    # Extraction sur les 7 prochains jours
    for i in range(7):
        day = today + datetime.timedelta(days=i)
        lessons = client.lessons(day)

        # Définition du fuseau horaire français
        tz_paris = ZoneInfo("Europe/Paris")

        for lesson in sorted(lessons, key=lambda x: x.start):
            if lesson.canceled:
                continue

            e = Event()
            e.name = lesson.subject.name
        
            # Retirer le fuseau horaire (tzinfo) pour garder l'heure exacte locale
            e.begin = lesson.start.replace(tzinfo=None)
            e.end = lesson.end.replace(tzinfo=None)
        
            details = []
            if lesson.classroom:
                e.location = f"Salle {lesson.classroom}"
            if lesson.teacher_name:
                details.append(f"Professeur : {lesson.teacher_name}")
        
            if details:
                e.description = "\n".join(details)
        
            cal.events.add(e)
    # Sauvegarde directe à la racine du dépôt
    filepath = "luce.ics"

    with open(filepath, "w", encoding="utf-8") as f:
        f.writelines(cal.serialize_iter())

    print(f"Fichier ICS généré avec succès : {filepath}")


if __name__ == "__main__":
    main()
