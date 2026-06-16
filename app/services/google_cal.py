import os
import json
import asyncio
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from app.config import SCOPES
from app.database.requests import get_google_token, update_google_token

CREDENTIALS_PATH = '/data/credentials.json' if os.path.exists('/data/credentials.json') else 'credentials.json'

def get_oauth_flow(redirect_uri: str):
    if not os.path.exists(CREDENTIALS_PATH):
        return None
    flow = Flow.from_client_secrets_file(
        CREDENTIALS_PATH,
        scopes=SCOPES,
        redirect_uri=redirect_uri
    )
    return flow

async def get_google_calendar_service(user_id: int):
    token_json_str = await get_google_token(user_id)
    if not token_json_str:
        return None
        
    creds_data = json.loads(token_json_str)
    creds = Credentials.from_authorized_user_info(creds_data, SCOPES)
    
    if creds and creds.expired and creds.refresh_token:
        try:
            await asyncio.to_thread(creds.refresh, Request())
            await update_google_token(user_id, creds.to_json())
        except Exception as e:
            print(f"Error refreshing token for user {user_id}: {e}")
            return None
            
    if not creds.valid:
        return None
        
    return build('calendar', 'v3', credentials=creds)

async def add_event_to_google(user_id: int, title: str, start_dt_str: str, end_dt_str: str, is_timeless: bool, user_tz: str) -> str:
    service = await get_google_calendar_service(user_id)
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
        
    def _insert():
        return service.events().insert(calendarId='primary', body=event_body).execute()
        
    try:
        created_event = await asyncio.to_thread(_insert)
        return created_event.get('id')
    except Exception as e:
        print(f"❌ Ошибка создания в Google для {user_id}: {e}")
        return None

async def update_event_in_google(user_id: int, event_id: str, new_title: str):
    if not event_id: return
    service = await get_google_calendar_service(user_id)
    if not service: return
    
    def _update():
        event = service.events().get(calendarId='primary', eventId=event_id).execute()
        event['summary'] = new_title
        service.events().update(calendarId='primary', eventId=event_id, body=event).execute()
        
    try:
        await asyncio.to_thread(_update)
    except Exception as e:
        print(f"❌ Ошибка обновления в Google: {e}")

async def delete_event_from_google(user_id: int, event_id: str):
    if not event_id: return
    service = await get_google_calendar_service(user_id)
    if not service: return
    
    def _delete():
        service.events().delete(calendarId='primary', eventId=event_id).execute()
        
    try:
        await asyncio.to_thread(_delete)
    except Exception as e:
        print(f"❌ Ошибка удаления из Google: {e}")
