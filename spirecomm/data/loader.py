import json
import os
from typing import Dict, List, Any, Optional

class GameDataLoader:
    """
    Load and provide access to Slay the Spire game data from export files.
    """
    
    def __init__(self, data_path: str = "D:\\SteamLibrary\\steamapps\\common\\SlayTheSpire\\export"):
        self.data_path = data_path
        self.items_file = os.path.join(data_path, "items.json")
        self._cards: Optional[Dict[str, Dict[str, Any]]] = None
        self._relics: Optional[Dict[str, Dict[str, Any]]] = None
        self._keywords: Optional[Dict[str, Dict[str, Any]]] = None
        self._creatures: Optional[Dict[str, Dict[str, Any]]] = None
        self._enemies: Optional[Dict[str, Dict[str, Any]]] = None
        
    def load_data(self) -> None:
        """
        Load all game data from the items.json file.
        """
        if os.path.exists(self.items_file):
            with open(self.items_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Process cards
            self._cards = {}
            for card in data.get('cards', []):
                card_name = card['name'].lower()
                self._cards[card_name] = card
            
            # Process relics
            self._relics = {}
            for relic in data.get('relics', []):
                relic_name = relic['name'].lower()
                self._relics[relic_name] = relic
            
            # Process keywords
            self._keywords = {}
            for keyword in data.get('keywords', []):
                keyword_name = keyword['name'].lower()
                self._keywords[keyword_name] = keyword
            
            # Process creatures (includes players and enemies)
            self._creatures = {}
            self._enemies = {}
            for creature in data.get('creatures', []):
                creature_name = creature['name'].lower()
                self._creatures[creature_name] = creature
                
                # Filter out enemies (non-player creatures)
                if creature.get('type') != 'Player':
                    self._enemies[creature_name] = creature
    
    def get_card_data(self, card_name: str) -> Optional[Dict[str, Any]]:
        """
        Get data for a specific card.
        
        Args:
            card_name: Name of the card (case-insensitive)
            
        Returns:
            Card data dictionary, or None if not found
        """
        if self._cards is None:
            self.load_data()
        
        card_name = card_name.lower()
        return self._cards.get(card_name)
    
    def get_relic_data(self, relic_name: str) -> Optional[Dict[str, Any]]:
        """
        Get data for a specific relic.
        
        Args:
            relic_name: Name of the relic (case-insensitive)
            
        Returns:
            Relic data dictionary, or None if not found
        """
        if self._relics is None:
            self.load_data()
        
        relic_name = relic_name.lower()
        return self._relics.get(relic_name)
    
    def get_keyword_data(self, keyword: str) -> Optional[Dict[str, Any]]:
        """
        Get data for a specific keyword.
        
        Args:
            keyword: Keyword name (case-insensitive)
            
        Returns:
            Keyword data dictionary, or None if not found
        """
        if self._keywords is None:
            self.load_data()
        
        keyword = keyword.lower()
        return self._keywords.get(keyword)
    
    def get_all_cards(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all card data.
        
        Returns:
            Dictionary mapping card names to their data
        """
        if self._cards is None:
            self.load_data()
        return self._cards
    
    def get_all_relics(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all relic data.
        
        Returns:
            Dictionary mapping relic names to their data
        """
        if self._relics is None:
            self.load_data()
        return self._relics
    
    def search_cards(self, **filters) -> List[Dict[str, Any]]:
        """
        Search for cards matching specific filters.

        Args:
            filters: Keyword arguments to filter cards (e.g., type="Attack", color="Red")

        Returns:
            List of matching cards
        """
        if self._cards is None:
            self.load_data()

        results = []
        for card_data in self._cards.values():
            match = True
            for key, value in filters.items():
                if key in card_data and card_data[key].lower() != value.lower():
                    match = False
                    break
            if match:
                results.append(card_data)

        return results
    
    def get_creature_data(self, creature_name: str) -> Optional[Dict[str, Any]]:
        """
        Get data for a specific creature.

        Args:
            creature_name: Name of the creature (case-insensitive)

        Returns:
            Creature data dictionary, or None if not found
        """
        if self._creatures is None:
            self.load_data()

        creature_name = creature_name.lower()
        return self._creatures.get(creature_name)
    
    def get_enemy_data(self, enemy_name: str) -> Optional[Dict[str, Any]]:
        """
        Get data for a specific enemy.

        Args:
            enemy_name: Name of the enemy (case-insensitive)

        Returns:
            Enemy data dictionary, or None if not found
        """
        if self._enemies is None:
            self.load_data()

        enemy_name = enemy_name.lower()
        return self._enemies.get(enemy_name)
    
    def get_all_creatures(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all creature data.

        Returns:
            Dictionary mapping creature names to their data
        """
        if self._creatures is None:
            self.load_data()
        return self._creatures
    
    def get_all_enemies(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all enemy data.

        Returns:
            Dictionary mapping enemy names to their data
        """
        if self._enemies is None:
            self.load_data()
        return self._enemies
    
    def search_enemies(self, **filters) -> List[Dict[str, Any]]:
        """
        Search for enemies matching specific filters.

        Args:
            filters: Keyword arguments to filter enemies (e.g., type="Boss")

        Returns:
            List of matching enemies
        """
        if self._enemies is None:
            self.load_data()

        results = []
        for enemy_data in self._enemies.values():
            match = True
            for key, value in filters.items():
                if key in enemy_data and enemy_data[key].lower() != value.lower():
                    match = False
                    break
            if match:
                results.append(enemy_data)

        return results

# Create a global instance for easy access
game_data_loader = GameDataLoader()
