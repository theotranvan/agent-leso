"""Clients Supabase (admin + user) et wrapper Storage."""
from functools import lru_cache

from supabase import Client, create_client

from app.config import settings


@lru_cache
def get_supabase_admin() -> Client:
    """Client service_role - BYPASS RLS. À n'utiliser qu'en système."""
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


def get_supabase_user(access_token: str) -> Client:
    """Client authentifié JWT - respecte RLS."""
    client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
    client.postgrest.auth(access_token)
    return client


class SupabaseStorage:
    """Wrapper du bucket privé Supabase."""

    def __init__(self):
        self.client = get_supabase_admin()
        self.bucket = settings.SUPABASE_STORAGE_BUCKET

    def upload(self, path: str, file_bytes: bytes, content_type: str = "application/octet-stream") -> str:
        self.client.storage.from_(self.bucket).upload(
            path=path, file=file_bytes,
            file_options={"content-type": content_type, "upsert": "true"},
        )
        return path

    def download(self, path: str) -> bytes:
        return self.client.storage.from_(self.bucket).download(path)

    def get_signed_url(self, path: str, expires_in: int = 3600) -> str:
        resp = self.client.storage.from_(self.bucket).create_signed_url(path, expires_in)
        return resp.get("signedURL") if isinstance(resp, dict) else resp.get("signedURL", "")

    def delete(self, path: str) -> None:
        self.client.storage.from_(self.bucket).remove([path])


@lru_cache
def get_storage() -> SupabaseStorage:
    return SupabaseStorage()
