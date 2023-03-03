from abc import ABCMeta, abstractmethod
from typing import List, Optional

from pydantic import BaseModel
from pydantic.utils import deep_update

from .db import get_async_firestore_client, in_memory_session


class BaseRepository(metaclass=ABCMeta):
    @abstractmethod
    async def get_by_id(self, item_id: str) -> Optional[BaseModel]:
        pass

    @abstractmethod
    async def save(self, item: BaseModel) -> BaseModel:
        pass

    @abstractmethod
    async def update(self, updated_item: BaseModel) -> BaseModel:
        pass

    @abstractmethod
    async def delete(self, item_id: str) -> None:
        pass


class InMemoryRepository(BaseRepository):
    def __init__(self, item_id: str, table: str, DB_BASE_MODEL: BaseModel) -> None:
        self.item_id = item_id
        self.table = table
        self.DB_BASE_MODEL = DB_BASE_MODEL
        self.session = in_memory_session[self.table]

    async def get_by_id(self, item_id: str) -> Optional[BaseModel]:
        item = self.session.get(item_id, None)
        return self.DB_BASE_MODEL(**item) if item else None

    async def save(self, item: BaseModel) -> BaseModel:
        item_dict = item.dict()
        self.session[item_dict[str(self.item_id)]] = item_dict
        return item

    async def get_many_by_id(self, item_ids: List[str]) -> List[BaseModel]:
        return [self.DB_BASE_MODEL(**self.session[item_id]) for item_id in item_ids]

    async def update(self, updated_item: BaseModel) -> BaseModel:
        item_id = str(updated_item.dict()[self.item_id])
        old_item = self.DB_BASE_MODEL.from_orm(await self.get_by_id(item_id))
        updated_data = updated_item.dict(exclude_unset=True)
        updated_item = self.DB_BASE_MODEL(**deep_update(old_item.dict(), updated_data))
        await self.save(updated_item)
        return updated_item

    async def delete(self, item_id: str) -> None:
        await self.session.pop(item_id, None)


class AsyncFirestoreRepository(BaseRepository):
    def __init__(self, item_id: str, table: str, DB_BASE_MODEL: BaseModel) -> None:
        self.item_id = item_id
        self.table = table
        self.DB_BASE_MODEL = DB_BASE_MODEL
        self.client = get_async_firestore_client()
        self.session = self.client.collection(self.table)

    async def get_by_id(self, item_id: str) -> Optional[BaseModel]:
        item = await self.session.document(item_id).get()
        print(item.to_dict())
        return self.DB_BASE_MODEL(**item.to_dict()) if item.exists else None

    async def save(self, item: BaseModel) -> BaseModel:
        item = item.dict()
        await self.session.document(item.pop(self.item_id)).set(item)
        return item

    async def update(self, updated_item: BaseModel) -> BaseModel:
        # TODO implement
        return updated_item

    async def delete(self, item_id: str) -> None:
        await self.session.document(item_id).delete()