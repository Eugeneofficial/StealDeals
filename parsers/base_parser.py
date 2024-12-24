from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from dataclasses import dataclass

@dataclass
class GameDeal:
    title: str
    platform: str
    store_id: str
    current_price: float
    original_price: float
    discount_percent: int
    is_free: bool
    url: str
    genres: List[str]

class BaseParser(ABC):
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    @abstractmethod
    async def get_free_games(self) -> List[GameDeal]:
        """Получить список бесплатных игр"""
        pass
    
    @abstractmethod
    async def get_deals(self, min_discount: int = 50) -> List[GameDeal]:
        """Получить список игр со скидками"""
        pass
    
    @abstractmethod
    async def search_game(self, title: str) -> Optional[GameDeal]:
        """Поиск конкретной игры"""
        pass
    
    @abstractmethod
    async def get_game_details(self, store_id: str) -> Dict:
        """Получить детальную информацию об игре"""
        pass 