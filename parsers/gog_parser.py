import aiohttp
import json
from typing import List, Dict, Optional
from .base_parser import BaseParser, GameDeal

class GogParser(BaseParser):
    def __init__(self):
        super().__init__()
        self.base_url = "https://www.gog.com"
        self.api_url = "https://api.gog.com/products"
        self.embed_url = "https://embed.gog.com"
    
    async def get_free_games(self) -> List[GameDeal]:
        """Получить список бесплатных игр"""
        async with aiohttp.ClientSession() as session:
            url = f"{self.embed_url}/games/ajax/filtered"
            params = {
                "mediaType": "game",
                "price": "free",
                "sort": "popularity"
            }
            
            async with session.get(url, headers=self.headers, params=params) as response:
                if response.status != 200:
                    return []
                
                data = await response.json()
                games = []
                
                for product in data.get('products', []):
                    try:
                        if not product.get('isGame') or not product.get('price', {}).get('isFree'):
                            continue
                        
                        title = product.get('title', '')
                        store_id = str(product.get('id', ''))
                        url = f"{self.base_url}{product.get('url', '')}"
                        
                        game_deal = GameDeal(
                            title=title,
                            platform='gog',
                            store_id=store_id,
                            current_price=0.0,
                            original_price=float(product.get('price', {}).get('baseAmount', 0)),
                            discount_percent=100,
                            is_free=True,
                            url=url,
                            genres=product.get('genres', [])
                        )
                        
                        games.append(game_deal)
                    except Exception as e:
                        continue
                
                return games
    
    async def get_deals(self, min_discount: int = 50) -> List[GameDeal]:
        """Получить список игр со скидками"""
        async with aiohttp.ClientSession() as session:
            url = f"{self.embed_url}/games/ajax/filtered"
            params = {
                "mediaType": "game",
                "discount": f"{min_discount},",
                "sort": "discount"
            }
            
            async with session.get(url, headers=self.headers, params=params) as response:
                if response.status != 200:
                    return []
                
                data = await response.json()
                games = []
                
                for product in data.get('products', []):
                    try:
                        if not product.get('isGame'):
                            continue
                        
                        price_data = product.get('price', {})
                        if not price_data or not price_data.get('isDiscounted'):
                            continue
                        
                        discount = int(price_data.get('discount', 0))
                        if discount < min_discount:
                            continue
                        
                        title = product.get('title', '')
                        store_id = str(product.get('id', ''))
                        url = f"{self.base_url}{product.get('url', '')}"
                        
                        game_deal = GameDeal(
                            title=title,
                            platform='gog',
                            store_id=store_id,
                            current_price=float(price_data.get('finalAmount', 0)),
                            original_price=float(price_data.get('baseAmount', 0)),
                            discount_percent=discount,
                            is_free=False,
                            url=url,
                            genres=product.get('genres', [])
                        )
                        
                        games.append(game_deal)
                    except Exception as e:
                        continue
                
                return games
    
    async def search_game(self, title: str) -> Optional[GameDeal]:
        """Поиск конкретной игры"""
        async with aiohttp.ClientSession() as session:
            url = f"{self.embed_url}/games/ajax/filtered"
            params = {
                "mediaType": "game",
                "search": title
            }
            
            async with session.get(url, headers=self.headers, params=params) as response:
                if response.status != 200:
                    return None
                
                data = await response.json()
                products = data.get('products', [])
                
                if not products:
                    return None
                
                product = products[0]
                if not product.get('isGame'):
                    return None
                
                price_data = product.get('price', {})
                store_id = str(product.get('id', ''))
                details = await self.get_game_details(store_id)
                
                return GameDeal(
                    title=product.get('title', ''),
                    platform='gog',
                    store_id=store_id,
                    current_price=float(price_data.get('finalAmount', 0)),
                    original_price=float(price_data.get('baseAmount', 0)),
                    discount_percent=int(price_data.get('discount', 0)),
                    is_free=price_data.get('isFree', False),
                    url=f"{self.base_url}{product.get('url', '')}",
                    genres=details.get('genres', product.get('genres', []))
                )
    
    async def get_game_details(self, store_id: str) -> Dict:
        """Получить детальную информацию об игре"""
        async with aiohttp.ClientSession() as session:
            url = f"{self.api_url}/{store_id}"
            params = {
                "expand": "description,screenshots,videos,related"
            }
            
            async with session.get(url, headers=self.headers, params=params) as response:
                if response.status != 200:
                    return {}
                
                data = await response.json()
                if not data:
                    return {}
                
                return {
                    'genres': [genre.get('name', '') for genre in data.get('genres', [])],
                    'is_free': data.get('price', {}).get('isFree', False),
                    'price': float(data.get('price', {}).get('finalAmount', 0)),
                    'original_price': float(data.get('price', {}).get('baseAmount', 0)),
                    'discount_percent': int(data.get('price', {}).get('discount', 0))
                } 