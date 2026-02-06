#!/usr/bin/env python3
"""
Analyze training progress by bucketing recent Slay the Spire runs.

Usage:
    python analyze_progress.py
    python analyze_progress.py --count 500 --bucket 50
    python analyze_progress.py --character IRONCLAD
"""

import argparse
import base64
import hashlib
import hmac
import json
import logging
import os
import sys
import time
import urllib.parse
from datetime import datetime
from pathlib import Path

import requests

# Setup logging
LOG_FILE = "./ai_cron.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


DEFAULT_RUNS_DIR_WSL = "/mnt/d/SteamLibrary/steamapps/common/SlayTheSpire/runs"
DEFAULT_RUNS_DIR_WIN = r"D:\SteamLibrary\steamapps\common\SlayTheSpire\runs"

# 飞书机器人配置
FEISHU_WEBHOOK = "https://open.feishu.cn/open-apis/bot/v2/hook/9bca16ff-61ee-4d4e-8454-67bc4b3b86d9"
FEISHU_SIGN_KEY = "cQXnaP1F4TPKV9HLk0VgLe"


def load_run(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def parse_local_time(value):
    if not value or len(value) < 12:
        return None
    try:
        return datetime.strptime(value[:12], "%Y%m%d%H%M")
    except ValueError:
        return None


def format_time(value):
    if not value:
        return "unknown"
    return value.strftime("%m-%d %H:%M")


def collect_runs(runs_dir, character, count):
    runs_path = Path(runs_dir) / character
    if not runs_path.exists():
        raise FileNotFoundError(f"Directory not found: {runs_path}")

    run_files = sorted(
        runs_path.glob("*.run"),
        key=os.path.getmtime,
        reverse=True,
    )[:count]
    run_files.reverse()

    runs = []
    for path in run_files:
        run = load_run(path)
        if not run:
            continue
        runs.append(
            {
                "filename": path.name,
                "victory": run.get("victory", False),
                "floor": run.get("floor_reached", 0),
                "score": run.get("score", 0),
                "deck_size": len(run.get("master_deck", [])),
                "relics": len(run.get("relics", [])),
                "damage_taken": sum(
                    d.get("damage", 0) for d in run.get("damage_taken", [])
                ),
                "local_time": parse_local_time(run.get("local_time", "")),
                "mtime": datetime.fromtimestamp(path.stat().st_mtime),
            }
        )
    return runs


def bucket_runs(runs, bucket_size):
    buckets = []
    for i in range(0, len(runs), bucket_size):
        chunk = runs[i : i + bucket_size]
        if chunk:
            buckets.append(chunk)
    return buckets


def summarize_bucket(bucket, index_start):
    total = len(bucket)
    wins = sum(1 for r in bucket if r["victory"])
    avg_floor = sum(r["floor"] for r in bucket) / total
    max_floor = max(r["floor"] for r in bucket)
    avg_score = sum(r["score"] for r in bucket) / total
    avg_damage = sum(r["damage_taken"] for r in bucket) / total

    times = [r["local_time"] for r in bucket if r["local_time"]]
    time_start = min(times) if times else None
    time_end = max(times) if times else None

    return {
        "index_start": index_start,
        "index_end": index_start + total - 1,
        "total": total,
        "win_rate": (wins / total) * 100,
        "avg_floor": avg_floor,
        "max_floor": max_floor,
        "avg_score": avg_score,
        "avg_damage": avg_damage,
        "time_start": time_start,
        "time_end": time_end,
    }


def print_progress(buckets):
    print("=" * 80)
    print("TRAINING PROGRESS DASHBOARD")
    print("=" * 80)
    print(
        f"{'Bucket':<12} {'Runs':<6} {'Win%':<6} {'AvgFloor':<9} "
        f"{'Max':<5} {'AvgScore':<9} {'AvgDmg':<8} {'TimeRange'}"
    )
    print("-" * 80)

    summaries = []
    run_index = 1
    for bucket in buckets:
        summary = summarize_bucket(bucket, run_index)
        summaries.append(summary)
        time_range = f"{format_time(summary['time_start'])} - {format_time(summary['time_end'])}"
        print(
            f"{summary['index_start']:>3}-{summary['index_end']:<6} "
            f"{summary['total']:<6} "
            f"{summary['win_rate']:<6.1f} "
            f"{summary['avg_floor']:<9.2f} "
            f"{summary['max_floor']:<5} "
            f"{summary['avg_score']:<9.1f} "
            f"{summary['avg_damage']:<8.1f} "
            f"{time_range}"
        )
        run_index += summary["total"]

    print("-" * 80)
    print_trend(summaries)


def print_trend(summaries):
    if len(summaries) < 2:
        print("Not enough buckets to assess trend.")
        return

    floors = [s["avg_floor"] for s in summaries]
    last = summaries[-1]
    prev = summaries[-2]
    delta_floor = last["avg_floor"] - prev["avg_floor"]
    delta_win = last["win_rate"] - prev["win_rate"]

    trend = "stable"
    if delta_floor >= 1.0 or delta_win >= 2.0:
        trend = "improving"
    elif delta_floor <= -1.0 or delta_win <= -2.0:
        trend = "declining"

    print(
        f"Recent trend: {trend} "
        f"(avg_floor {delta_floor:+.2f}, win_rate {delta_win:+.1f}%)"
    )

    slope = compute_slope(floors)
    slope_per_100 = slope / summaries[0]["total"] * 100
    rolling = rolling_average(floors, window=5)
    rolling_tail = ", ".join(f"{v:.2f}" for v in rolling[-10:])
    print(
        f"Slope(avg_floor per bucket): {slope:+.4f} "
        f"(per 100 runs: {slope_per_100:+.4f})"
    )
    print(f"RollingAvg(5 buckets) last 10: {rolling_tail}")

    if len(summaries) >= 3:
        last_three = summaries[-3:]
        span = max(floors[-3:]) - min(floors[-3:])
        if span <= 0.5:
            print("Plateau hint: last 3 buckets show <= 0.5 avg_floor variance.")


def compute_slope(values):
    n = len(values)
    if n < 2:
        return 0.0
    xs = list(range(1, n + 1))
    mean_x = sum(xs) / n
    mean_y = sum(values) / n
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, values))
    den = sum((x - mean_x) ** 2 for x in xs)
    return num / den if den else 0.0


