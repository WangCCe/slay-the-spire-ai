import json
import os
from typing import Dict, List, Any
import re
from pathlib import Path


def load_items_json(export_path: str) -> Dict[str, List[Dict[str, Any]]]:
    """
    Load items.json from the export directory.
    
    Args:
        export_path: Path to the Slay the Spire export directory
    
    Returns:
        Dictionary containing game data from items.json
    """
    items_path = os.path.join(export_path, "items.json")
    with open(items_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_markdown_table(markdown_path: str) -> List[Dict[str, str]]:
    """
    Load a markdown table from a file and convert it to a list of dictionaries.
    
    Args:
        markdown_path: Path to the markdown file
    
    Returns:
        List of dictionaries representing the table rows
    """
    with open(markdown_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Split into lines and remove empty lines
    lines = [line.strip() for line in content.split("\n") if line.strip()]
    
    # Find the header and data rows
    header_line = None
    separator_line = None
    data_lines = []
    
    for i, line in enumerate(lines):
        if line.startswith("|"):
            header_line = line
            separator_line = lines[i + 1]
            data_lines = lines[i + 2:]
            break
    
    if not header_line or not separator_line:
        return []
    
    # Parse headers
    headers = [h.strip() for h in header_line.split("|")[1:-1]]
    
    # Parse data rows
    rows = []
    for line in data_lines:
        if not line.startswith("|"):
            continue
        
        values = [v.strip() for v in line.split("|")[1:-1]]
        if len(values) != len(headers):
            continue
        
        row = {headers[i]: values[i] for i in range(len(headers))}
        rows.append(row)
    
    return rows


def load_cards_markdown(export_path: str) -> List[Dict[str, str]]:
    """
    Load cards.md from the export directory.
    
    Args:
        export_path: Path to the Slay the Spire export directory
    
    Returns:
        List of dictionaries representing cards
    """
    cards_path = os.path.join(export_path, "cards.md")
    return load_markdown_table(cards_path)


def load_relics_markdown(export_path: str) -> List[Dict[str, str]]:
    """
    Load relics.md from the export directory.
    
    Args:
        export_path: Path to the Slay the Spire export directory
    
    Returns:
        List of dictionaries representing relics
    """
    relics_path = os.path.join(export_path, "relics.md")
    return load_markdown_table(relics_path)


def load_creatures_markdown(export_path: str) -> List[Dict[str, str]]:
    """
    Load creatures.md from the export directory.
    
    Args:
        export_path: Path to the Slay the Spire export directory
    
    Returns:
        List of dictionaries representing creatures
    """
    creatures_path = os.path.join(export_path, "creatures.md")
    return load_markdown_table(creatures_path)


class GameDataLoader:
    """
    A loader for Slay the Spire game data from the export directory.
    """
    
    def __init__(self, export_path: str = "D:\\SteamLibrary\\steamapps\\common\\SlayTheSpire\\export"):
        """
        Initialize the game data loader.
        
        Args:
            export_path: Path to the Slay the Spire export directory
        """
        self.export_path = export_path
        self.items_data = None
        self.cards_markdown = None
        self.relics_markdown = None
        self.creatures_markdown = None
        self._load_all_data()
    
    def _load_all_data(self):
        """Load all game data files."""
        self.items_data = load_items_json(self.export_path)
        self.cards_markdown = load_cards_markdown(self.export_path)
        self.relics_markdown = load_relics_markdown(self.export_path)
        self.creatures_markdown = load_creatures_markdown(self.export_path)
    
    def get_card_by_name(self, name: str, upgraded: bool = False) -> Dict[str, Any]:
        """
        Get card information by name.
        
        Args:
            name: Card name
            upgraded: Whether to get the upgraded version
        
        Returns:
            Dictionary containing card information, or empty dict if not found
        """
        # Check in items.json first
        for card in self.items_data.get("cards", []):
            card_name = card.get("name", "")
            if upgraded and card_name == f"{name}+":
                return card
            elif not upgraded and card_name == name:
                return card
        
        # Fallback to markdown data
        for card in self.cards_markdown:
            if card.get("Name") == name:
                return card
        
        return {}
    
    def get_relic_by_name(self, name: str) -> Dict[str, str]:
        """
        Get relic information by name.
        
        Args:
            name: Relic name
        
        Returns:
            Dictionary containing relic information, or empty dict if not found
        """
        for relic in self.relics_markdown:
            if relic.get("Name") == name:
                return relic
        return {}
    
    def get_creature_by_name(self, name: str) -> Dict[str, str]:
        """
        Get creature information by name.
        
        Args:
            name: Creature name
        
        Returns:
            Dictionary containing creature information, or empty dict if not found
        """
        for creature in self.creatures_markdown:
            if creature.get("Name") == name:
                return creature
        return {}
    
    def get_all_cards(self) -> List[Dict[str, Any]]:
        """
        Get all cards from items.json.
        
        Returns:
            List of dictionaries representing all cards
        """
        return self.items_data.get("cards", [])
    
    def get_all_relics(self) -> List[Dict[str, str]]:
        """
        Get all relics from relics.md.
        
        Returns:
            List of dictionaries representing all relics
        """
        return self.relics_markdown
    
    def get_all_creatures(self) -> List[Dict[str, str]]:
        """
        Get all creatures from creatures.md.
        
        Returns:
            List of dictionaries representing all creatures
        """
        return self.creatures_markdown
    
    def refresh_data(self):
        """Reload all game data files."""
        self._load_all_data()


# Create a global instance of the GameDataLoader
default_export_path = "D:\\SteamLibrary\\steamapps\\common\\SlayTheSpire\\export"
game_data = None


def initialize_game_data(export_path: str = default_export_path):
    """
    Initialize the global game data instance.
    
    Args:
        export_path: Path to the Slay the Spire export directory
    """
    global game_data
    game_data = GameDataLoader(export_path)


# Initialize the game data when the module is imported
if os.path.exists(default_export_path):
    initialize_game_data()
