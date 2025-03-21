from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from typing import Optional
from sqlalchemy import select, insert, delete, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from database import get_async_session
from fastapi_cache.decorator import cache
from hashlib import sha256
from datetime import datetime
import time
import uuid
import re
from urllib.parse import urlparse

from auth.users import current_active_user
from auth.db import User
from models import urls, queries
from schemas import URLCreate

router = APIRouter(
    prefix="/links",
    tags=["Links"]
)


# Функция для проверки url
def valid_url(url: str) -> bool:
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


alias_pattern = re.compile(r'^[A-Za-z0-9_-]{1,20}$')

datetime_pattern = re.compile(
    r"^(?P<year>\d{4})-(?P<month>0[1-9]|1[0-2])-(?P<day>0[1-9]|[12]\d|3[01])\s(?P<hour>[01]\d|2[0-3]):(?P<minute>[0-5]\d)$"
)


@router.get("/check_cache")
@cache(expire=60)
async def check_cache():
    time.sleep(3)
    return {"status": "success"}


@router.post("/shorten")
async def shorten_url(
    new_url: URLCreate,
    session: AsyncSession = Depends(get_async_session),
    current_user: Optional[User] = Depends(current_active_user)  # Необязательная авторизация
):
    # Проверка полного url'a
    if not valid_url(new_url.full_url):
        raise HTTPException(status_code=400, detail="Неверный формат URL.")

    # Проверка формата expires_at
    expires_at_dt = None
    if new_url.expires_at:
        if not datetime_pattern.match(new_url.expires_at):
            raise HTTPException(
                status_code=400,
                detail=("Неверный формат expires_at. Ожидается формат YYYY-MM-DD HH:MM.")
            )
        try:
            expires_at_dt = datetime.fromisoformat(new_url.expires_at)
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail="Неверное значение expires_at, не удалось преобразовать в дату."
            ) from e

    # Если задан кастомный alias, валидируем его формат
    if new_url.custom_alias:
        if not alias_pattern.match(new_url.custom_alias):
            raise HTTPException(
                status_code=400,
                detail=("Неверный формат кастомного alias. Разрешены символы A-Z, a-z, 0-9, "
                        "'-' и '_', длина 1-20 символов.")
            )
        short_url = new_url.custom_alias

        # Проверка наличия данного alias'a в базе данных
        query = select(urls).where(urls.c.short_url == short_url)
        result = await session.execute(query)
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail="Указанный alias уже существует."
            )
    else:
        # Если кастосный alias не задан, то делаем 3 попытки посолить и захэшировать ссылку
        for _ in range(3):
            salt = uuid.uuid4().hex
            salted_url = new_url.full_url + salt
            short_url = sha256(salted_url.encode('utf-8')).hexdigest()[:10]
            query = select(urls).where(urls.c.short_url == short_url)
            result = await session.execute(query)
            print("Salted URL:", salted_url)
            print("Generated short_url:", short_url)
            if not result.scalar_one_or_none():
                break
        else:
            raise HTTPException(
                status_code=500,
                detail="Не удалось сгенерировать уникальный короткий URL. Попробуйте повторить запрос позже."
            )

    values = new_url.model_dump(exclude={"custom_alias", "expires_at"})
    values["short_url"] = short_url
    values["creation_time"] = datetime.now()
    values["creator_id"] = current_user.id if current_user else None
    if expires_at_dt:
        values["expires_at"] = expires_at_dt

    statement = insert(urls).values(**values)
    try:
        await session.execute(statement)
        await session.commit()
    except IntegrityError as e:
        await session.rollback()
        raise HTTPException(
            status_code=500,
            detail="Ошибка базы данных при сохранении URL. Попробуйте повторить запрос позже."
        ) from e
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=500,
            detail="Произошла непредвиденная ошибка. Попробуйте повторить запрос позже."
        ) from e

    return {"status": "success", "short_url": short_url}


@router.get("/search")
@cache(expire=60)
async def search_link(
    original_url: str,
    session: AsyncSession = Depends(get_async_session)
):
    query = select(urls).where(urls.c.full_url == original_url)
    result = await session.execute(query)
    records = result.all()

    if not records:
        raise HTTPException(status_code=404, detail="Ссылка не найдена.")

    return [
        {
            "original_url": record.full_url,
            "short_url": record.short_url,
            "creation_time": record.creation_time,
            "expires_at": record.expires_at
        }
        for record in records
    ]


@router.get("/{short_url}")
async def redirect(short_url: str, session: AsyncSession = Depends(get_async_session)):
    query = select(urls).where(urls.c.short_url == short_url)
    result = await session.execute(query)
    record = result.one_or_none()

    if record is None:
        raise HTTPException(status_code=404, detail="Alias не найден.")

    if record.expires_at < datetime.now():
        raise HTTPException(status_code=404, detail="Ссылка больше недоступна.")

    try:
        insert_query = insert(queries).values(
            url_id=record.id,
            full_url=record.full_url,
            short_url=record.short_url,
            access_time=datetime.now()
        )
        await session.execute(insert_query)
        await session.commit()

        return RedirectResponse(url=record.full_url)
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=500,
            detail="Произошла непредвиденная ошибка. Попробуйте повторить запрос позже."
        ) from e