def rolling_average(values, window):
    if window <= 1:
        return values[:]
    averages = []
    for i in range(len(values)):
        start = max(0, i - window + 1)
        chunk = values[start : i + 1]
        averages.append(sum(chunk) / len(chunk))
    return averages


def generate_sign(timestamp, key):
    """生成飞书签名"""
    string_to_sign = f"{timestamp}\n{key}"
    hmac_code = hmac.new(
        string_to_sign.encode("utf-8"),
        digestmod=hashlib.sha256
    ).digest()
    sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
    return sign


def send_meow_message(summary_text, title="AI训练进度"):
    """发送 MeoW Push 通知

    Args:
        summary_text: 消息文本
        title: 通知标题
    """
    url = f"https://api.chuckfang.com/2f9a8d51/{urllib.parse.quote(title)}/{urllib.parse.quote(summary_text)}"
    logger.info(f"Sending MeoW notification, URL length: {len(url)}")
    try:
        response = requests.get(url, timeout=10)
        logger.info(f"MeoW response status: {response.status_code}, body: {response.text[:200]}")
        if response.status_code == 200:
            print("\n[OK] MeoW notification sent successfully")
        else:
            print(f"\n[ERROR] MeoW notification failed: {response.status_code}")
            logger.error(f"MeoW failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"\n[ERROR] MeoW notification exception: {e}")
        logger.error(f"MeoW exception: {e}")


def send_feishu_message(summary_text, at_all=False, at_mobiles=None):
    """发送飞书群消息（带签名验证）

    Args:
        summary_text: 消息文本
        at_all: 是否@所有人
        at_mobiles: 要@的用户ID列表（open_id或union_id）
    """
    timestamp = int(time.time())
    sign = generate_sign(timestamp, FEISHU_SIGN_KEY)

    # 构建 @ 内容
    at_text = ""
    if at_all:
        at_text = '<at user_id="all">所有人</at>\n'

    if at_mobiles:
        for user_id in at_mobiles:
            at_text += f'<at user_id="{user_id}"></at>\n'

    # 组合最终内容
    content = at_text + summary_text

    # 使用 text 类型 + lark_md 格式
    data = {
        "msg_type": "text",
        "content": {
            "text": content
        },
        "timestamp": str(timestamp),
        "sign": sign
    }

    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(FEISHU_WEBHOOK, headers=headers, json=data, timeout=10)
        result = response.json()
        if result.get("StatusCode") == 0 or result.get("code") == 0:
            print("\n[OK] Feishu notification sent successfully")
        else:
            print(f"\n[ERROR] Feishu notification failed: {result}")
    except Exception as e:
        print(f"\n[ERROR] Feishu notification exception: {e}")


def generate_summary(buckets, character, total_runs):
    """生成分析结论摘要"""
    if not buckets:
        return "无数据可分析"

    summaries = [summarize_bucket(bucket, 1) for bucket in buckets]
    latest = summaries[-1]
    prev = summaries[-2] if len(summaries) >= 2 else None

    # 计算趋势
    if prev:
        delta_floor = latest["avg_floor"] - prev["avg_floor"]
        delta_win = latest["win_rate"] - prev["win_rate"]
        trend = "📈 上升" if delta_floor >= 1.0 or delta_win >= 2.0 else \
                "📉 下降" if delta_floor <= -1.0 or delta_win <= -2.0 else "➡️ 平稳"
    else:
        delta_floor = 0
        delta_win = 0
        trend = "➡️ 平稳"

    # 构建消息
    msg = f"""🎮 AI游戏训练进度报告 ({character})
━━━━━━━━━━━━━━━━━━━━━━
📊 分析范围: 最近 {total_runs} 场游戏 ({len(buckets)} 个区间)

🏆 最新表现:
  • 胜率: {latest['win_rate']:.1f}%
  • 平均层数: {latest['avg_floor']:.2f}
  • 最高层数: {latest['max_floor']}
  • 平均得分: {latest['avg_score']:.1f}
  • 平均受伤: {latest['avg_damage']:.1f}

📈 趋势分析:
  • {trend} (层数 {delta_floor:+.2f}, 胜率 {delta_win:+.1f}%)
  • 最近区间: {format_time(latest['time_start'])} ~ {format_time(latest['time_end'])}

💡 建议: {get_suggestion(latest, prev)}

⏰ 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""

    return msg


def get_suggestion(latest, prev):
    """根据数据生成建议"""
    if latest["win_rate"] >= 60:
        return "表现优秀！继续当前策略"
    elif latest["win_rate"] >= 40:
        return "表现良好，可尝试优化关键节点决策"
    elif latest["avg_floor"] < 10:
        return "前期失败较多，建议检查战斗决策"
    elif prev and latest["avg_floor"] > prev["avg_floor"] + 2:
        return "层数提升明显，稳定性需加强"
    else:
        return "持续观察数据变化"


def main():
    logger.info("=" * 60)
    logger.info("Script started")
    logger.info(f"Working directory: {os.getcwd()}")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Args: {' '.join(sys.argv)}")

    parser = argparse.ArgumentParser(description="Training progress dashboard.")
    parser.add_argument("--count", type=int, default=300, help="Runs to include.")
    parser.add_argument("--bucket", type=int, default=50, help="Bucket size.")
    parser.add_argument(
        "--character",
        type=str,
        default="IRONCLAD",
        help="Character folder to analyze.",
    )
    parser.add_argument(
        "--notify",
        action="store_true",
        help="发送飞书通知",
    )
    parser.add_argument(
        "--meow",
        action="store_true",
        help="发送 MeoW Push 通知",
    )
    parser.add_argument(
        "--at-all",
        action="store_true",
        help="@所有人",
    )
    parser.add_argument(
        "--at",
        type=str,
        nargs="*",
        help="@指定人（手机号）",
    )
    args = parser.parse_args()

    runs_dir = (
        DEFAULT_RUNS_DIR_WSL
        if os.path.exists(DEFAULT_RUNS_DIR_WSL)
        else DEFAULT_RUNS_DIR_WIN
    )

    runs = collect_runs(runs_dir, args.character, args.count)
    if not runs:
        print("No runs found.")
        return

    buckets = bucket_runs(runs, args.bucket)
    print_progress(buckets)

    # 发送通知
    summary = generate_summary(buckets, args.character, len(runs))

    # 检查是否突破16层
    latest_summary = summarize_bucket(buckets[-1], len(runs) - len(buckets[-1]) + 1)
    max_floor = latest_summary["max_floor"]
    broke_16 = max_floor > 16

    # 飞书通知（始终发送）
    if args.notify or args.meow:
        send_feishu_message(summary, at_all=args.at_all, at_mobiles=args.at)

    # MeoW Push（只在突破16层时发送）
    if args.meow and broke_16:
        meow_msg = f"🎯 突破16层！\n\n最高层数: {max_floor}\n\n{summary[:300]}"
        send_meow_message(meow_msg, "训练突破")
        logger.info(f"MeoW notification sent for breaking floor 16 (max: {max_floor})")
    elif args.meow:
        logger.info(f"No MeoW notification - max floor {max_floor} <= 16")

    logger.info("Script completed successfully")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.exception(f"Script failed with exception: {e}")
        print(f"[ERROR] Script failed: {e}")
        sys.exit(1)
