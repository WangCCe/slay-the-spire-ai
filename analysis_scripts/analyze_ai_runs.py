"""
分析 Slay the Spire AI 游戏记录

用法:
    cd D:/SteamLibrary/steamapps/common/SlayTheSpire
    python D:/PycharmProjects/slay-the-spire-ai/analysis_scripts/analyze_ai_runs.py

功能:
    - 读取 runs/ai_games.txt 获取 AI 游戏列表
    - 统计胜率、平均楼层等
    - 显示最近的 AI 游戏记录
"""

import json
from pathlib import Path
from datetime import datetime
from collections import Counter

# 配置路径 (从游戏目录运行，所以用相对路径)
DEFAULT_GAME_DIR = Path(r"D:\\SteamLibrary\\steamapps\\common\\SlayTheSpire")
CHARACTER = "IRONCLAD"  # 修改这个来分析其他角色


def load_ai_games(ai_games_file: Path):
    """读取 AI 游戏列表"""
    if not ai_games_file.exists():
        print(f"未找到 AI 游戏记录: {ai_games_file}")
        print("请先运行 AI，让它记录一些游戏")
        return []

    with open(ai_games_file) as f:
        return [line.strip() for line in f if line.strip()]


def load_run_data(runs_dir: Path, character: str, game_timestamp):
    """读取单个游戏的详细数据（时间戳模糊匹配）"""
    # 查找最接近的 .run 文件（允许 5 分钟误差）
    timestamp_int = int(game_timestamp)

    # 列出所有 .run 文件，找最接近的
    closest_file = None
    min_diff = float('inf')

    for run_file in (runs_dir / character).glob("*.run"):
        # 从文件名提取时间戳
        try:
            file_timestamp = int(run_file.stem)
            time_diff = abs(file_timestamp - timestamp_int)
            if time_diff < min_diff and time_diff < 300:  # 5 分钟内
                min_diff = time_diff
                closest_file = run_file
        except ValueError:
            continue

    if closest_file:
        with open(closest_file) as f:
            return json.load(f)
    return None


def analyze_ai_games(game_dir: Path, character: str):
    """分析 AI 游戏数据"""
    runs_dir = game_dir / "runs"
    ai_games_file = runs_dir / "ai_games.txt"
    ai_game_ids = load_ai_games(ai_games_file)

    if not ai_game_ids:
        return

    print(f"\n找到 {len(ai_game_ids)} 局 AI 游戏")
    print("=" * 60)

    # 统计数据
    victories = 0
    floors = []
    playtimes = []
    relics_counts = []
    death_causes = Counter()

    # 最近的游戏
    recent_games = []

    for game_id in ai_game_ids[-10:]:  # 最近10局
        data = load_run_data(runs_dir, character, game_id)
        if not data:
            continue

        is_victory = data.get('victory', False)
        floor = data.get('floor_reached', 0)
        playtime = data.get('playtime', 0)
        relics = len(data.get('relics', []))

        if is_victory:
            victories += 1

        floors.append(floor)
        playtimes.append(playtime)
        relics_counts.append(relics)

        # 死亡原因（从最后一场战斗获取）
        damage_taken = data.get('damage_taken', [])
        if damage_taken:
            last_fight = damage_taken[-1]
            enemies = last_fight.get('enemies', 'Unknown')
            death_causes[enemies] += 1

        recent_games.append({
            'id': game_id,
            'floor': floor,
            'victory': is_victory,
            'time': playtime,
            'relics': relics
        })

    # 打印统计
    win_rate = victories / len(ai_game_ids) * 100
    avg_floor = sum(floors) / len(floors) if floors else 0
    avg_time = sum(playtimes) / len(playtimes) if playtimes else 0

    print(f"\n总体统计:")
    print(f"  胜率: {win_rate:.1f}% ({victories}/{len(ai_game_ids)})")
    print(f"  平均楼层: {avg_floor:.1f}")
    print(f"  平均时长: {avg_time:.0f} 秒")
    print(f"  平均遗物: {sum(relics_counts) / len(relics_counts):.1f} 个")

    # 死亡原因 TOP 5
    print(f"\n死亡原因 TOP 5:")
    for enemies, count in death_causes.most_common(5):
        print(f"  {enemies}: {count} 次")

    # 最近的游戏
    print(f"\n最近 {len(recent_games)} 局:")
    for game in reversed(recent_games):
        result = "WIN" if game['victory'] else "LOSS"
        print(f"  {game['id']}: {result} | 楼层 {game['floor']} | "
              f"{game['time']}秒 | {game['relics']} 遗物")

    print("\n" + "=" * 60)


def show_all_ai_games(game_dir: Path, character: str):
    """显示所有 AI 游戏（简化版）"""
    runs_dir = game_dir / "runs"
    ai_games_file = runs_dir / "ai_games.txt"
    ai_game_ids = load_ai_games(ai_games_file)

    if not ai_game_ids:
        return

    print(f"\n所有 AI 游戏列表 ({len(ai_game_ids)} 局):")
    print("=" * 60)

    for game_id in ai_game_ids:
        data = load_run_data(runs_dir, character, game_id)
        if data:
            floor = data.get('floor_reached', 0)
            victory = "WIN" if data.get('victory', False) else "LOSS"
            print(f"  {game_id}: {victory} | 楼层 {floor}")

    print("=" * 60)


if __name__ == "__main__":
    import sys

    game_dir = DEFAULT_GAME_DIR
    args = sys.argv[1:]
    if "--game-dir" in args:
        idx = args.index("--game-dir")
        if idx + 1 < len(args):
            game_dir = Path(args[idx + 1])
            args.pop(idx + 1)
            args.pop(idx)
    if "--character" in args:
        idx = args.index("--character")
        if idx + 1 < len(args):
            CHARACTER = args[idx + 1]
            args.pop(idx + 1)
            args.pop(idx)

    if args and args[0] == "--all":
        show_all_ai_games(game_dir, CHARACTER)
    else:
        analyze_ai_games(game_dir, CHARACTER)
