#!/usr/bin/env python3
"""
分析RL训练的整体进度和性能

用法:
    python analysis_scripts/analyze_rl_training_progress.py

输出:
    - Episode数量
    - Checkpoint信息
    - 游戏表现统计
    - 胜率和进度
"""

import re
import os
from pathlib import Path

LOG_PATH = r"D:\SteamLibrary\steamapps\common\SlayTheSpire\ai_debug.log"
CHECKPOINT_DIR = r"D:\SteamLibrary\steamapps\common\SlayTheSpire\checkpoints"


def parse_episodes(log_path):
    """解析日志中的游戏记录"""
    episodes = []

    with open(log_path, 'r', encoding='utf-8') as f:
        for line in f:
            # 查找游戏开始
            if '[TRACKING] Starting new run' in line:
                episodes.append({'start': line, 'floor_reached': 0, 'victory': False, 'killed_by': None})

            # 查找到达的层数
            elif '[TRACKING] Floor' in line and 'Starting combat' in line and episodes:
                floor_match = re.search(r'Floor (\d+)', line)
                if floor_match:
                    episodes[-1]['floor_reached'] = max(episodes[-1]['floor_reached'], int(floor_match.group(1)))

            # 查找游戏结束
            elif '[GAME_OVER]' in line or 'Game Summary' in line:
                if episodes:
                    if 'victory=True' in line or 'VICTORY' in line:
                        episodes[-1]['victory'] = True

                    if 'killed_by=' in line:
                        killed_match = re.search(r'killed_by=(\S+)', line)
                        if killed_match:
                            episodes[-1]['killed_by'] = killed_match.group(1)

    return episodes


def analyze_checkpoints(checkpoint_dir):
    """分析checkpoint文件"""
    if not os.path.exists(checkpoint_dir):
        return {'count': 0, 'latest': None, 'files': []}

    checkpoint_files = []
    for file in os.listdir(checkpoint_dir):
        if file.endswith('.pth'):
            file_path = os.path.join(checkpoint_dir, file)
            mtime = os.path.getmtime(file_path)
            size_mb = os.path.getsize(file_path) / (1024 * 1024)
            checkpoint_files.append({
                'name': file,
                'mtime': mtime,
                'size_mb': size_mb,
                'episode': re.search(r'ep(\d+)', file)
            })

    checkpoint_files.sort(key=lambda x: x['mtime'], reverse=True)

    return {
        'count': len(checkpoint_files),
        'latest': checkpoint_files[0] if checkpoint_files else None,
        'files': checkpoint_files
    }


def parse_combat_stats(log_path):
    """解析战斗统计"""
    stats = {
        'total_damage_dealt': 0,
        'total_damage_taken': 0,
        'total_turns': 0,
        'combats': 0
    }

    with open(log_path, 'r', encoding='utf-8') as f:
        for line in f:
            # 查找伤害信息
            if '[RL_REWARD]' in line and 'dmg=' in line:
                dmg_match = re.search(r'dmg=([\d.]+)', line)
                if dmg_match:
                    stats['total_damage_dealt'] += float(dmg_match.group(1))

            # 累计回合数（粗略估计）
            if '[RL_CHOICE]' in line and 'turn=' in line:
                turn_match = re.search(r'turn=(\d+)', line)
                if turn_match:
                    stats['total_turns'] = max(stats['total_turns'], int(turn_match.group(1)))

            # 战斗计数（每次combat开始）
            if '[TRACKING] Starting combat' in line:
                stats['combats'] += 1

    return stats


def main():
    print("=" * 80)
    print("RL训练进度分析")
    print("=" * 80)
    print()

    # 分析episodes
    print("【游戏统计】")
    episodes = parse_episodes(LOG_PATH)

    if episodes:
        print(f"  总游戏数: {len(episodes)}")

        victories = sum(1 for e in episodes if e['victory'])
        print(f"  胜利: {victories} ({victories/len(episodes)*100:.1f}%)")
        print(f"  失败: {len(episodes) - victories}")

        avg_floor = sum(e['floor_reached'] for e in episodes) / len(episodes)
        max_floor = max(e['floor_reached'] for e in episodes)
        print(f"  平均层数: {avg_floor:.1f}")
        print(f"  最远层数: {max_floor}")

        # 死因统计
        death_causes = {}
        for e in episodes:
            if not e['victory'] and e['killed_by']:
                death_causes[e['killed_by']] = death_causes.get(e['killed_by'], 0) + 1

        if death_causes:
            print(f"\n  主要死因:")
            for cause, count in sorted(death_causes.items(), key=lambda x: -x[1])[:5]:
                print(f"    - {cause}: {count}次")
    else:
        print("  [WARNING] 未找到游戏记录")
    print()

    # 分析checkpoints
    print("【Checkpoint信息】")
    ckpt_info = analyze_checkpoints(CHECKPOINT_DIR)

    if ckpt_info['count'] > 0:
        print(f"  Checkpoint数量: {ckpt_info['count']}")
        latest = ckpt_info['latest']
        if latest:
            import datetime
            mtime_dt = datetime.datetime.fromtimestamp(latest['mtime'])
            print(f"  最新: {latest['name']}")
            print(f"  更新时间: {mtime_dt.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"  文件大小: {latest['size_mb']:.1f} MB")

            if latest['episode']:
                print(f"  Episode: {latest['episode'].group(1)}")
    else:
        print("  [WARNING] 未找到checkpoint文件")
        print("  训练可能尚未开始或未到保存周期")
    print()

    # 战斗统计
    print("【战斗表现】")
    combat_stats = parse_combat_stats(LOG_PATH)

    if combat_stats['combats'] > 0:
        print(f"  总战斗数: {combat_stats['combats']}")
        print(f"  总回合数: {combat_stats['total_turns']}")
        print(f"  总造成伤害: {combat_stats['total_damage_dealt']:.0f}")

        if combat_stats['combats'] > 0:
            avg_turns_per_combat = combat_stats['total_turns'] / combat_stats['combats']
            print(f"  平均每战回合: {avg_turns_per_combat:.1f}")
    else:
        print("  [WARNING] 战斗数据不足")
    print()

    # 训练建议
    print("=" * 80)
    print("[训练建议]")

    if not episodes:
        print("  - 开始训练后，等待至少5局游戏再查看统计")
    elif len(episodes) < 20:
        print(f"  - 当前只有{len(episodes)}局游戏，处于早期探索阶段")
        print("  - 继续训练到100局后再评估策略")
    elif len(episodes) < 100:
        print(f"  - 已完成{len(episodes)}局，开始形成基础策略")
        print("  - 观察卡牌选择模式是否趋于稳定")
    else:
        print(f"  - 已完成{len(episodes)}局，进入成熟阶段")
        print("  - 检查胜率和平均层数是否有提升")

    if ckpt_info['count'] == 0:
        print("  - Checkpoint尚未生成，继续训练")
    print()


if __name__ == '__main__':
    main()
