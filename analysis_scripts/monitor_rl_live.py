#!/usr/bin/env python3
"""
实时监控RL训练 - 持续追踪最新决策

用法:
    python analysis_scripts/monitor_rl_live.py

功能:
    - 监控最新的卡牌选择
    - 显示最近的游戏结果
    - 实时更新统计
"""

import time
import os
from pathlib import Path

LOG_PATH = r"D:\SteamLibrary\steamapps\common\SlayTheSpire\ai_debug.log"
CHECK_INTERVAL = 30  # 秒


def get_file_size(filepath):
    """获取文件大小"""
    if os.path.exists(filepath):
        return os.path.getsize(filepath)
    return 0


def tail_log(filepath, lines=50):
    """读取日志文件最后N行"""
    if not os.path.exists(filepath):
        return []

    with open(filepath, 'r', encoding='utf-8') as f:
        all_lines = f.readlines()
        return all_lines[-lines:]


def parse_recent_card_choices(log_lines):
    """解析最近的卡牌选择"""
    choices = []
    for line in log_lines:
        if '[CARD_CHOICE_PURE_RL]' in line:
            # 简化解析
            if 'chosen=SKIP' in line:
                choices.append(('SKIP', 'SKIPPED'))
            elif 'chosen=' in line:
                import re
                match = re.search(r'chosen=([^\s]+)', line)
                if match:
                    card_name = match.group(1)
                    # 提取稀有度
                    rarity = 'UNKNOWN'
                    candidates_match = re.search(r'candidates=(.+?) \[', line)
                    if candidates_match:
                        for card in candidates_match.group(1).split(', '):
                            if card_name in card:
                                rarity_match = re.search(r'\((\w+)\)', card)
                                if rarity_match:
                                    rarity = rarity_match.group(1)
                    choices.append((card_name, rarity))
    return choices


def parse_recent_combats(log_lines):
    """解析最近的战斗结果"""
    combats = []
    for line in log_lines:
        if '[GAME_OVER]' in line or 'Game Summary' in line:
            if 'floor=' in line:
                import re
                floor_match = re.search(r'floor=(\d+)', line)
                victory = 'victory=True' in line or 'VICTORY' in line
                if floor_match:
                    combats.append({
                        'floor': int(floor_match.group(1)),
                        'victory': victory
                    })
    return combats


def display_recent_stats(choices, combats):
    """显示最近统计"""
    print("\n" + "=" * 80)
    print("[实时训练监控]")
    print("=" * 80)

    # 最近卡牌选择
    if choices:
        print(f"\n【最近 {len(choices)} 次卡牌选择】")
        for i, (card, rarity) in enumerate(choices[-10:], 1):
            skip_symbol = "⏭️ " if card == 'SKIP' else "✅ "
            print(f"  {i}. {skip_symbol}{card} ({rarity})")

        # 统计
        skip_count = sum(1 for c, _ in choices if c == 'SKIP')
        pick_count = len(choices) - skip_count
        print(f"\n  选择率: {pick_count}/{len(choices)} = {pick_count/len(choices)*100:.1f}%")
    else:
        print("\n【卡牌选择】暂无数据")

    # 最近游戏
    if combats:
        print(f"\n【最近 {len(combats)} 局游戏】")
        victories = sum(1 for c in combats if c['victory'])
        avg_floor = sum(c['floor'] for c in combats) / len(combats)

        for i, combat in enumerate(combats[-5:], 1):
            status = "[VICTORY]" if combat['victory'] else "[DEFEAT]"
            print(f"  {i}. Floor {combat['floor']} - {status}")

        print(f"\n  胜率: {victories}/{len(combats)} = {victories/len(combats)*100:.1f}%")
        print(f"  平均层数: {avg_floor:.1f}")
    else:
        print("\n【游戏记录】暂无数据")


def main():
    print("=" * 80)
    print("RL训练实时监控")
    print("=" * 80)
    print(f"日志文件: {LOG_PATH}")
    print(f"刷新间隔: {CHECK_INTERVAL}秒")
    print("\n按 Ctrl+C 停止监控\n")

    last_size = get_file_size(LOG_PATH)
    iteration = 0

    try:
        while True:
            iteration += 1
            current_size = get_file_size(LOG_PATH)

            # 检查文件是否有更新
            if current_size != last_size:
                print(f"\n[UPDATE] 检测到日志更新 (Iteration #{iteration})")
                last_size = current_size

                # 读取最新日志
                log_lines = tail_log(LOG_PATH, 200)

                # 解析数据
                choices = parse_recent_card_choices(log_lines)
                combats = parse_recent_combats(log_lines)

                # 显示
                display_recent_stats(choices, combats)
            else:
                print(f"[WAIT] 等待新日志... (#{iteration}, 大小: {current_size/1024/1024:.2f} MB)")

            time.sleep(CHECK_INTERVAL)

    except KeyboardInterrupt:
        print("\n\n监控已停止")
        print("查看完整分析:")
        print("  python analysis_scripts/analyze_rl_card_choices.py")
        print("  python analysis_scripts/analyze_rl_training_progress.py")


if __name__ == '__main__':
    main()
