import aiohttp
import json
from typing import List, Dict, Optional
from .base_parser import BaseParser, GameDeal
from bs4 import BeautifulSoup

class SteamParser(BaseParser):
    def __init__(self):
        super().__init__()
        self.base_url = "https://store.steampowered.com"
        self.api_url = "https://store.steampowered.com/api"
    
    async def get_free_games(self) -> List[GameDeal]:
        """Получить список бесплатных игр"""
        async with aiohttp.ClientSession() as session:
            url = f"{self.base_url}/search/?maxprice=free&specials=1"
            async with session.get(url, headers=self.headers) as response:
                if response.status != 200:
                    return []
                
                html = await response.text()
                soup = BeautifulSoup(html, 'lxml')
                games = []
                
                for game_div in soup.select('a.search_result_row'):
                    try:
                        title = game_div.select_one('span.title').text.strip()
                        store_id = game_div['data-ds-appid']
                        url = game_div['href']
                        
                        game = GameDeal(
                            title=title,
                            platform='steam',
                            store_id=store_id,
                            current_price=0.0,
                            original_price=0.0,
                            discount_percent=100,
                            is_free=True,
                            url=url,
                            genres=[]
                        )
                        
                        # Получаем дополнительную информацию об игре
                        details = await self.get_game_details(store_id)
                        if details:
                            game.genres = details.get('genres', [])
                        
                        games.append(game)
                    except Exception as e:
                        continue
                
                return games
    
    async def get_deals(self, min_discount: int = 50) -> List[GameDeal]:
        """Получить список игр со скидками"""
        async with aiohttp.ClientSession() as session:
            url = f"{self.base_url}/search/?specials=1&filter=topsellers"
            async with session.get(url, headers=self.headers) as response:
                if response.status != 200:
                    return []
                
                html = await response.text()
                soup = BeautifulSoup(html, 'lxml')
                games = []
                
                for game_div in soup.select('a.search_result_row'):
                    try:
                        discount_span = game_div.select_one('div.search_discount span')
                        if not discount_span:
                            continue
                        
                        discount = int(discount_span.text.strip('-%'))
                        if discount < min_discount:
                            continue
                        
                        title = game_div.select_one('span.title').text.strip()
                        store_id = game_div['data-ds-appid']
                        url = game_div['href']
                        
                        price_div = game_div.select_one('div.search_price')
                        if not price_div:
                            continue
                        
                        prices = [float(p.strip().replace('₽', '').replace(',', '')) 
                                for p in price_div.text.strip().split() if p.strip()]
                        
                        if len(prices) >= 2:
                            original_price = prices[0]
                            current_price = prices[-1]
                        else:
                            continue
                        
                        game = GameDeal(
                            title=title,
                            platform='steam',
                            store_id=store_id,
                            current_price=current_price,
                            original_price=original_price,
                            discount_percent=discount,
                            is_free=False,
                            url=url,
                            genres=[]
                        )
                        
                        # Получаем дополнительную информацию об игре
                        details = await self.get_game_details(store_id)
                        if details:
                            game.genres = details.get('genres', [])
                        
                        games.append(game)
                    except Exception as e:
                        continue
                
                return games
    
    async def search_game(self, title: str) -> Optional[GameDeal]:
        """Поиск конкретной ��гры"""
        async with aiohttp.ClientSession() as session:
            url = f"{self.base_url}/search/suggest?term={title}&f=games&cc=RU&l=russian"
            async with session.get(url, headers=self.headers) as response:
                if response.status != 200:
                    return None
                
                data = await response.json()
                if not data or 'items' not in data:
                    return None
                
                for item in data['items']:
                    if item.get('type') != 'game':
                        continue
                    
                    store_id = str(item.get('id'))
                    details = await self.get_game_details(store_id)
                    
                    if not details:
                        continue
                    
                    return GameDeal(
                        title=item.get('name', ''),
                        platform='steam',
                        store_id=store_id,
                        current_price=details.get('price', 0.0),
                        original_price=details.get('initial_price', 0.0),
                        discount_percent=details.get('discount_percent', 0),
                        is_free=details.get('is_free', False),
                        url=f"{self.base_url}/app/{store_id}",
                        genres=details.get('genres', [])
                    )
                
                return None
    
    async def get_game_details(self, store_id: str) -> Dict:
        """Получить детальную информацию об игре"""
        async with aiohttp.ClientSession() as session:
            url = f"{self.api_url}/appdetails?appids={store_id}&cc=RU&l=russian"
            async with session.get(url, headers=self.headers) as response:
                if response.status != 200:
                    return {}
                
                data = await response.json()
                if not data or store_id not in data or not data[store_id].get('success'):
                    return {}
                
                game_data = data[store_id]['data']
                return {
                    'genres': [genre['description'] for genre in game_data.get('genres', [])],
                    'is_free': game_data.get('is_free', False),
                    'price': float(game_data.get('price_overview', {}).get('final', 0)) / 100,
                    'initial_price': float(game_data.get('price_overview', {}).get('initial', 0)) / 100,
                    'discount_percent': game_data.get('price_overview', {}).get('discount_percent', 0)
                } 