import json
import logging
import os
import sys
import re
import warnings
from typing import Dict, List, Any, Optional, Tuple


DEFAULT_EXPORT_PATH = "D:\\SteamLibrary\\steamapps\\common\\SlayTheSpire\\export"

logger = logging.getLogger(__name__)


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
# These are cards that cannot be reliably parsed from wiki data or descriptions
# After wiki parser integration, this only contains cards with dynamic formulas
CARD_METADATA = {
    # X-Damage Cards (variable damage based on game state)
    'body slam': {
        'damage': 0,
        'is_x_damage': True,
        'reason': 'X-damage = player_block'
    },
    'whirlwind': {
        'damage': 0,
        'is_x_damage': True,
        'aoe': True,
        'reason': 'X-damage = max_energy (AOE to all enemies)'
    },
    'combust': {
        'damage': 0,
        'is_x_damage': True,
        'reason': 'X-damage = self-damage over time'
    },

    # X-Block Cards (variable block based on game state)
    'rage': {
        'block': 0,
        'is_x_block': True,
        'reason': 'X-block = max_energy'
    },

    # Complex Formula Cards (damage scales with stats)
    'heavy blade': {
        'damage': 14,
        'upgraded_damage': 14,
        'is_x_damage': False,
        'reason': 'Base damage, scales with Strength multiplier in combat simulation'
    },

    # Power Cards (no direct damage/block, stat manipulation)
    'demon form': {
        'damage': 0,
        'reason': 'Power: Gain Strength each turn'
    },
    'inflame': {
        'damage': 0,
        'reason': 'Power: Gain Strength'
    },
    'spot weakness': {
        'damage': 0,
        'reason': 'Power: Gain Strength when attacking if enemy intends to attack'
    },
    'limit break': {
        'damage': 0,
        'reason': 'Power: Double your Strength'
    },
    'flex': {
        'damage': 0,
        'reason': 'Gain Strength this turn, lose at end of turn'
    },

    # Special Effect Cards (mechanics not captured by damage/block values)
    'exhume': {
        'damage': 0,
        'reason': 'Retrieve card from exhaust pile'
    },
    'second wind': {
        'damage': 0,
        'block': 0,
        'reason': 'Exhaust non-Attack cards, gain block per card'
    },
    'disarm': {
        'damage': 0,
        'reason': 'Enemy loses Strength, Exhaust'
    },
    'pain': {
        'damage': 0,
        'reason': 'Curse: Lose HP when other cards played'
    },
}


def _split_card_upgrade_suffix(card_name: str) -> Tuple[str, int]:
    match = re.match(r'^(.*?)(?:\+(\d*))?$', card_name)
    if not match:
        return card_name, 0
    base_name, upgrade_count = match.groups()
    if base_name == card_name:
        return card_name, 0
    if upgrade_count:
        return base_name, int(upgrade_count)
    return base_name, 1


def _searing_blow_upgrade_damage(upgrades: int) -> int:
    return upgrades * (upgrades + 7) // 2 if upgrades > 0 else 0


