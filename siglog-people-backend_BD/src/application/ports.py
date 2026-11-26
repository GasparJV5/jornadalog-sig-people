"""Portas (interfaces) que a camada de aplicação exige da infraestrutura."""
from abc import ABC, abstractmethod
from typing import List, Optional

from src.domain.events import DomainEvent


class EventPublisher(ABC):
    @abstractmethod
    def publish(self, event: DomainEvent) -> None: ...


class Repository(ABC):
    @abstractmethod
    def add(self, entity): ...
    @abstractmethod
    def get(self, id: str): ...
    @abstractmethod
    def update(self, entity): ...
    @abstractmethod
    def list(self) -> List: ...
