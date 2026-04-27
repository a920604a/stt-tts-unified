from ..database import get_db


class SettingsService:
    async def get(self, key: str, default: str | None = None) -> str | None:
        async with get_db() as db:
            async with db.execute(
                "SELECT value FROM app_settings WHERE key = ?", (key,)
            ) as cursor:
                row = await cursor.fetchone()
                return row["value"] if row else default

    async def set(self, key: str, value: str) -> None:
        async with get_db() as db:
            await db.execute(
                "INSERT OR REPLACE INTO app_settings (key, value) VALUES (?, ?)",
                (key, value),
            )
            await db.commit()

    async def get_all(self) -> dict[str, str]:
        async with get_db() as db:
            async with db.execute("SELECT key, value FROM app_settings") as cursor:
                rows = await cursor.fetchall()
                return {row["key"]: row["value"] for row in rows}


settings_service = SettingsService()
