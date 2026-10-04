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
ICS_URL = os.getenv("ICS_URL")  # URL publique GitHub Pages (ex: https://<pseudo>.github.io/<repo>/luce.ics)

PARIS_TZ = ZoneInfo("Europe/Paris")


def send_free_sms(message: str):
    """Envoie un SMS via l'API Free Mobile."""
    if not FREE_USER or not FREE_PASS:
        print("Identifiants Free Mobile manquants, envoi SMS ignoré.")
        return

    url = "https://smsapi.free-mobile.fr/sendmsg"
    params = {"user": FREE_USER, "pass": FREE_PASS, "msg": message}
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            print("SMS d'alerte envoyé avec succès.")
        else:
            print(f"Échec envoi SMS (code HTTP {response.status_code}): {response.text}")
    except Exception as e:
        print(f"Erreur lors de l'envoi du SMS : {e}")


def load_previous_events(file_path="luce.ics", url=None):
    """Charge les événements du fichier .ics précédent (local ou distant)."""
    content = None

    # 1. Essayer de lire le fichier local s'il existe
    if os.path.exists(file_path):
        try:
            with open(file_path, "rb") as f:
                content = f.read()
        except Exception as e:
            print(f"Erreur de lecture du fichier local {file_path} : {e}")

    # 2. Si pas de fichier local, tenter le téléchargement via l'URL GitHub Pages
    if not content and url:
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                content = resp.content
        except Exception as e:
            print(f"Impossible de récupérer l'ancien .ics via l'URL : {e}")

    if not content:
        return {}

    events = {}
    try:
        cal = Calendar.from_ical(content)
        for component in cal.walk():
            if component.name == "VEVENT":
                dtstart = component.get("dtstart").dt
                dtend = component.get("dtend").dt

                # Normalisation des fuseaux horaires vers Europe/Paris
                if isinstance(dtstart, datetime.datetime):
                    dtstart = dtstart.replace(tzinfo=PARIS_TZ) if dtstart.tzinfo is None else dtstart.astimezone(PARIS_TZ)
                if isinstance(dtend, datetime.datetime):
                    dtend = dtend.replace(tzinfo=PARIS_TZ) if dtend.tzinfo is None else dtend.astimezone(PARIS_TZ)

                summary = str(component.get("summary", ""))
                location = str(component.get("location", ""))
                description = str(component.get("description", ""))

                events[(dtstart, dtend)] = {
                    "summary": summary,
                    "location": location,
                    "description": description,
                    "start": dtstart,
                    "end": dtend,
                }
    except Exception as e:
        print(f"Erreur d'analyse de l'ancien fichier .ics : {e}")

    return events


def compare_schedules(old_events, new_events, today):
    """Compare l'ancien emploi du temps et le nouveau sur la fenêtre de 7 jours."""
    if not old_events:
        return []

    today_start = datetime.datetime.combine(today, datetime.time.min, tzinfo=PARIS_TZ)
    window_end = datetime.datetime.combine(today + datetime.timedelta(days=7), datetime.time.max, tzinfo=PARIS_TZ)

    changes = []

    # 1. Vérifier les cours annulés ou modifiés
    for key, old_item in old_events.items():
        start, end = key
        if not (today_start <= start <= window_end):
            continue

        if key not in new_events:
            date_str = start.strftime("%d/%m à %Hh%M")
            changes.append(f"❌ Annulé : {old_item['summary']} ({date_str})")
        else:
            new_item = new_events[key]
            diffs = []
            if old_item["summary"] != new_item["summary"]:
                diffs.append(f"Matière: {old_item['summary']} -> {new_item['summary']}")
            if old_item["location"] != new_item["location"]:
                old_loc = old_item["location"] or "sans salle"
                new_loc = new_item["location"] or "sans salle"
                diffs.append(f"Salle: {old_loc} -> {new_loc}")

            if diffs:
                date_str = start.strftime("%d/%m à %Hh%M")
                changes.append(f"✏️ Modifié ({date_str}) : {new_item['summary']} ({', '.join(diffs)})")

    # 2. Vérifier les nouveaux cours ajoutés
    for key, new_item in new_events.items():
        start, end = key
        if key not in old_events:
            date_str = start.strftime("%d/%m à %Hh%M")
            loc_str = f" ({new_item['location']})" if new_item["location"] else ""
            changes.append(f"➕ Ajouté : {new_item['summary']} ({date_str}){loc_str}")

    return changes


def main():
    if not all([PRONOTE_URL, USERNAME, PASSWORD]):
        print("Erreur : secrets Pronote manquants.")
        return

    # Charger l'ancien emploi du temps pour comparaison
    old_events = load_previous_events("luce.ics", url=ICS_URL)

    client = pronotepy.ParentClient(
        PRONOTE_URL, username=USERNAME, password=PASSWORD, ent=ENT
    )
    if not client.logged_in:
        print("Échec de connexion à Pronote.")
        return

    children = [c for c in client.children if CHILD_NAME.lower() in c.name.lower()]
    target_child = children[0] if children else client.children[0]
    client.set_child(target_child)

    cal = Calendar()
    cal.add("prodid", "-//Pronote Calendar//FR")
    cal.add("version", "2.0")
    cal.add("x-wr-timezone", "Europe/Paris")

    today = datetime.date.today()
    new_events = {}

    for i in range(7):
        day = today + datetime.timedelta(days=i)
        lessons = client.lessons(day)

        for lesson in sorted(lessons, key=lambda x: x.start):
            if lesson.canceled:
                continue

            e = Event()
            e.add("summary", lesson.subject.name)

            start_dt = lesson.start
            end_dt = lesson.end

            start_paris = start_dt.replace(tzinfo=PARIS_TZ) if start_dt.tzinfo is None else start_dt.astimezone(PARIS_TZ)
            end_paris = end_dt.replace(tzinfo=PARIS_TZ) if end_dt.tzinfo is None else end_dt.astimezone(PARIS_TZ)

            e.add("dtstart", start_paris)
            e.add("dtend", end_paris)

            details = []
            location_str = ""
            if lesson.classroom:
                location_str = f"Salle {lesson.classroom}"
                e.add("location", location_str)
            if lesson.teacher_name:
                details.append(f"Professeur : {lesson.teacher_name}")

            if details:
                e.add("description", "\n".join(details))

            cal.add_component(e)

            # Enregistrer dans notre dictionnaire pour comparaison
            new_events[(start_paris, end_paris)] = {
                "summary": lesson.subject.name,
                "location": location_str,
                "description": "\n".join(details) if details else "",
                "start": start_paris,
                "end": end_paris,
            }

    # Comparer l'ancien et le nouvel emploi du temps
    if old_events:
        changes = compare_schedules(old_events, new_events, today)
        if changes:
            print(f"{len(changes)} modification(s) détectée(s).")
            sms_body = f"[Pronote {CHILD_NAME}] Changement EDT :\n" + "\n".join(changes)
            send_free_sms(sms_body)
        else:
            print("Aucune modification détectée.")
    else:
        print("Aucun fichier .ics antérieur trouvé. Initialisation sans alerte SMS.")

    # Enregistrer le nouveau fichier .ics
    with open("luce.ics", "wb") as f:
        f.write(cal.to_ical())

    print("Fichier luce.ics généré avec succès.")


if __name__ == "__main__":
    main()
