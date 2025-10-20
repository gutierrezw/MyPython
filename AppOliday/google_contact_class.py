from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import os, pickle

SCOPES = ['https://www.googleapis.com/auth/contacts.readonly']

def get_google_contacts():
    creds = None
    if os.path.exists('token_people.pickle'):
        with open('token_people.pickle', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token_people.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('people', 'v1', credentials=creds)
    results = service.people().connections().list(
        resourceName='people/me',
        pageSize=2000,
        personFields='names,phoneNumbers,emailAddresses'
    ).execute()
    connections = results.get('connections', [])

    contactos = []
    for person in connections:
        nombres = person.get('names', [])
        telefonos = person.get('phoneNumbers', [])
        emails = person.get('emailAddresses', [])
        if nombres and telefonos:
            contactos.append({
                'nombre': nombres[0].get('displayName'),
                'telefono': telefonos[0].get('value'),
                'email': emails[0].get('value') if emails else None
            })
    return contactos