class GameDataLoader:
    """
    Load and provide access to Slay the Spire game data from export files.

    This loader reads items.json from the Slay the Spire export directory
    and provides access to card, relic, creature, and keyword metadata.

    Additionally, it can parse wiki-card-data.txt for enhanced upgrade value extraction.
    """

    def __init__(self, data_path: str = DEFAULT_EXPORT_PATH, auto_load: bool = True, wiki_data_path: Optional[str] = None):
        """
        Initialize the game data loader.

        Args:
            data_path: Path to the Slay the Spire export directory
            auto_load: If True, load data immediately (raises FileNotFoundError if missing)
                      If False, data loads on first access (returns None if missing)
            wiki_data_path: Optional path to wiki-card-data.txt. If None, uses data_path/wiki-card-data.txt
        """
        self.data_path = convert_windows_path_to_wsl(data_path)
        self.items_file = os.path.join(self.data_path, "items.json")
        self._wiki_data_file = convert_windows_path_to_wsl(wiki_data_path) if wiki_data_path else os.path.join(self.data_path, "wiki-card-data.txt")
        self._cards: Optional[Dict[str, Dict[str, Any]]] = None
        self._relics: Optional[Dict[str, Dict[str, Any]]] = None
        self._keywords: Optional[Dict[str, Dict[str, Any]]] = None
        self._creatures: Optional[Dict[str, Dict[str, Any]]] = None
        self._enemies: Optional[Dict[str, Dict[str, Any]]] = None
        self._wiki_data: Optional[Dict[str, Dict[str, Any]]] = None  # Lazy-loaded wiki card data
        self._enhanced_monster_db = None  # Lazy-loaded enhanced monster database
        self._loaded = False
        self._logged_source = False
        self._fallback_used = False
        self._fallback_from = None
        self._fallback_to = None
        self._potions_count = 0

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

        # If the export path points to an empty StSExporter stub, fall back to parent export.
        if not data.get('cards'):
            parent_path = os.path.dirname(self.data_path)
            parent_items = os.path.join(parent_path, "items.json")
            if parent_path and parent_path != self.data_path and os.path.exists(parent_items):
                try:
                    with open(parent_items, 'r', encoding='utf-8') as f:
                        parent_data = json.load(f)
                    if parent_data.get('cards'):
                        logger.warning(
                            "items.json at %s has 0 cards; falling back to %s",
                            self.items_file,
                            parent_items,
                        )
                        self._fallback_used = True
                        self._fallback_from = self.items_file
                        self._fallback_to = parent_items
                        self.data_path = parent_path
                        self.items_file = parent_items
                        self._wiki_data_file = os.path.join(self.data_path, "wiki-card-data.txt")
                        data = parent_data
                except json.JSONDecodeError:
                    pass

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
        self._potions_count = len(data.get('potions', []))

    def _log_loaded_source_once(self) -> None:
        """Log data source details once, after logging is configured."""
        if not self._loaded or self._logged_source:
            return
        self._logged_source = True
        if self._fallback_used:
            logger.warning(
                "Game data fallback: using %s instead of %s",
                self._fallback_to,
                self._fallback_from,
            )
        logger.info(
            "Game data loaded: %s cards, %s relics, %s creatures, %s keywords, %s potions",
            len(self._cards) if self._cards is not None else 0,
            len(self._relics) if self._relics is not None else 0,
            len(self._creatures) if self._creatures is not None else 0,
            len(self._keywords) if self._keywords is not None else 0,
            self._potions_count,
        )
        logger.info("Game data source: %s", self.items_file)

    def _load_wiki_data(self) -> None:
        """
        Lazy-load wiki card data from wiki-card-data.txt.

        This method loads and parses the Lua-formatted wiki data file,
        extracting Text fields with upgrade values like [8|10].
        The data is cached in self._wiki_data for subsequent accesses.

        Wiki data format (simplified Lua table):
        {Name = "Bash", Text = "Deal [8|10] damage.", Cost = 2, CostPlus = nil}
        """
        if self._wiki_data is not None:
            return  # Already loaded

        self._wiki_data = {}

        if not os.path.exists(self._wiki_data_file):
            print(
                f"Wiki data not found at {self._wiki_data_file}, using fallback parsing",
                file=sys.stderr
            )
            return

        try:
            with open(self._wiki_data_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Parse wiki data using regex
            # Match individual card entries: {Name = "...", Text = "...", ...}
            card_pattern = r'\{Name = "(.*?)",.*?Text = "(.*?)".*?\}'
            matches = re.findall(card_pattern, content, re.DOTALL)

            for name, text in matches:
                card_name = name.lower()
                self._wiki_data[card_name] = {
                    'text': text,
                    'name': name
                }

            # Extract CostPlus field if present (for upgraded cost detection)
            cost_plus_pattern = r'\{Name = "(.*?)",.*?CostPlus = (-?\d+).*?\}'
            cost_matches = re.findall(cost_plus_pattern, content, re.DOTALL)
            for name, cost_plus in cost_matches:
                card_name = name.lower()
                if card_name in self._wiki_data:
                    self._wiki_data[card_name]['cost_plus'] = int(cost_plus)

            print(
                f"Loaded wiki data for {len(self._wiki_data)} cards",
                file=sys.stderr
            )

        except Exception as e:
            warnings.warn(
                f"Failed to load wiki data: {e}\n"
                f"Wiki parsing will be disabled."
            )
            self._wiki_data = {}

    def _parse_text_field_for_upgrade_values(self, text: str) -> Tuple[Optional[int], Optional[int]]:
        """
        Extract base and upgraded values from wiki Text field.

        Args:
            text: Text field containing upgrade values like "[8|10]"

        Returns:
            Tuple of (base_value, upgraded_value), or (None, None) if no match

        Examples:
            >>> _parse_text_field_for_upgrade_values("Deal [8|10] damage.")
            (8, 10)
            >>> _parse_text_field_for_upgrade_values("Gain [5|8] Block.")
            (5, 8)
            >>> _parse_text_field_for_upgrade_values("No values here")
            (None, None)
        """
        # Pattern to match [base|upgraded] format
        upgrade_pattern = r'\[(\d+)\|(\d+)\]'
        matches = re.findall(upgrade_pattern, text)

        if not matches:
            return None, None

        # Return the first match (most cards have only one upgrade pair)
        base_value, upgraded_value = matches[0]
        return int(base_value), int(upgraded_value)

    def _parse_text_field_for_damage_upgrade_values(self, text: str) -> Tuple[Optional[int], Optional[int]]:
        """
        Extract base and upgraded damage values from a wiki Text field.

        Wiki text can include upgrade pairs for debuff stacks, hit counts, or
        scaling amounts. Only pairs that directly replace the damage number in
        a damage clause should be treated as card damage.
        """
        upgrade_pattern = r'\[(\d+)\|(\d+)\]'
        for match in re.finditer(upgrade_pattern, text):
            clause_start = max(
                text.rfind('.', 0, match.start()),
                text.rfind('\n', 0, match.start()),
                text.rfind('\\n', 0, match.start()),
            )
            clause_start = 0 if clause_start < 0 else clause_start + 1

            clause_end_candidates = [
                index for index in (
                    text.find('.', match.end()),
                    text.find('\n', match.end()),
                    text.find('\\n', match.end()),
                ) if index != -1
            ]
            clause_end = min(clause_end_candidates) if clause_end_candidates else len(text)
            clause = text[clause_start:clause_end].lower()
            after_pair = clause[match.end() - clause_start:]

            if 'additional damage' in clause:
                continue
            if ('deal' in clause or 'deals' in clause) and re.match(r'\s*damage\b', after_pair):
                return int(match.group(1)), int(match.group(2))

        return None, None

    def _parse_text_field_for_block_upgrade_values(self, text: str) -> Tuple[Optional[int], Optional[int]]:
        """
        Extract base and upgraded block values from a wiki Text field.

        Wiki text can include upgrade pairs for non-block effects, such as
        Burning Pact's draw count. Only pairs in a clause that mentions Block
        should be treated as block values.
        """
        upgrade_pattern = r'\[(\d+)\|(\d+)\]'
        for match in re.finditer(upgrade_pattern, text):
            clause_start = max(
                text.rfind('.', 0, match.start()),
                text.rfind('\n', 0, match.start()),
                text.rfind('\\n', 0, match.start()),
            )
            clause_start = 0 if clause_start < 0 else clause_start + 1

            clause_end_candidates = [
                index for index in (
                    text.find('.', match.end()),
                    text.find('\n', match.end()),
                    text.find('\\n', match.end()),
                ) if index != -1
            ]
            clause_end = min(clause_end_candidates) if clause_end_candidates else len(text)
            clause = text[clause_start:clause_end].lower()

            if 'block' in clause:
                return int(match.group(1)), int(match.group(2))

        return None, None

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

        self._log_loaded_source_once()
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

        self._log_loaded_source_once()
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

        self._log_loaded_source_once()
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
        self._log_loaded_source_once()
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
        self._log_loaded_source_once()
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

        self._log_loaded_source_once()
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

        self._log_loaded_source_once()
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

        self._log_loaded_source_once()
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
        self._log_loaded_source_once()
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
        self._log_loaded_source_once()
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

        self._log_loaded_source_once()
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
        2. Check CARD_METADATA for X-cards and complex formulas (priority over wiki)
        3. Parse wiki-card-data.txt for upgrade values (static cards)
        4. Check CARD_METADATA for remaining hardcoded values
        5. Parse description with regex

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
        base_card_name, upgrade_count = _split_card_upgrade_suffix(card_name)
        is_upgraded = upgrade_count > 0

        # Stage 2: Check CARD_METADATA first for X-cards and complex formulas (priority over wiki)
        if base_card_name in CARD_METADATA:
            metadata = CARD_METADATA[base_card_name]
            # X-damage cards should always use CARD_METADATA, not wiki data
            if metadata.get('is_x_damage'):
                return 0  # X-damage cards have variable damage
            # Complex formula cards also use CARD_METADATA
            if 'reason' in metadata and 'scales with' in metadata['reason'].lower():
                damage = metadata.get('damage')
                upgraded_damage_meta = metadata.get('upgraded_damage')
                if is_upgraded and upgraded_damage_meta is not None:
                    return upgraded_damage_meta
                return damage

        # Stage 3: Parse wiki data for upgrade values (static cards only)
        self._load_wiki_data()  # Lazy load
        if self._wiki_data and base_card_name in self._wiki_data:
            wiki_entry = self._wiki_data[base_card_name]
            text = wiki_entry.get('text', '')
            base_damage, upgraded_damage = self._parse_text_field_for_damage_upgrade_values(text)
            if base_damage is not None:
                # Return appropriate value based on upgrade status
                return upgraded_damage if is_upgraded else base_damage

        # Stage 4: Check CARD_METADATA for remaining hardcoded values
        if base_card_name in CARD_METADATA:
            metadata = CARD_METADATA[base_card_name]
            damage = metadata.get('damage')
            upgraded_damage_meta = metadata.get('upgraded_damage')
            if is_upgraded and upgraded_damage_meta is not None:
                return upgraded_damage_meta
            return damage

        # Stage 5: Parse description with regex
        description = card_data.get('description', '').lower()
        match = re.search(r'deal (\d+) damage', description)
        if match:
            damage = int(match.group(1))
            if base_card_name == 'searing blow':
                damage += _searing_blow_upgrade_damage(upgrade_count)
            return damage

        return None

    def _parse_card_block(self, card_data: Dict[str, Any]) -> Optional[int]:
        """
        Extract base block value from card data using multi-stage approach.

        Stages:
        1. Check structured 'block' field (future-proof for StSExporter)
        2. Check CARD_METADATA for X-block cards (priority over wiki)
        3. Parse wiki-card-data.txt for upgrade values (static cards)
        4. Check CARD_METADATA for remaining hardcoded values
        5. Parse description with regex

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

        # Stage 1: Check structured field
        if 'block' in card_data:
            return int(card_data['block']) if card_data['block'] else None

        card_name = card_data.get('name', '').lower()
        is_upgraded = card_name.endswith('+')
        base_card_name = card_name.rstrip('+')  # Remove '+' for lookup

        # Stage 2: Check CARD_METADATA first for X-block cards (priority over wiki)
        if base_card_name in CARD_METADATA:
            metadata = CARD_METADATA[base_card_name]
            # X-block cards should always use CARD_METADATA, not wiki data
            if metadata.get('is_x_block'):
                return 0  # X-block cards have variable block

        # Stage 3: Parse wiki data for upgrade values (static cards only)
        self._load_wiki_data()  # Lazy load
        if self._wiki_data and base_card_name in self._wiki_data:
            wiki_entry = self._wiki_data[base_card_name]
            text = wiki_entry.get('text', '')
            base_block, upgraded_block = self._parse_text_field_for_block_upgrade_values(text)
            if base_block is not None:
                # Return appropriate value based on upgrade status
                return upgraded_block if is_upgraded else base_block

        # Stage 4: Check CARD_METADATA for remaining hardcoded values
        if base_card_name in CARD_METADATA:
            metadata = CARD_METADATA[base_card_name]
            block = metadata.get('block')
            upgraded_block_meta = metadata.get('upgraded_block')
            if is_upgraded and upgraded_block_meta is not None:
                return upgraded_block_meta
            return block

        # Stage 5: Parse description with regex
        description = card_data.get('description', '').lower()
        match = re.search(r'gain (\d+) block', description)
        if match:
            return int(match.group(1))

        return None

    def _is_card_aoe(self, card_data: Dict[str, Any]) -> bool:
        """
        Detect if card is an AOE (multi-target) attack.

        Uses multi-stage approach:
        1. Check CARD_METADATA first (for complex AOE cards)
        2. Check wiki data for AOE indicators in Text field (NEW)
        3. Check description for AOE keywords

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
        base_card_name = card_name.rstrip('+')  # Remove '+' for lookup

        # Stage 1: Check CARD_METADATA first (complex cards)
        if base_card_name in CARD_METADATA:
            return CARD_METADATA[base_card_name].get('aoe', False)

        # Stage 2: Check wiki data for AOE indicators (NEW)
        self._load_wiki_data()  # Lazy load
        if self._wiki_data and base_card_name in self._wiki_data:
            wiki_entry = self._wiki_data[base_card_name]
            text = wiki_entry.get('text', '').lower()
            aoe_keywords = ['all enemies', 'every enemy', 'each enemy']
            if any(keyword in text for keyword in aoe_keywords):
                return True

        # Stage 3: Check description for AOE keywords
        description = card_data.get('description', '').lower()
        aoe_keywords = ['all enemies', 'every enemy', 'each enemy']
        return any(keyword in description for keyword in aoe_keywords)

    # ===== Enhanced Monster Database Methods =====

    def _get_enhanced_monster_db(self):
        """
        Lazy-load the enhanced monster database.

        Returns:
            EnhancedMonsterDatabase instance
        """
        if self._enhanced_monster_db is None:
            try:
                from spirecomm.ai.heuristics.enhanced_monster_database import EnhancedMonsterDatabase
                self._enhanced_monster_db = EnhancedMonsterDatabase()
                print(
                    f"Enhanced monster database loaded: {len(self._enhanced_monster_db.get_all_monsters())} monsters",
                    file=sys.stderr
                )
            except Exception as e:
                warnings.warn(
                    f"Failed to load enhanced monster database: {e}\n"
                    f"Enhanced monster features will be disabled."
                )
                self._enhanced_monster_db = False  # Use False to indicate failed load
        return self._enhanced_monster_db

    def get_enhanced_monster_data(self, monster_name: str) -> Optional[Dict[str, Any]]:
        """
        Get enhanced monster data from Wiki.

        Args:
            monster_name: Name of the monster (e.g., "Cultist", "Lagavulin", "The Champ")

        Returns:
            Dictionary with enhanced monster data (moves, patterns, special mechanics, threat profile),
            or None if not found or database unavailable
        """
        db = self._get_enhanced_monster_db()
        if db and isinstance(db, object):  # Check if db loaded successfully (not False)
            return db.get_monster_data(monster_name)
        return None

    def get_monster_moves(self, monster_name: str) -> List[Dict[str, Any]]:
        """
        Get list of moves for a monster from Wiki data.

        Args:
            monster_name: Name of the monster

        Returns:
            List of move dictionaries with move_id, name, intent, damage, effect
        """
        db = self._get_enhanced_monster_db()
        if db and isinstance(db, object):
            return db.get_moves(monster_name)
        return []

    def get_monster_pattern(self, monster_name: str) -> Optional[Dict[str, Any]]:
        """
        Get move pattern information for a monster from Wiki data.

        Args:
            monster_name: Name of the monster

        Returns:
            Pattern dictionary with description, probabilities, constraints, phases
        """
        db = self._get_enhanced_monster_db()
        if db and isinstance(db, object):
            return db.get_pattern(monster_name)
        return None

    def get_monster_special_mechanics(self, monster_name: str) -> Optional[Dict[str, Any]]:
        """
        Get special mechanics for a monster from Wiki data.

        Args:
            monster_name: Name of the monster

        Returns:
            Special mechanics dictionary with type and additional details
            (summoner, hibernation, phase_change, death_split, etc.)
        """
        db = self._get_enhanced_monster_db()
        if db and isinstance(db, object):
            return db.get_special_mechanics(monster_name)
        return None

    def get_monster_threat_profile(self, monster_name: str) -> Optional[Dict[str, Any]]:
        """
        Get threat profile for a monster from Wiki data.

        Args:
            monster_name: Name of the monster

        Returns:
            Threat profile dictionary with base_threat, scaling_threat, special situation threats
        """
        db = self._get_enhanced_monster_db()
        if db and isinstance(db, object):
            return db.get_threat_profile(monster_name)
        return None

    def get_monster_type(self, monster_name: str) -> str:
        """
        Get monster type (normal, elite, boss) from Wiki data.

        Args:
            monster_name: Name of the monster

        Returns:
            Monster type string (defaults to "normal" if unavailable)
        """
        db = self._get_enhanced_monster_db()
        if db and isinstance(db, object):
            return db.get_monster_type(monster_name)
        return "normal"

    def predict_monster_moves(self, monster_name: str, current_turn: int,
                             monster_hp_percent: float) -> List[Dict[str, Any]]:
        """
        Predict next moves for a monster based on its Wiki pattern.

        Args:
            monster_name: Name of the monster
            current_turn: Current combat turn (1-indexed)
            monster_hp_percent: Current HP as percentage (0.0 to 1.0)

        Returns:
            List of predicted moves for next 3 turns with confidence scores
        """
        db = self._get_enhanced_monster_db()
        if db and isinstance(db, object):
            return db.predict_next_moves(monster_name, current_turn, monster_hp_percent)
        return []

    def calculate_monster_future_threat(self, monster_name: str, current_turn: int,
                                       monster_hp_percent: float, current_strength: int = 0) -> int:
        """
        Calculate future threat based on predicted moves and scaling from Wiki data.

        Args:
            monster_name: Name of the monster
            current_turn: Current combat turn
            monster_hp_percent: Current HP as percentage
            current_strength: Current monster Strength (for scaling)

        Returns:
            Future threat score (higher = more dangerous)
        """
        db = self._get_enhanced_monster_db()
        if db and isinstance(db, object):
            return db.calculate_future_threat(monster_name, current_turn, monster_hp_percent, current_strength)
        return 20  # Default fallback

    def is_monster_summoner(self, monster_name: str) -> bool:
        """Check if monster is a summoner type from Wiki data."""
        db = self._get_enhanced_monster_db()
        if db and isinstance(db, object):
            return db.is_summoner(monster_name)
        return False

    def is_monster_hibernating(self, monster_name: str, current_turn: int) -> bool:
        """Check if monster is currently hibernating from Wiki data."""
        db = self._get_enhanced_monster_db()
        if db and isinstance(db, object):
            return db.is_hibernating(monster_name, current_turn)
        return False

    def does_monster_have_phase_change(self, monster_name: str) -> bool:
        """Check if monster has phase change mechanics from Wiki data."""
        db = self._get_enhanced_monster_db()
        if db and isinstance(db, object):
            return db.has_phase_change(monster_name)
        return False

    def does_monster_have_death_split(self, monster_name: str) -> bool:
        """Check if monster splits on death from Wiki data."""
        db = self._get_enhanced_monster_db()
        if db and isinstance(db, object):
            return db.has_death_split(monster_name)
        return False

    def get_monster_recommended_strategy(self, monster_name: str) -> Optional[Dict[str, Any]]:
        """
        Get recommended strategy for fighting a monster from Wiki data.

        Args:
            monster_name: Name of the monster

        Returns:
            Strategy dictionary with primary, secondary, and note
        """
        db = self._get_enhanced_monster_db()
        if db and isinstance(db, object):
            return db.get_recommended_strategy(monster_name)
        return None

    def get_monster_minions(self, monster_name: str) -> List[str]:
        """
        Get list of minions a monster can summon from Wiki data.

        Args:
            monster_name: Name of the monster

        Returns:
            List of minion names
        """
        db = self._get_enhanced_monster_db()
        if db and isinstance(db, object):
            return db.get_minions(monster_name)
        return []

    def is_monster_duo_boss(self, monster_name: str) -> bool:
        """Check if monster is a duo boss (two monsters fighting together) from Wiki data."""
        db = self._get_enhanced_monster_db()
        if db and isinstance(db, object):
            return db.is_duo_boss(monster_name)
        return False

    def get_monster_timing_hints(self, monster_name: str) -> Optional[Dict[str, Any]]:
        """
        Get timing strategy hints for a monster from Wiki data.

        Args:
            monster_name: Name of the monster

        Returns:
            Timing hints dictionary with safe_turn_indicators, spike_turn_indicators, etc.
        """
        db = self._get_enhanced_monster_db()
        if db and isinstance(db, object):
            return db.get_timing_hints(monster_name)
        return None

    def is_monster_safe_turn(self, monster_name: str, current_turn: int,
                            monster_hp_percent: float = 1.0) -> bool:
        """
        Check if current turn is a "safe turn" for a monster (buffing/defending).

        Args:
            monster_name: Name of the monster
            current_turn: Current combat turn
            monster_hp_percent: Monster HP as percentage (for phase detection)

        Returns:
            True if monster is not attacking this turn
        """
        db = self._get_enhanced_monster_db()
        if db and isinstance(db, object):
            return db.is_safe_turn(monster_name, current_turn, monster_hp_percent)
        return False

    def get_monster_big_attack_pattern(self, monster_name: str) -> List[Dict[str, Any]]:
        """
        Get big attack patterns for a monster from Wiki data.

        Args:
            monster_name: Name of the monster

        Returns:
            List of big attack patterns with turn numbers and damage
        """
        db = self._get_enhanced_monster_db()
        if db and isinstance(db, object):
            return db.get_big_attack_pattern(monster_name)
        return []


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
