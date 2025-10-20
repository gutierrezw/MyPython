from Library_python import (
datetime,
timedelta,
os,
Request,
Credentials,
InstalledAppFlow,
build,
HttpError,
)
from Library_utils import define_FileCache, delete_file

SCOPES = ["https://www.googleapis.com/auth/calendar"]

class GoogleCalendarManager:
    def __init__(self):
        self.service = self._authenticate()
        self.DEFAULT_TIMEZONE = "America/Argentina/Buenos_Aires"
        SCOPES = ["https://www.googleapis.com/auth/calendar"]

    def _authenticate(self):
        creds = None

        filetoken = define_FileCache(name="token.json")
        fileCredetials = define_FileCache(name="credentials.json")

        if os.path.exists(filetoken):
            creds = Credentials.from_authorized_user_file(filetoken, SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(fileCredetials, SCOPES)
                creds = flow.run_local_server(port=0)

            # Save the credentials for the next run
            with open("token.json", "w") as token:
                token.write(creds.to_json())

        return build("calendar", "v3", credentials=creds)

    def list_upcoming_events(self, max_results=10):
        now = datetime.utcnow().isoformat() + "Z"
        tomorrow = (datetime.now() + timedelta(days=5)).replace(hour=23, minute=59, second=0, microsecond=0).isoformat() + "Z"

        events_result = self.service.events().list(
            calendarId='primary', timeMin=now, timeMax=tomorrow,
            maxResults=max_results, singleEvents=True,
            orderBy='startTime'
        ).execute()
        events = events_result.get('items', [])

        if not events:
            print('No upcoming events found.')
        else:
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                print(start, event['summary'],event['id'])
        
        return events

    def create_event(self, summary, start_time, end_time, timezone=None, attendees=None):
        event = {
            'summary': summary,
            'start': {
                'dateTime': start_time,
                'timeZone': self.DEFAULT_TIMEZONE,
            },
            'end': {
                'dateTime': end_time,
                'timeZone': self.DEFAULT_TIMEZONE,
            }
        }

        if attendees:
            event["attendees"] = [{"email": email} for email in attendees]

        try:
            event = self.service.events().insert(calendarId="primary", body=event).execute()
            print(f"Event created: {event.get('htmlLink')}")
        except HttpError as error:
            print(f"An error has occurred: {error}")

    def update_event(self, event_id, summary=None, start_time=None, end_time=None):
        event = self.calendar_service.events().get(calendarId='primary', eventId=event_id).execute()

        if summary:
            event['summary'] = summary

        if start_time:
            event['start']['dateTime'] = start_time.strftime('%Y-%m-%dT%H:%M:%S')

        if end_time:
            event['end']['dateTime'] = end_time.strftime('%Y-%m-%dT%H:%M:%S')

        updated_event = self.calendar_service.events().update(
            calendarId='primary', eventId=event_id, body=event).execute()
        return updated_event

    def delete_event(self, event_id):
        self.calendar_service.events().delete(calendarId='primary', eventId=event_id).execute()
        return True
    

calendar = GoogleCalendarManager()

calendar.list_upcoming_events()

calendar.create_event(summary=f"Le recordamos que tiene cita {"Depilación"} sede San Juan",
                      start_time="2025-10-21T16:30:00+02:00",
                      end_time="2025-10-21T17:30:00+02:00",
                      attendees=["gutierrez.madrid.wilmer@gmail.com"])
