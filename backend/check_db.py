import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import pprint

async def main():
    client = AsyncIOMotorClient('mongodb://localhost:27017')
    db = client['lifeos']
    user = await db.users.find_one()
    pprint.pprint(user.get('google_tokens', {}))

if __name__ == '__main__':
    asyncio.run(main())
