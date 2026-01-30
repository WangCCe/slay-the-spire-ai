#!/usr/bin/env python3
"""
分析纯RL训练的卡牌选择策略

用法:
    python analysis_scripts/analyze_rl_card_choices.py

输出:
    - 卡牌选择统计
    - 选择vs跳过比例
    - 按稀有度的选择分布
    - 时间趋势分析
"""

import re
from collections import Counter, defaultdict
from datetime import datetime

LOG_PATH = r"D:\SteamLibrary\steamapps\common\SlayTheSpire\ai_debug.log"


def parse_card_choices(log_path):
    """解析日志中的卡牌选择记录"""
    choices = []

    with open(log_path, 'r', encoding='utf-8') as f:
        for line in f:
            if '[CARD_CHOICE_PURE_RL]' in line:
                # 解析行，例如:
                # 2026-01-30 22:31:33,865 - INFO - [CARD_CHOICE_PURE_RL] chosen=Inflame candidates=Flex(COMMON), Inflame(UNCOMMON), Iron Wave(COMMON) [no heuristic reward - network learns from gameplay]

                # 提取时间
                time_match = re.search(r'(\d{2}:\d{2}:\d{2})', line)
                timestamp = time_match.group(1) if time_match else "00:00:00"

                # 提取chosen
                chosen_match = re.search(r'chosen=([^\s]+)', line)
                chosen = chosen_match.group(1) if chosen_match else "UNKNOWN"

                # 提取candidates
                candidates_match = re.search(r'candidates=(.+?) \[no heuristic', line)
                if candidates_match:
                    candidates_str = candidates_match.group(1)
                    # 解析每张卡的稀有度
                    candidates = []
                    for card_str in candidates_str.split(', '):
                        rarity_match = re.search(r'\((\w+)\)', card_str)
                        rarity = rarity_match.group(1) if rarity_match else "UNKNOWN"
                        card_name = card_str.split('(')[0].strip()
                        candidates.append({
                            'name': card_name,
                            'rarity': rarity
                        })

                    choices.append({
                        'timestamp': timestamp,
                        'chosen': chosen,
                        'candidates': candidates,
                        'is_skip': chosen == 'SKIP'
                    })

    return choices


def analyze_choices(choices):
    """分析卡牌选择数据"""

    print("=" * 80)
    print("纯RL训练 - 卡牌选择分析报告")
    print("=" * 80)
    print(f"总决策数: {len(choices)}")
    print()

    # 1. 选择vs跳过统计
    skip_count = sum(1 for c in choices if c['is_skip'])
    pick_count = len(choices) - skip_count

    print("【选择 vs 跳过】")
    print(f"  选择卡牌: {pick_count} ({pick_count/len(choices)*100:.1f}%)")
    print(f"  跳过所有: {skip_count} ({skip_count/len(choices)*100:.1f}%)")
    print()

    # 2. 按稀有度统计被选中的卡牌
    chosen_by_rarity = Counter()
    for choice in choices:
        if not choice['is_skip']:
            # 找到被选中卡牌的稀有度
            for card in choice['candidates']:
                if card['name'] == choice['chosen']:
                    chosen_by_rarity[card['rarity']] += 1
                    break

    print("【被选卡牌的稀有度分布】")
    for rarity in ['BASIC', 'COMMON', 'UNCOMMON', 'RARE', 'SPECIAL']:
        count = chosen_by_rarity.get(rarity, 0)
        if count > 0:
            pct = count / pick_count * 100 if pick_count > 0 else 0
            print(f"  {rarity}: {count} ({pct:.1f}%)")
    print()

    # 3. 最常被选中的卡牌
    chosen_cards = [c['chosen'] for c in choices if not c['is_skip']]
    top_cards = Counter(chosen_cards).most_common(10)

    print("【最常被选中的卡牌 TOP 10】")
    for i, (card_name, count) in enumerate(top_cards, 1):
        pct = count / pick_count * 100 if pick_count > 0 else 0
        print(f"  {i}. {card_name}: {count}次 ({pct:.1f}%)")
    print()

    # 4. 分析跳过决策 - 跳过了什么质量的卡牌
    skip_with_rare = 0
    skip_with_uncommon = 0
    skip_with_all_common = 0

    for choice in choices:
        if choice['is_skip']:
            rarities = [card['rarity'] for card in choice['candidates']]
            if 'RARE' in rarities:
                skip_with_rare += 1
            elif 'UNCOMMON' in rarities:
                skip_with_uncommon += 1
            elif all(r in ['COMMON', 'BASIC'] for r in rarities):
                skip_with_all_common += 1

    print("【跳过决策分析】")
    print(f"  跳过包含RARE的选择: {skip_with_rare}次")
    print(f"  跳过包含UNCOMMON的选择: {skip_with_uncommon}次")
    print(f"  跳过全COMMON/BASIC: {skip_with_all_common}次")
    print()

    # 5. 探索性分析 - 选择的多样性
    unique_cards = len(set(chosen_cards))
    print("【探索性分析】")
    print(f"  不同卡牌种类: {unique_cards}")
    print(f"  平均每局选择卡牌: {pick_count/len(choices)*100:.1f}%")
    print()

    # 6. 时间趋势 - 将选择分为前后两半
    mid_point = len(choices) // 2
    first_half_skip = sum(1 for c in choices[:mid_point] if c['is_skip'])
    second_half_skip = sum(1 for c in choices[mid_point:] if c['is_skip'])

    print("【时间趋势】")
    print(f"  前半段跳过率: {first_half_skip/mid_point*100:.1f}% ({first_half_skip}/{mid_point})")
    if len(choices) > mid_point:
        print(f"  后半段跳过率: {second_half_skip/(len(choices)-mid_point)*100:.1f}% ({second_half_skip}/{len(choices)-mid_point})")

        trend = second_half_skip - first_half_skip
        if trend > 0:
            print(f"  趋势: 跳过率增加 {trend/mid_point*100:.1f}% (可能变得更保守)")
        elif trend < 0:
            print(f"  趋势: 跳过率降低 {abs(trend)/mid_point*100:.1f}% (可能变得更积极)")
        else:
            print(f"  趋势: 跳过率保持稳定")
    print()

    return {
        'total': len(choices),
        'pick_count': pick_count,
        'skip_count': skip_count,
        'chosen_by_rarity': chosen_by_rarity,
        'top_cards': top_cards,
    }


def main():
    print(f"读取日志: {LOG_PATH}")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    choices = parse_card_choices(LOG_PATH)

    if not choices:
        print("❌ 未找到任何卡牌选择记录")
        print("提示: 确保日志路径正确，并且已经运行过游戏")
        return

    stats = analyze_choices(choices)

    print("=" * 80)
    print("[建议]")
    if stats['skip_count'] > stats['pick_count']:
        print("  - 当前跳过率较高，AI可能过于保守")
        print("  - 这是正常的早期探索行为，继续训练观察")
    elif stats['skip_count'] < stats['pick_count'] * 0.3:
        print("  - 当前选择率较高，AI可能过于激进")
        print("  - 注意观察牌组是否膨胀过快")
    else:
        print("  - 选择和跳过的比例比较平衡")
        print("  - 继续训练，观察长期趋势")
    print()


if __name__ == '__main__':
    main()
