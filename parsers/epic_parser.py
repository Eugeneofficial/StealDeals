import aiohttp
import json
from typing import List, Dict, Optional
from .base_parser import BaseParser, GameDeal
from datetime import datetime

class EpicParser(BaseParser):
    def __init__(self):
        super().__init__()
        self.base_url = "https://store.epicgames.com"
        self.api_url = "https://store-content.ak.epicgames.com/api"
    
    async def get_free_games(self) -> List[GameDeal]:
        """Получить список бесплатных игр"""
        async with aiohttp.ClientSession() as session:
            url = "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions"
            params = {
                "locale": "ru",
                "country": "RU",
                "allowCountries": "RU"
            }
            
            async with session.get(url, headers=self.headers, params=params) as response:
                if response.status != 200:
                    return []
                
                data = await response.json()
                games = []
                
                for game in data.get('data', {}).get('Catalog', {}).get('searchStore', {}).get('elements', []):
                    try:
                        promotions = game.get('promotions', {})
                        if not promotions or not promotions.get('promotionalOffers'):
                            continue
                        
                        for offer in promotions['promotionalOffers']:
                            for promo in offer.get('promotionalOffers', []):
                                if promo.get('discountSetting', {}).get('discountPercentage') == 0:
                                    title = game.get('title', '')
                                    store_id = game.get('id', '')
                                    url = f"{self.base_url}/store/p/{game.get('urlSlug', '')}"
                                    
                                    game_deal = GameDeal(
                                        title=title,
                                        platform='epic',
                                        store_id=store_id,
                                        current_price=0.0,
                                        original_price=float(game.get('price', {}).get('totalPrice', {}).get('originalPrice', 0)) / 100,
                                        discount_percent=100,
                                        is_free=True,
                                        url=url,
                                        genres=[tag.get('name', '') for tag in game.get('tags', [])]
                                    )
                                    
                                    games.append(game_deal)
                    except Exception as e:
                        continue
                
                return games
    
    async def get_deals(self, min_discount: int = 50) -> List[GameDeal]:
        """Получить список игр со скидками"""
        async with aiohttp.ClientSession() as session:
            url = "https://store-site-backend-static.ak.epicgames.com/store/api/graphql"
            query = """
            query searchStoreQuery($allowCountries: String, $category: String, $count: Int, $country: String!, $keywords: String, $locale: String, $sortBy: String, $sortDir: String, $start: Int) {
                Catalog {
                    searchStore(allowCountries: $allowCountries, category: $category, count: $count, country: $country, keywords: $keywords, locale: $locale, sortBy: $sortBy, sortDir: $sortDir, start: $start) {
                        elements {
                            title
                            id
                            namespace
                            description
                            effectiveDate
                            keyImages {
                                type
                                url
                            }
                            seller {
                                name
                            }
                            price {
                                totalPrice {
                                    discountPrice
                                    originalPrice
                                    discount
                                    currencyCode
                                    currencyInfo {
                                        decimals
                                    }
                                    fmtPrice {
                                        originalPrice
                                        discountPrice
                                        intermediatePrice
                                    }
                                }
                            }
                            promotions {
                                promotionalOffers {
                                    promotionalOffers {
                                        startDate
                                        endDate
                                        discountSetting {
                                            discountType
                                            discountPercentage
                                        }
                                    }
                                }
                            }
                        }
                        paging {
                            count
                            total
                        }
                    }
                }
            }
            """
            
            variables = {
                "allowCountries": "RU",
                "category": "games/edition/base|bundles/games|editors",
                "count": 40,
                "country": "RU",
                "locale": "ru",
                "sortBy": "effectiveDate",
                "sortDir": "DESC",
                "start": 0
            }
            
            async with session.post(url, headers=self.headers, json={"query": query, "variables": variables}) as response:
                if response.status != 200:
                    return []
                
                data = await response.json()
                games = []
                
                for game in data.get('data', {}).get('Catalog', {}).get('searchStore', {}).get('elements', []):
                    try:
                        price_data = game.get('price', {}).get('totalPrice', {})
                        original_price = float(price_data.get('originalPrice', 0)) / 100
                        current_price = float(price_data.get('discountPrice', 0)) / 100
                        
                        if original_price == 0 or current_price == original_price:
                            continue
                        
                        discount = int((original_price - current_price) / original_price * 100)
                        if discount < min_discount:
                            continue
                        
                        title = game.get('title', '')
                        store_id = game.get('id', '')
                        url = f"{self.base_url}/store/p/{game.get('urlSlug', '')}"
                        
                        game_deal = GameDeal(
                            title=title,
                            platform='epic',
                            store_id=store_id,
                            current_price=current_price,
                            original_price=original_price,
                            discount_percent=discount,
                            is_free=False,
                            url=url,
                            genres=[]
                        )
                        
                        games.append(game_deal)
                    except Exception as e:
                        continue
                
                return games
    
    async def search_game(self, title: str) -> Optional[GameDeal]:
        """Поиск конкретной игры"""
        async with aiohttp.ClientSession() as session:
            url = f"{self.api_url}/content/products/search"
            params = {
                "searchTerm": title,
                "lang": "ru",
                "country": "RU",
                "sortBy": "relevancy",
                "sortDir": "DESC",
                "count": 1
            }
            
            async with session.get(url, headers=self.headers, params=params) as response:
                if response.status != 200:
                    return None
                
                data = await response.json()
                if not data or 'products' not in data:
                    return None
                
                for product in data['products']:
                    details = await self.get_game_details(product.get('productId', ''))
                    if not details:
                        continue
                    
                    return GameDeal(
                        title=product.get('title', ''),
                        platform='epic',
                        store_id=product.get('productId', ''),
                        current_price=details.get('price', 0.0),
                        original_price=details.get('original_price', 0.0),
                        discount_percent=details.get('discount_percent', 0),
                        is_free=details.get('is_free', False),
                        url=f"{self.base_url}/store/p/{product.get('urlSlug', '')}",
                        genres=details.get('genres', [])
                    )
                
                return None
    
    async def get_game_details(self, store_id: str) -> Dict:
        """Получить детальную информацию об игре"""
        async with aiohttp.ClientSession() as session:
            url = f"{self.api_url}/content/products/{store_id}"
            params = {
                "lang": "ru",
                "country": "RU"
            }
            
            async with session.get(url, headers=self.headers, params=params) as response:
                if response.status != 200:
                    return {}
                
                data = await response.json()
                if not data:
                    return {}
                
                price_data = data.get('price', {}).get('totalPrice', {})
                original_price = float(price_data.get('originalPrice', 0)) / 100
                current_price = float(price_data.get('discountPrice', 0)) / 100
                
                return {
                    'genres': [tag.get('name', '') for tag in data.get('tags', [])],
                    'is_free': current_price == 0,
                    'price': current_price,
                    'original_price': original_price,
                    'discount_percent': int((original_price - current_price) / original_price * 100) if original_price > 0 else 0
                } 