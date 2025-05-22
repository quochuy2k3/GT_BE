import asyncio
import os
import sys
from typing import Optional

# Add the project root directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient
from config.config import Settings
from models.user import User


async def migrate_push_token(dry_run: bool = False, verbose: bool = True):
    settings = Settings()
    client = AsyncIOMotorClient(settings.DATABASE_URL)

    # Initialize database connection with only the User model
    await init_beanie(database=client.get_default_database(), document_models=[User])

    # Find all users
    users = await User.find_all().to_list()
    updated_users = 0

    for user in users:
        modified = False
        
        # Check if push_token is missing (None or doesn't exist)
        if user.push_token is None:
            user.push_token = ""  # Initialize with empty string
            modified = True
            
            if verbose:
                print(f"↪︎ Adding push_token field to user: {user.email}")

        if modified:
            updated_users += 1
            
            if verbose:
                print(f"🛠 User `{user.email}` updated with push_token field")

            if not dry_run:
                await user.save()
                if verbose:
                    print(f"✓ Changes saved for user {user.email}")

    print("\n✅ Migration Summary")
    print("────────────────────")
    print(f"📄 Users scanned: {len(users)}")
    print(f"🧩 Users updated: {updated_users}")
    if dry_run:
        print("⚠️ DRY RUN mode — no data was modified")
    else:
        print("✅ Migration completed successfully!")


if __name__ == "__main__":
    # Run with dry_run=False to actually make the changes
    asyncio.run(migrate_push_token(dry_run=False, verbose=True)) 