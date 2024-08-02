from abc import abstractmethod
from typing import Protocol, TypeVar, Union

KeyT = TypeVar("KeyT", contravariant=True)
ResponseT = TypeVar("ResponseT", covariant=True)
EncodableT = TypeVar("EncodableT", contravariant=True)
ExpiryT = TypeVar("ExpiryT", contravariant=True)
AbsExpiryT = TypeVar("AbsExpiryT", contravariant=True)

class CacheProtocol(Protocol[KeyT, ResponseT, EncodableT, ExpiryT, AbsExpiryT]):
    @abstractmethod
    def get(self, name: KeyT) -> ResponseT:
        pass

    @abstractmethod
    def set(
        self,
        name: KeyT,
        value: EncodableT,
        ex: Union[ExpiryT, None] = None,
        px: Union[ExpiryT, None] = None,
        nx: bool = False,
        xx: bool = False,
        keepttl: bool = False,
        get: bool = False,
        exat: Union[AbsExpiryT, None] = None,
        pxat: Union[AbsExpiryT, None] = None,
    ) -> ResponseT:
        pass

    @abstractmethod
    def delete(self, *names: KeyT) -> ResponseT:
        pass
