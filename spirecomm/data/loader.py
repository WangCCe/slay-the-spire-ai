import json
import os
import sys
import re
import warnings
from typing import Dict, List, Any, Optional


DEFAULT_EXPORT_PATH = "D:\\SteamLibrary\\steamapps\\common\\SlayTheSpire\\export"


def convert_windows_path_to_wsl(windows_path: str) -> str:
    """
    Convert Windows path to WSL path if running in WSL.

    Examples:
        D:\\path\\to\\file → /mnt/d/path/to/file
        C:\\path\\to\\file → /mnt/c/path/to/file

    Args:
        windows_path: Windows-style path

    Returns:
        WSL-compatible path (or original path if not in WSL)
    """
    # Check if we're in WSL
    is_wsl = sys.platform.startswith('linux') and os.path.exists('/proc/version')
    if is_wsl:
        try:
            with open('/proc/version', 'r') as f:
                version_info = f.read().lower()
                is_wsl = 'microsoft' in version_info or 'wsl' in version_info
        except:
            is_wsl = False

    if not is_wsl:
        return windows_path

    # Convert Windows path to WSL path
    # Handle both backslashes and forward slashes
    path = windows_path.replace('\\', '/')

    # Match drive letter and path (e.g., D:/path or D:/path)
    match = re.match(r'^([A-Za-z]):/(.*)$', path)
    if match:
        drive_letter = match.group(1).lower()
        rest_of_path = match.group(2)
        return f'/mnt/{drive_letter}/{rest_of_path}'

    return windows_path


# Hardcoded metadata for cards with complex damage formulas
# These are cards that cannot be reliably parsed from descriptions
CARD_METADATA = {
    # Ironclad Attacks
    'heavy blade': {
        'damage': 14,
        'upgraded_damage': 22,
        'is_x_damage': False,
        'reason': 'Dynamic damage formula: !D! = 5 + times_str**'
    },
    'cleave': {
        'damage': 8,
        'upgraded_damage': 11,
        'aoe': True,
        'reason': 'AOE attack affecting all enemies'
    },
    'whirlwind': {
        'damage': 0,
        'is_x_damage': True,
        'aoe': True,
        'reason': 'X damage = energy spent'
    },
    'pommel strike': {
        'damage': 10,
        'upgraded_damage': 14,
        'reason': 'Multi-hit: deals damage twice'
    },
    'iron wave': {
        'damage': 5,
        'upgraded_damage': 7,
        'block': 5,
        'upgraded_block': 7,
        'reason': 'Deal damage and gain block'
    },
    'body slam': {
        'damage': 0,
        'is_x_damage': True,
        'reason': 'Damage equals your block'
    },
    'bludgeon': {
        'damage': 0,
        'is_x_damage': True,
        'reason': 'X damage = 12-30 based on current block'
    },
    'uppercut': {
        'damage': 13,
        'upgraded_damage': 18,
        'reason': 'Multi-hit: deals damage 3 times'
    },
    'sword boom': {
        'damage': 13,
        'upgraded_damage': 17,
        'reason': 'Returns to hand, exhaust if not ethereal'
    },
    'immolate': {
        'damage': 21,
        'upgraded_damage': 28,
        'aoe': True,
        'reason': 'AOE damage to all enemies'
    },
    'sever soul': {
        'damage': 16,
        'upgraded_damage': 22,
        'reason': 'Exhausts a card from hand'
    },
    'reaper': {
        'damage': 3,
        'upgraded_damage': 4,
        'is_x_damage': True,  # Based on unblocked damage
        'reason': 'Heals for % of unblocked damage dealt'
    },
    'carnage': {
        'damage': 20,
        'upgraded_damage': 28,
        'reason': 'Cannot attack if at low HP'
    },
    'limit break': {
        'damage': 0,
        'reason': 'Double strength, no direct damage'
    },

    # Common Ironclad Skills
    'defend': {
        'block': 5,
        'upgraded_block': 8,
        'reason': 'Basic defense card'
    },
    'bash': {
        'damage': 8,
        'upgraded_damage': 10,
        'reason': 'Vulnerable debuff'
    },
    'armaments': {
        'damage': 5,
        'upgraded_damage': 5,
        'reason': 'Upgrade cards in hand'
    },
    'angry mode': {
        'block': 5,
        'reason': 'Gain strength when damaged'
    },
    'flex': {
        'damage': 2,
        'upgraded_damage': 3,
        'reason': 'Gain-lose strength combo'
    },
    'flash of steel': {
        'damage': 5,
        'upgraded_damage': 7,
        'reason': 'Draw 1 card'
    },
    'shrug it off': {
        'block': 8,
        'upgraded_block': 11,
        'reason': 'Draw 1 card'
    },
    'pain': {
        'damage': 6,
        'upgraded_damage': 9,
        'reason': 'Lose HP, deal damage'
    },
    'disarm': {
        'damage': 7,
        'upgraded_damage': 10,
        'reason': 'Temporarily reduce enemy attack'
    },
    'pummel': {
        'damage': 3,
        'upgraded_damage': 4,
        'reason': 'Multi-hit based on energy'
    },
    'tempest': {
        'damage': 4,
        'upgraded_damage': 6,
        'is_x_damage': True,  # Multi-hit
        'reason': 'Multi-hit based on energy'
    },
    'dark embrace': {
        'block': 5,
        'upgraded_block': 7,
        'reason': 'Draw when cards exhausted'
    },
    'combust': {
        'damage': 0,
        'is_x_damage': True,  # Based on turns played
        'reason': 'Self-damage over time'
    },
    'rage': {
        'block': 0,
        'is_x_block': True,  # Based on energy spent
        'reason': 'X block = energy spent'
    },
    'exhume': {
        'damage': 0,
        'reason': 'Retrieve exhaust pile card'
    },
    'second wind': {
        'damage': 0,
        'block': 0,
        'reason': 'Exhaust: gain block and draw'
    },

    # Powers
    'demon form': {
        'damage': 0,
        'reason': 'Gain strength each turn'
    },
    'inflame': {
        'damage': 0,
        'reason': 'Gain strength'
    },
    'spot weakness': {
        'damage': 0,
        'reason': 'Gain strength when attacking enemy with intent'
    },
}


