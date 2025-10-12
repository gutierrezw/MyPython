from Library_python import (
    datetime,
    os,
    sys,
    Request,
    Credentials,
    InstalledAppFlow,
    build,
)

sys.path.append(r"C:\Users\InversionesWildaga\Documents\MyPython\AppOliday")


# Permisos que pedimos al usuario
SCOPES = ["https://www.googleapis.com/auth/calendar"]


def get_calendar_service():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    service = build("calendar", "v3", credentials=creds)
    return service


def add_event(summary, start_time, end_time):
    service = get_calendar_service()
    event = {
        "summary": summary,
        "start": {"dateTime": start_time, "timeZone": "America/Argentina/Buenos_Aires"},
        "end": {"dateTime": end_time, "timeZone": "America/Argentina/Buenos_Aires"},
    }
    event = service.events().insert(calendarId="primary", body=event).execute()
    print(f"Evento creado: {event.get('htmlLink')}")


if __name__ == "__main__":
    inicio = "2025-10-12T14:00:00-03:00"
    fin = "2025-10-12T15:00:00-03:00"
    add_event("Masaje Descontracturante - Cliente Juan Pérez", inicio, fin)
