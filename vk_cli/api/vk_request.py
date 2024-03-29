from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

import requests

from . import vk_const
from .misc import get_model_class, timer
from .vk_api_error import (
    VKApiErrorFactory,
    VKECaptchaNeeded,
    VKEInternal,
    VKETooFrequent,
    VKError,
)
from .vk_response import VKResponse

if TYPE_CHECKING:
    from .vk_credentials import VK, VKCredentials

log = logging.getLogger(__name__)


class VKRequest:
    URL_BASE = 'https://api.vk.com/method/'
    attempts = 1  # By default, there is 1 attempt for loading

    def __init__(self, vk: VK, method_name: str | None = None, parameters: dict | None = None, **pars) -> None:
        self._vk = vk
        self.method_name = method_name
        self.method_params = parameters or {}
        self.method_params = {**self.method_params, **pars}

        self._method_params_prepared = None
        self.response = None
        self.binded_model = None

    @classmethod
    def from_request(cls, request: VKRequest) -> VKRequest:
        pre = cls(None)
        pre._init_from_request(request)
        return pre

    def _init_from_request(self, request: VKRequest) -> None:
        from copy import deepcopy

        self.__dict__.update(deepcopy(request.__dict__))
        assert self._vk is not None, f"is required to set 'vk' value for class '{self.__class__.__name__}'"

    def __str__(self) -> str:
        inv = ('stub', 'invoked')[self.is_invoked]
        binding = ''
        if self.binded_model:
            binding = f"--> '{self.binded_model.__name__}'"
        return f'{self.method_name}({self.method_params}) [{inv}] {binding}'

    @property
    def _credentials(self) -> VKCredentials:
        return self._vk.credentials

    @property
    def is_binded(self) -> bool:
        return self.binded_model is not None

    @property
    def is_invoked(self) -> bool:
        return self.response is not None

    def set_param(self, param: str, value: Any) -> None:
        self.method_params[param] = value

    @property
    def _prepared_parameters(self) -> dict:
        if self._method_params_prepared is None:
            self._method_params_prepared = self.method_params.copy()

            if self._credentials.access_token is not None:
                self._method_params_prepared[vk_const.ACCESS_TOKEN] = self._credentials.access_token

            # Set actual version of API
            self._method_params_prepared[vk_const.API_VERSION] = self._credentials.api_version

            # Set preferred language for request
            if self._credentials.lang:
                self._method_params_prepared[vk_const.LANG] = self._credentials.lang

        return self._method_params_prepared

    @property
    def _str_prepared_parameters(self) -> dict[str, str]:
        """
        filter out empty values, cast values to str
        :return:
        """
        str_params = {}

        for k, v in self._prepared_parameters.items():
            if v is None:
                continue

            # cast params
            if isinstance(v, bool):
                str_params[k] = int(v)
            elif isinstance(v, list | set):
                str_params[k] = ','.join(map(str, v))
            else:
                str_params[k] = v

        return {k: str(v).encode('utf-8') for k, v in str_params.items()}

    @property
    def url(self) -> str:
        return self.URL_BASE + self.method_name

    def invoke(self):
        """
        Выполнение запроса, формирование и сохранение результата
        """
        raw_result = self._do_invoke()
        assert raw_result is not None

        self.response = VKResponse(self, raw_result)

    def invoked(self):
        if not self.is_invoked:
            self.invoke()
        return self

    @timer
    def _do_invoke(self):
        """
        Непосредственный вызов одного из методов API vk.com
        """
        log.debug('_do_invoke')
        log.info(f'* {self.method_name}: {self.method_params}')

        while True:
            try:
                resp = requests.post(self.url, data=self._str_prepared_parameters, timeout=5)
                resp.raise_for_status()
                json_resp = resp.json()
                try:
                    return json_resp['response']
                except KeyError as e:
                    raise VKApiErrorFactory.get_exception(json_resp.get('error') or json_resp) from e

            except (VKETooFrequent, VKEInternal):
                # если запросы отправляются слишком часто
                log.info('sleep for 1 sec')

                time.sleep(3)

            except VKECaptchaNeeded as e:
                # требуется ввод кода с картинки
                sid, img = e.error['captcha_sid'], e.error['captcha_img']

                captha_r = VKCapchaR(sid, img, self.method_name, self._prepared_parameters)
                captha_r.show()
                captha_r.get_input()

                return captha_r.invoke_response()

            except VKError:
                raise

    def invoke_response(self):
        return self._do_invoke()

    def get_invoke_result(self, update=False) -> VKResponse:
        """
        Результат выполнения запроса
        :return:
        """
        if not self.is_invoked or update:
            self.invoke()
        return self.response

    def bind_model(self, model_class_name):
        """
        Сопоставление запросу модели по имени класса
        :param model_class_name:
        :return:
        """
        self.binded_model = get_model_class(model_class_name)


class PartialRequest(VKRequest):
    offset = None
    count = None

    def __init__(self, request, step, offset) -> None:
        super().__init__(None)
        self._init_from_request(request)

        self.set_offset(offset)
        self.set_count(step)

    def set_offset(self, offset):
        self.offset = offset

        old_offset = self.method_params.get('offset', 0)
        if self.offset != old_offset:
            self.set_param('offset', offset)
            self.response = None

    def set_count(self, step):
        self.count = step

        old_count = self.method_params.get('count', 0)
        if self.count != old_count:
            self.set_param('count', self.count)
            self.response = None

    def __str__(self) -> str:
        res = f' [{self.response.count} items]' if self.is_invoked else ''
        return f'{self.method_name}: {self.method_params} \ninvoked = {self.is_invoked}{res}'


class VKCapchaR(VKRequest):
    def __init__(self, sid, ig_url, method, params) -> None:
        super().__init__(method, params)

        self.sid = sid
        self.capcha_url = ig_url
        self.answer_code = ''

    def show(self) -> None:
        import webbrowser

        webbrowser.open(self.capcha_url)

    def get_input(self):
        self.answer_code = input('Enter a code from the image:')
        print(self.answer_code)

    def invoke_response(self):
        self.method_params['captcha_sid'] = self.sid
        self.method_params['captcha_key'] = self.answer_code

        return super().invoke_response()
