from datetime import datetime
from pathlib import Path

from vk_cli import api

from .data import PhotoData
from .vk_object import VKobjectOwned


class VKPhoto(VKobjectOwned):
    """
    Фотография ВК. Представление фотографии на сайте vk.com
    """

    vk_object_type = 'photo'
    vk_data_class = PhotoData

    size_vars = (2560, 1280, 807, 604, 130, 75)
    size_vars_old = ('w', 'z', 'y', 'x', 'm', 's')

    vk_data: PhotoData | None

    def _get_vk_data(self) -> dict:
        request = api.photos.get_by_id(photos=self.string_id, photo_sizes=None, extended=True)
        result = request.get_invoke_result()
        return result.single

    def __repr__(self) -> str:
        return self.url

    @property
    def url(self) -> str:
        url_base = 'https://vk.com/photo'
        return f'{url_base}{self.owner_id}_{self.id}'

    @property
    def sizes(self):
        """
        image variants sizes dict
        :return:
        """
        return {i.type: i for i in self.vk_data.sizes}

    def out_html(self) -> str:
        return (
            f'<a href="https://vk.com/photo{self.vk_data.owner_id}_{self.vk_data.id}">'
            f'<img src="{self.vk_data.photo_max}"><br />'
            '</a>\r\n'
        )

    def delete(self) -> None:
        """
        Удаление фотографии
        """

    def download(self, folder: Path, name_counter=None, size_fmt=None) -> bool:
        """
        Скачивание графического файла в указанную папку
        :param folder: папка назначения
        :param name_counter: опциональный счётчик для использования в имени файла
        :param size_fmt: формат размера по умолчанию максимальный 'max'
        """
        from urllib.request import urlopen

        fname = self.as_attachment

        if isinstance(name_counter, int):
            fname = f'{name_counter:04d}. {fname}.jpg'

        fname_full = folder / fname

        if fname_full.is_file():  # skip exists
            return True

        with fname_full.open('wb') as f:
            url = self.get_image_url(size_fmt)
            u = urlopen(url)
            f.write(u.read())
        return fname_full.exists()

    def get_image_url(self, size_fmt=None) -> str:
        """
        Ссылка на jpg заданного размера
        :param size_fmt: формат размера, если не указан используется максимальный
        """
        if self.sizes:  # новый формат
            if size_fmt is None:
                sizez = 'smxopqryzw'[::-1]
                size = next(
                    self.sizes.get(s_l)
                    for s_l in sizez
                    if hasattr(self.sizes.get(s_l), 'url') and self.sizes.get(s_l).url
                )
            elif isinstance(size_fmt, tuple):
                size = self.sizes.get(size_fmt[0]) or self.sizes.get('x')
            else:
                msg = 'size_fmt None or tuple allowed '
                raise TypeError(msg)
            return size.url

        else:  # старый формат
            if size_fmt is None:
                return self.vk_data.photo_max  # старый формат
            elif isinstance(size_fmt, tuple):
                return getattr(self.vk_data, f'photo_{size_fmt[1]}', 'error')
            else:
                msg = 'size_fmt None or tuple allowed '
                raise TypeError(msg)

    def get_comments_data(self):
        return api.photos.get_comments(self.vk_data.id, owner_id=self.vk_data.owner_id, need_likes=True)

    @property
    def date(self) -> datetime:
        return self.vk_data.date

    @property
    def photo_max(self):
        try:
            return next(getattr(self, 'photo_' + str(s)) for s in self.size_vars if hasattr(self, 'photo_' + str(s)))
        except StopIteration:
            return None

    @property
    def as_attachment(self) -> str:
        # <type><owner_id>_<media_id>
        return f'{self.vk_object_type}{self.owner_id}_{self.id}'
