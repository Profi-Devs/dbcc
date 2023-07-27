import asyncio
from typing import Any, Union

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient

from dbcc.base import TableEngine

mongo = None


def remove_id(payload: dict):
    if "_id" in payload:
        del payload["_id"]


class MongoTableEngine(TableEngine):
    db: Any = None
    collection: Any = None

    def __init__(self, url: str, db_name: str, collection_name: str = None):
        super().__init__(url, db_name, collection_name)
        global mongo
        if not mongo:
            mongo = AsyncIOMotorClient(
                url, connect=False
            )  # , tls=True, tlsAllowInvalidCertificates=True)
            mongo.get_io_loop = asyncio.get_event_loop
        self.db = mongo[self.db_name]
        if collection_name:
            self.collection = self.db[collection_name]

    def __getitem__(self, key):
        return MongoTableEngine(self.url, self.db_name, key)

    async def find_batch(self, pattern: dict = None, skip: int = None, limit: int = None, sort: list = None) -> list:
        pattern = pattern if pattern else {}
        routine = self.collection.find(pattern)
        if sort:
            routine = routine.sort(sort)
        if limit:
            routine = routine.limit(limit)
        if skip:
            routine = routine.skip(skip)
        return [entity async for entity in routine]

    async def create(self, entry: dict) -> dict:
        inserted_id = (await self.collection.insert_one(entry)).inserted_id
        await self.update_by_id(inserted_id, {"id": str(inserted_id)})
        entry["id"] = str(inserted_id)
        return entry

    async def update_by_id(self, id: Union[str, ObjectId], payload: dict):
        remove_id(payload)
        return await self.collection.update_one({"_id": ObjectId(id)}, {"$set": payload})

    async def delete_by_id(self, id: Union[str, ObjectId]):
        await self.collection.delete_one({"_id": ObjectId(id)})

    async def find_single(self, field: str, value):
        return await self.collection.find_one({field: value})