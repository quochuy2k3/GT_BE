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


async def test_push_token():
    settings = Settings()
    client = AsyncIOMotorClient(settings.DATABASE_URL)

    # Initialize database connection with only the User model
    await init_beanie(database=client.get_default_database(), document_models=[User])

    # Find first user
    users = await User.find_all().limit(1).to_list()
    if not users:
        print("No users found in the database.")
        return
    
    user = users[0]
    print(f"User before update: {user.email}, push_token={user.push_token}")
    
    # Update push token
    test_token = "test_token_" + user.email
    user.push_token = test_token
    await user.save()
    
    # Fetch user again to confirm changes were saved
    updated_user = await User.get(user.id)
    print(f"User after update: {updated_user.email}, push_token={updated_user.push_token}")
    
    # Verify the token was saved
    if updated_user.push_token == test_token:
        print("✅ SUCCESS: Push token was successfully saved!")
    else:
        print("❌ ERROR: Push token was not saved correctly.")
        print(f"  Expected: {test_token}")
        print(f"  Got: {updated_user.push_token}")


if __name__ == "__main__":
    asyncio.run(test_push_token()) 