@router.delete("/{short_url}")
async def delete_url(
    short_url: str,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_active_user)  # Обязательная авторизация
):
    query = select(urls).where(urls.c.short_url == short_url)
    result = await session.execute(query)
    record = result.one_or_none()

    if current_user is None:
        raise HTTPException(status_code=403, detail="You should be logged in to do that.")

    if record is None:
        raise HTTPException(status_code=404, detail="Short URL not found.")

    if record.creator_id is not None and record.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized.")

    try:
        stmt = delete(urls).where(urls.c.short_url == short_url)
        await session.execute(stmt)
        await session.commit()

        return {"status": "success", "message": "URL deleted."}
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=500,
            detail="Произошла непредвиденная ошибка. Попробуйте повторить запрос позже."
        ) from e


@router.put("/{short_url}")
async def put_url(
    short_url: str,
    new_alias: Optional[str],
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_active_user)  # Обязательная авторизация
):
    # Получаем запись из базы по текущему короткому URL
    query = select(urls).where(urls.c.short_url == short_url)
    result = await session.execute(query)
    record = result.one_or_none()

    if current_user is None:
        raise HTTPException(status_code=403, detail="You should be logged in to do that.")

    if record is None:
        raise HTTPException(status_code=404, detail="Короткий URL не найден.")

    if record.creator_id is not None and record.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Нет прав для изменения.")

    if new_alias:
        if not alias_pattern.match(new_alias):
            raise HTTPException(
                status_code=400,
                detail=("Неверный формат кастомного alias. Разрешены символы A-Z, a-z, 0-9, "
                        "'-' и '_', длина 1-20 символов.")
            )

        # Проверка наличия данного alias'a в базе данных
        query = select(urls).where(urls.c.short_url == new_alias)
        result = await session.execute(query)
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail="Указанный alias уже существует."
            )
    else:
        # Если кастосный alias не задан, то делаем 3 попытки посолить и захэшировать ссылку
        for _ in range(3):
            salt = uuid.uuid4().hex
            new_alias = sha256(salt.encode('utf-8')).hexdigest()[:10]
            query = select(urls).where(urls.c.short_url == new_alias)
            result = await session.execute(query)
            if not result.scalar_one_or_none():
                break
        else:
            raise HTTPException(
                status_code=500,
                detail="Не удалось сгенерировать уникальный короткий URL. Попробуйте повторить запрос позже."
            )

    # Проверяем, не существует ли уже другой записи с таким новым коротким URL
    query = select(urls).where(urls.c.short_url == new_alias, urls.c.id != record.id)
    result = await session.execute(query)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Указанный alias уже существует.")

    # Подготавливаем данные для обновления записи
    update_data = {}
    update_data["short_url"] = new_alias
    update_data["creation_time"] = datetime.now()

    # Выполняем обновление записи в базе данных
    stmt = update(urls).where(urls.c.id == record.id).values(**update_data)
    try:
        await session.execute(stmt)
        await session.commit()
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Произошла непредвиденная ошибка. Попробуйте повторить запрос позже. {str(e)}"
        ) from e

    return {"status": "success", "short_url": new_alias}


@router.get("/expired/stats")
@cache(expire=60)
async def get_expired_links_stats(
    session: AsyncSession = Depends(get_async_session)
):
    # Получаем все просроченные ссылки (где expires_at меньше текущего времени)
    query = select(urls).where(urls.c.expires_at < datetime.now())
    result = await session.execute(query)
    expired_links = result.all()

    stats_list = []
    try:
        for link in expired_links:
            stats_query = select(
                func.count(queries.c.id).label("access_count"),
                func.max(queries.c.access_time).label("last_access")
            ).where(queries.c.url_id == link.id)
            stats_result = await session.execute(stats_query)
            stats = stats_result.one()

            stats_list.append({
                "original_url": link.full_url,
                "creation_time": link.creation_time,
                "access_count": stats.access_count,
                "last_access": stats.last_access
            })
        return stats_list

    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Произошла непредвиденная ошибка. Попробуйте повторить запрос позже. {str(e)}"
        ) from e


@router.get("/{short_url}/stats")
@cache(expire=60)
async def get_link_stats(
    short_url: str,
    session: AsyncSession = Depends(get_async_session)
):
    query = select(urls).where(urls.c.short_url == short_url)
    result = await session.execute(query)
    record = result.one_or_none()

    if record is None:
        raise HTTPException(status_code=404, detail="Короткий URL не найден.")

    try:
        query = select(
            func.count(queries.c.id).label("access_count"),
            func.max(queries.c.access_time).label("last_access")
        ).where(queries.c.url_id == record.id)
        result = await session.execute(query)
        stats = result.one()

        return {
            "original_url": record.full_url,
            "creation_time": record.creation_time,
            "access_count": stats.access_count,
            "last_access": stats.last_access
        }
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Произошла непредвиденная ошибка. Попробуйте повторить запрос позже. {str(e)}"
        ) from e
