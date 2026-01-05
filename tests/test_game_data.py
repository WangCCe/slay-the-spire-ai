from spirecomm.data.loader import game_data_loader

# Load game data
game_data_loader.load_data()

# Check if data loaded successfully
print('Data loaded:', bool(game_data_loader._cards))
print(f'Number of cards loaded: {len(game_data_loader._cards) if game_data_loader._cards else 0}')

# Test some card data
print('\nTest cards in data:')
test_cards = ['defend', 'strike', 'corruption', 'second wind', 'demon form']
for card_name in test_cards:
    data = game_data_loader.get_card_data(card_name)
    print(f'{card_name}: {data is not None}')
    if data:
        print(f'  Description: {data.get("description", "")}')
        print(f'  Type: {data.get("type", "")}')
        print(f'  Color: {data.get("color", "")}')
