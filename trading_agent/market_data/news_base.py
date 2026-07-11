from abc import ABC, abstractmethod
from typing import Any, Dict, List


class NewsDataProvider(ABC):
    @abstractmethod
    def get_news(self, symbols: List[str]) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_sentiment_summary(self, symbols: List[str]) -> str:
        pass
