import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from app.config import SCOPES

def get_google_calendar_service():
    creds = None
    token_path = '/data/token.json' if os.path.exists('/data') else 'token.json'
    credentials_path = '/data/credentials.json' if os.path.exists('/data/credentials.json') else 'credentials.json'
    
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(credentials_path):
                print("⚠️ Файл credentials.json не найден!")
                return None
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
    return build('calendar', 'v3', credentials=creds)

def add_event_to_google(title: str, start_dt_str: str, end_dt_str: str, is_timeless: bool, user_tz: str) -> str:
    try:
        service = get_google_calendar_service()
        if not service: return None
        user_zone = ZoneInfo(user_tz)
        event_body = {
            'summary': title,
            'description': 'Создано автоматически через Telegram ToDo Bot',
            'reminders': {'useDefault': False, 'overrides': [{'method': 'popup', 'minutes': 15}]}
        }
        if is_timeless or not start_dt_str:
            base_date = datetime.strptime(start_dt_str[:10], "%Y-%m-%d") if start_dt_str else datetime.now(user_zone)
            event_body['start'] = {'date': base_date.strftime("%Y-%m-%d")}
            event_body['end'] = {'date': (base_date + timedelta(days=1)).strftime("%Y-%m-%d")}
        else:
            start_local = datetime.strptime(start_dt_str, "%Y-%m-%d %H:%M")
            end_local = datetime.strptime(end_dt_str, "%Y-%m-%d %H:%M") if end_dt_str else start_local + timedelta(hours=1)
            event_body['start'] = {'dateTime': start_local.strftime("%Y-%m-%dT%H:%M:%S"), 'timeZone': user_tz}
            event_body['end'] = {'dateTime': end_local.strftime("%Y-%m-%dT%H:%M:%S"), 'timeZone': user_tz}
        created_event = service.events().insert(calendarId='primary', body=event_body).execute()
        return created_event.get('id')
    except Exception as e:
        print(f"❌ Ошибка создания в Google: {e}")
        return None

def update_event_in_google(event_id: str, new_title: str):
    if not event_id: return
    try:
        service = get_google_calendar_service()
        if not service: return
        event = service.events().get(calendarId='primary', eventId=event_id).execute()
        event['summary'] = new_title
        service.events().update(calendarId='primary', eventId=event_id, body=event).execute()
    except Exception as e: print(f"❌ Ошибка обновления в Google: {e}")

def delete_event_from_google(event_id: str):
    if not event_id: return
    try:
        service = get_google_calendar_service()
        if not service: return
        service.events().delete(calendarId='primary', eventId=event_id).execute()
    except Exception as e: print(f"❌ Ошибка удаления из Google: {e}")
