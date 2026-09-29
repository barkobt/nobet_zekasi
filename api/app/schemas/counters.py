"""Arayüz ayarları: görünür sayaçlar, kullanıcı tercihleri, kurum ayarları."""

from typing import Any

from pydantic import BaseModel, Field


class Counter(BaseModel):
    """visible_counters bir satırı. `key` API ve JSON anahtarı, `badge` ekranda görünen."""

    key: str
    badge: str
    label: str
    description: str | None = None
    always_shown: bool = Field(
        description="G · N · S: 'Detayları göster' kapalıyken de satırda durur, kapatılamaz"
    )
    weekly_on: bool
    monthly_on: bool


class CounterUpdate(BaseModel):
    key: str
    weekly_on: bool
    monthly_on: bool


class CounterList(BaseModel):
    counters: list[Counter]


class Preference(BaseModel):
    pref_key: str
    value: Any


class Setting(BaseModel):
    """app_settings bir satırı. Boş `value` geçerlidir: 'bu metni hiç gösterme'."""

    key: str
    value: str
    label: str
    description: str | None = None


class SettingUpdate(BaseModel):
    value: str = Field(max_length=120)


class SettingList(BaseModel):
    settings: list[Setting]