class GameDataLoader:
    """
    Load and provide access to Slay the Spire game data from export files.

    This loader reads items.json from the Slay the Spire export directory
    and provides access to card, relic, creature, and keyword metadata.
    """

    def __init__(self, data_path: str = DEFAULT_EXPORT_PATH, auto_load: bool = True):
        """
        Initialize the game data loader.

        Args:
            data_path: Path to the Slay the Spire export directory
            auto_load: If True, load data immediately (raises FileNotFoundError if missing)
                      If False, data loads on first access (returns None if missing)
        """
        self.data_path = convert_windows_path_to_wsl(data_path)
        self.items_file = os.path.join(self.data_path, "items.json")
        self._cards: Optional[Dict[str, Dict[str, Any]]] = None
        self._relics: Optional[Dict[str, Dict[str, Any]]] = None
        self._keywords: Optional[Dict[str, Dict[str, Any]]] = None
        self._creatures: Optional[Dict[str, Dict[str, Any]]] = None
        self._enemies: Optional[Dict[str, Dict[str, Any]]] = None
        self._loaded = False

        if auto_load:
            self.load_data()

    def load_data(self) -> None:
        """
        Load all game data from the items.json file.

        Raises:
            FileNotFoundError: If items.json does not exist
            ValueError: If items.json is corrupted or has invalid structure
        """
        if self._loaded:
            return

        if not os.path.exists(self.items_file):
            raise FileNotFoundError(
                f"items.json not found at {self.items_file}\n"
                f"Please install StSExporter mod for Slay the Spire."
            )

        try:
            with open(self.items_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"items.json is corrupted at line {e.lineno}: {e.msg}\n"
                f"Please reinstall StSExporter mod."
            )

        # Validate structure
        expected_keys = ['cards', 'relics', 'potions', 'creatures', 'keywords']
        missing_keys = [k for k in expected_keys if k not in data]
        if missing_keys:
            warnings.warn(
                f"items.json is missing expected keys: {missing_keys}\n"
                f"This may indicate a new StSExporter version."
            )

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

        self._loaded = True

        # Log success (to stderr to avoid interfering with Communication Mod)
        print(
            f"Game data loaded: {len(self._cards)} cards, "
            f"{len(self._relics)} relics, "
            f"{len(self._creatures)} creatures, "
            f"{len(self._keywords)} keywords, "
            f"{len(data.get('potions', []))} potions",
            file=sys.stderr
        )

    def get_card_data(self, card_name: str) -> Optional[Dict[str, Any]]:
        """
        Get data for a specific card.

        Args:
            card_name: Name of the card (case-insensitive)

        Returns:
            Card data dictionary, or None if not found
        """
        if self._cards is None:
            warnings.warn("GameDataLoader not initialized, call load_data() first")
            return None

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
            warnings.warn("GameDataLoader not initialized, call load_data() first")
            return None

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
            warnings.warn("GameDataLoader not initialized, call load_data() first")
            return None

        keyword = keyword.lower()
        return self._keywords.get(keyword)

    def get_all_cards(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all card data.

        Returns:
            Dictionary mapping card names to their data
        """
        if self._cards is None:
            warnings.warn("GameDataLoader not initialized, call load_data() first")
            return {}
        return self._cards

    def get_all_relics(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all relic data.

        Returns:
            Dictionary mapping relic names to their data
        """
        if self._relics is None:
            warnings.warn("GameDataLoader not initialized, call load_data() first")
            return {}
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
            warnings.warn("GameDataLoader not initialized, call load_data() first")
            return []

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
            warnings.warn("GameDataLoader not initialized, call load_data() first")
            return None

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
            warnings.warn("GameDataLoader not initialized, call load_data() first")
            return None

        enemy_name = enemy_name.lower()
        return self._enemies.get(enemy_name)

    def get_all_creatures(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all creature data.

        Returns:
            Dictionary mapping creature names to their data
        """
        if self._creatures is None:
            warnings.warn("GameDataLoader not initialized, call load_data() first")
            return {}
        return self._creatures

    def get_all_enemies(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all enemy data.

        Returns:
            Dictionary mapping enemy names to their data
        """
        if self._enemies is None:
            warnings.warn("GameDataLoader not initialized, call load_data() first")
            return {}
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
            warnings.warn("GameDataLoader not initialized, call load_data() first")
            return []

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

    def _parse_card_damage(self, card_data: Dict[str, Any]) -> Optional[int]:
        """
        Extract base damage value from card data using multi-stage approach.

        Stages:
        1. Check structured 'damage' field (future-proof for StSExporter)
        2. Check CARD_METADATA for hardcoded values (complex cards)
        3. Parse description with regex

        Args:
            card_data: Card data dictionary from items.json

        Returns:
            Base damage value, or None if not found/not applicable

        Examples:
            >>> loader._parse_card_damage({'name': 'Bash', 'description': 'Deal 8 damage.'})
            8
            >>> loader._parse_card_damage({'name': 'Heavy Blade', ...})
            14  # From CARD_METADATA
        """
        if not card_data:
            return None

        # Stage 1: Check for structured field (future-proof)
        if 'damage' in card_data:
            return int(card_data['damage']) if card_data['damage'] else None

        card_name = card_data.get('name', '').lower()

        # Stage 2: Check CARD_METADATA for hardcoded values
        if card_name in CARD_METADATA:
            metadata = CARD_METADATA[card_name]
            if metadata.get('is_x_damage'):
                return 0  # X-damage cards have variable damage
            return metadata.get('damage')

        # Stage 3: Parse description with regex
        description = card_data.get('description', '').lower()
        match = re.search(r'deal (\d+) damage', description)
        if match:
            return int(match.group(1))

        return None

    def _parse_card_block(self, card_data: Dict[str, Any]) -> Optional[int]:
        """
        Extract base block value from card data.

        Args:
            card_data: Card data dictionary from items.json

        Returns:
            Base block value, or None if not found/not applicable

        Examples:
            >>> loader._parse_card_block({'name': 'Defend', 'description': 'Gain 5 Block.'})
            5
        """
        if not card_data:
            return None

        # Check structured field
        if 'block' in card_data:
            return int(card_data['block']) if card_data['block'] else None

        card_name = card_data.get('name', '').lower()

        # Check CARD_METADATA
        if card_name in CARD_METADATA:
            metadata = CARD_METADATA[card_name]
            if metadata.get('is_x_block'):
                return 0  # X-block cards have variable block
            return metadata.get('block')

        # Parse description
        description = card_data.get('description', '').lower()
        match = re.search(r'gain (\d+) block', description)
        if match:
            return int(match.group(1))

        return None

    def _is_card_aoe(self, card_data: Dict[str, Any]) -> bool:
        """
        Detect if card is an AOE (multi-target) attack.

        Args:
            card_data: Card data dictionary from items.json

        Returns:
            True if card affects multiple enemies, False otherwise

        Examples:
            >>> loader._is_card_aoe({'name': 'Cleave', 'description': 'Deal 8 damage to ALL enemies.'})
            True
            >>> loader._is_card_aoe({'name': 'Strike', 'description': 'Deal 6 damage.'})
            False
        """
        if not card_data:
            return False

        card_name = card_data.get('name', '').lower()

        # Check CARD_METADATA first
        if card_name in CARD_METADATA:
            return CARD_METADATA[card_name].get('aoe', False)

        # Check description for AOE keywords
        description = card_data.get('description', '').lower()
        aoe_keywords = ['all enemies', 'every enemy', 'each enemy', 'all']
        return any(keyword in description for keyword in aoe_keywords)


# Create a global instance for easy access
# Try to initialize with auto_load=True, fall back to auto_load=False if file not found
try:
    export_path = os.environ.get('SLAY_THE_SPIRE_EXPORT_PATH', DEFAULT_EXPORT_PATH)
    game_data_loader = GameDataLoader(export_path, auto_load=True)
except (FileNotFoundError, ValueError) as e:
    # Fall back to non-initialized loader (will warn on first use)
    game_data_loader = GameDataLoader(auto_load=False)
    warnings.warn(
        f"Failed to load game data: {e}\n"
        f"Game data will be unavailable. Install StSExporter mod to enable card metadata."
    )
