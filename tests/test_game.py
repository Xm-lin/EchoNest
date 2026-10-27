import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from game import EVENTS, QUESTS, relationship
assert len(EVENTS) >= 6
assert len(QUESTS) == 3
assert relationship(0) == '初識'
assert relationship(25) == '熟悉'
assert relationship(55) == '信任'
assert relationship(80) == '知己'
for event in EVENTS:
    assert len(event['choices']) == 3
    assert '{name}' in event['story']
    for label, affection, xp, item, ending in event['choices']:
        assert label and item and ending
        assert 0 <= affection <= 5
        assert 1 <= xp <= 30
print('Game content tests passed')
