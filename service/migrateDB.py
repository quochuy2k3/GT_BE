import asyncio
from typing import Optional

from beanie import init_beanie, PydanticObjectId
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic_settings import BaseSettings
from models import Routine  # Đảm bảo Routine được import đúng


class Settings(BaseSettings):
    DATABASE_URL: str = "mongodb://root:password@localhost:27017/glowTrack?authSource=admin"
    DB_NAME: str = "glowTrack"

    class Config:
        env_file = ".env.docker-compose"
        from_attributes = True


async def migrate_session_ids(dry_run: bool = False, verbose: bool = True):
    settings = Settings()
    client = AsyncIOMotorClient(settings.DATABASE_URL)

    await init_beanie(database=client[settings.DB_NAME], document_models=[Routine])

    routines = await Routine.find_all().to_list()
    updated_routines = 0
    total_sessions_added = 0

    for routine in routines:
        modified = False
        sessions_added = 0

        for day in routine.days:
            for session in day.sessions:
                # ❌ Bỏ qua nếu không có bước nào
                if not session.steps or len(session.steps) == 0:
                    continue

                # ✅ Chỉ thêm id nếu cần
                if session.model_dump().get("id") is None:
                    session.id = PydanticObjectId()
                    modified = True
                    sessions_added += 1
                    if verbose:
                        print(f"↪︎ Added ID to session at {session.time} in routine '{routine.routine_name}'")

        if modified:
            updated_routines += 1
            total_sessions_added += sessions_added

            if verbose:
                print(f"🛠 Routine `{routine.routine_name}` updated with {sessions_added} session.id(s)")

            if not dry_run:
                await routine.save()

    print("\n✅ Migration Summary")
    print("────────────────────")
    print(f"📄 Routines scanned: {len(routines)}")
    print(f"🧩 Routines updated: {updated_routines}")
    print(f"🆔 Total session.id added: {total_sessions_added}")
    if dry_run:
        print("⚠️ DRY RUN mode — no data was modified")


if __name__ == "__main__":
    # 👉 Chạy dry run trước để test, đổi thành False khi muốn cập nhật thật
    asyncio.run(migrate_session_ids(dry_run=False, verbose=True))
