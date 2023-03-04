import datetime
from dataclasses import dataclass
from typing import Optional

from .vk_object_data import VKOwnedObjectData


@dataclass
class PhotoAlbumData(VKOwnedObjectData):
    """ """

    id: int  # идентификатор альбома;
    owner_id: int  # идентификатор владельца альбома;
    thumb_id: int  # идентификатор фотографии, которая является обложкой (0, если обложка отсутствует);
    title: str  # название альбома;
    description: Optional[str]  # описание альбома; (не приходит для системных альбомов)
    created: Optional[datetime.datetime]
    # дата создания альбома в формате unixtime; (не приходит для системных альбомов);

    updated: Optional[datetime.datetime]
    # дата последнего обновления альбома в формате unixtime; (не приходит для системных альбомов);

    size: int  # количество фотографий в альбоме;
    can_upload: Optional[bool]
    # 1, если текущий пользователь может загружать фотографии в альбом (при запросе информации об альбомах сообщества);

    privacy_view: Optional[dict]
    # настройки приватности для альбома в формате настроек приватности (только для альбома пользователя, не приходит
    # для системных альбомов);

    privacy_comment: Optional[dict]
    # настройки приватности для альбома в формате настроек приватности (только для альбома пользователя, не приходит
    # для системных альбомов);

    upload_by_admins_only: Optional[bool]
    # кто может загружать фотографии в альбом (только для альбома сообщества, не приходит для системных альбомов);

    comments_disabled: Optional[bool]
    # отключено ли комментирование альбома (только для альбома сообщества, не приходит для системных альбомов);

    thumb_src: Optional[str]  # ссылка на изображение обложки альбома (если был указан параметр need_covers).

    user_id: Optional[int]  # идентификатор пользователя, загрузившего фото (если фотография размещена в сообществе).
    # Для фотографий, размещенных от имени сообщества, user_id = 100.
