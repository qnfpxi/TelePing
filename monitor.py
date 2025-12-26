import base64
import hashlib
import html
import json
import logging
import threading
import time
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Tuple

import requests
import schedule
from telegram import BotCommand, Update
from telegram.ext import Application, CommandHandler, ContextTypes

CONFIG_FILE = "config.json"
LOG_FILE = "monitor.log"
DEFAULT_THRESHOLD = 0.20
RETRY_TIMES = 3
SLEEP_BETWEEN_RETRY = 5
CHECK_INTERVAL_MINUTES = 15

# 配置文件读写锁，防止并发操作导致数据损坏
_config_lock = threading.Lock()


def setup_logging() -> None:
    """初始化日志配置，记录到文件并输出基本格式。"""
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )


def load_config() -> Dict[str, Any]:
    """读取配置文件，失败时返回默认结构以保证流程继续运行。"""
    with _config_lock:
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            logging.error("加载配置失败，将使用默认配置: %s", exc)
            return {"sites": [], "alert_threshold": DEFAULT_THRESHOLD}


def save_config(config: Dict[str, Any]) -> None:
    """保存配置到文件，失败时记录错误。使用文件锁防止并发写入。"""
    with _config_lock:
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
        except Exception as exc:
            logging.error("保存配置失败: %s", exc)


def call_17ce_api(url: str, config: Dict[str, Any], retries: int = RETRY_TIMES) -> Optional[Dict[str, Any]]:
    """调用 17CE API，包含简单重试与签名逻辑。"""
    username = config.get("17ce_username")
    token = config.get("17ce_token")
    if not username or not token:
        logging.error("17CE 凭证未配置")
        return None

    for attempt in range(retries):
        try:
            ut = int(time.time())
            pwd_md5 = hashlib.md5(token.encode("utf-8")).hexdigest()[3:22]
            sign_str = f"{pwd_md5}{username}{ut}"
            sign_bytes = base64.b64encode(sign_str.encode("utf-8"))
            sign = hashlib.md5(sign_bytes).hexdigest()

            api_url = "https://api.17ce.com/get.php"
            params = {
                "url": url,
                "host": url,
                "pro_ids": "",          # 为空表示全省份
                "isp_ids": "1,2,3",     # 1电信 2联通 3移动
                "num": 1,
                "username": username,
                "ut": ut,
                "sign": sign,
            }
            response = requests.get(api_url, params=params, timeout=30)
            if response.status_code == 200:
                try:
                    return response.json()
                except ValueError as json_exc:
                    # JSON 解析失败，记录响应内容片段
                    body_preview = response.text[:200] if response.text else "(empty)"
                    logging.error("17CE 返回非 JSON 格式（状态 200）：%s，响应片段：%s", json_exc, body_preview)
                    # 继续重试
            else:
                logging.warning("17CE 返回非 200 状态: %s", response.status_code)
        except Exception as exc:
            logging.warning("17CE 调用失败（第 %s 次）: %s", attempt + 1, exc)

        # 最后一次失败不 sleep，避免浪费时间
        if attempt < retries - 1:
            time.sleep(SLEEP_BETWEEN_RETRY)
    return None


def analyze_results(results: Optional[Dict[str, Any]], threshold: float) -> Tuple[Optional[Dict[str, int]], Optional[Dict[str, int]], Optional[Dict[str, Dict[str, int]]], float]:
    """解析 17CE 返回结果，计算失败率并识别受影响运营商、地区和异常类型。"""
    if not results or "data" not in results:
        return None, None, None, 0.0

    data = results.get("data", [])
    # 验证 data 是否为列表
    if not isinstance(data, list):
        logging.error("17CE 返回的 data 不是列表类型: %s", type(data))
        return None, None, None, 0.0

    total = len(data)
    if total == 0:
        return None, None, None, 0.0

    failed = 0
    skipped = 0
    operators = {"电信": 0, "联通": 0, "移动": 0, "其他": 0}
    regions: Dict[str, int] = {}
    # 异常类型 -> 地区 -> 计数
    error_types: Dict[str, Dict[str, int]] = {}

    for node in data:
        try:
            # 安全地提取和转换字段
            status_raw = node.get("status", 0)
            loss_raw = node.get("loss", 0)

            # 处理可能的字符串值（如 "--"、""、None）
            try:
                status = int(status_raw) if status_raw not in (None, "", "--") else 0
            except (ValueError, TypeError):
                status = 0

            try:
                loss = float(loss_raw) if loss_raw not in (None, "", "--") else 0
            except (ValueError, TypeError):
                loss = 0

            isp = str(node.get("isp_name") or node.get("isp") or "")
            # 获取响应IP（可能的字段名）
            response_ip = str(node.get("ip") or node.get("serverip") or node.get("server_ip") or "")
            # 获取地区信息（优先使用省份，其次城市）
            region = str(node.get("province_name") or node.get("province") or
                        node.get("city_name") or node.get("city") or "未知")
        except Exception as exc:
            # 跳过异常节点并记录
            skipped += 1
            logging.warning("跳过异常节点数据: %s", exc)
            continue

        # 判定节点是否失败（包含异常 IP 检测）
        is_failed = (
            status != 200 or
            loss >= 100 or
            response_ip == "0.0.0.0" or
            response_ip.startswith("127.")
        )

        if is_failed:
            failed += 1
            if "电信" in isp:
                operators["电信"] += 1
            elif "联通" in isp:
                operators["联通"] += 1
            elif "移动" in isp:
                operators["移动"] += 1
            else:
                operators["其他"] += 1

            # 统计地区
            regions[region] = regions.get(region, 0) + 1

            # 识别异常类型
            error_type = ""
            if response_ip == "0.0.0.0":
                error_type = "DNS解析失败(0.0.0.0)"
            elif response_ip.startswith("127."):
                error_type = "DNS劫持(127.x.x.x)"
            elif loss >= 100:
                error_type = "连接超时/丢包100%"
            elif status == 0:
                error_type = "无法连接"
            elif status == 404:
                error_type = "404页面不存在"
            elif status in (500, 502, 503):
                error_type = f"{status}服务器错误"
            else:
                error_type = f"HTTP{status}错误"

            # 统计异常类型的地区分布
            if error_type not in error_types:
                error_types[error_type] = {}
            error_types[error_type][region] = error_types[error_type].get(region, 0) + 1

    # 记录跳过的节点数
    if skipped > 0:
        logging.warning("本轮检测跳过 %d 个异常节点", skipped)

    # 使用有效节点数计算失败率（排除跳过的节点）
    valid_total = total - skipped
    if valid_total == 0:
        # 所有节点都被跳过，无法计算失败率
        logging.error("所有节点数据异常，无法计算失败率")
        return None, None, None, 0.0

    fail_rate = failed / valid_total

    # 检查是否需要告警（满足任一条件即可）
    should_alert = False

    # 条件1：全国失败率超过阈值
    if fail_rate > threshold:
        should_alert = True
        logging.info("触发全国告警：失败率 %.2f%% > 阈值 %.2f%%", fail_rate * 100, threshold * 100)

    # 条件2：单地区失败节点数 >= 3
    if not should_alert:
        for region, count in regions.items():
            if count >= 3:
                should_alert = True
                logging.info("触发区域告警：%s 失败 %d 个节点（≥3）", region, count)
                break

    if should_alert:
        return operators, regions, error_types, fail_rate
    return None, None, None, fail_rate


def analyze_results_detailed(results: Optional[Dict[str, Any]]) -> Tuple[float, Dict[str, int], str]:
    """解析 17CE 返回结果，返回详细检测状态（用于 /check 命令）。

    返回: (失败率, 地区分布字典, 状态描述)
    """
    if not results or "data" not in results:
        return 0.0, {}, "❌ API调用失败"

    data = results.get("data", [])
    if not isinstance(data, list) or len(data) == 0:
        return 0.0, {}, "❌ 无检测数据"

    total = len(data)
    failed = 0
    regions: Dict[str, int] = {}

    for node in data:
        try:
            status_raw = node.get("status", 0)
            loss_raw = node.get("loss", 0)

            try:
                status = int(status_raw) if status_raw not in (None, "", "--") else 0
            except (ValueError, TypeError):
                status = 0

            try:
                loss = float(loss_raw) if loss_raw not in (None, "", "--") else 0
            except (ValueError, TypeError):
                loss = 0

            response_ip = str(node.get("ip") or node.get("serverip") or node.get("server_ip") or "")
            region = str(node.get("province_name") or node.get("province") or
                        node.get("city_name") or node.get("city") or "未知")

            # 判定节点是否失败
            is_failed = (
                status != 200 or
                loss >= 100 or
                response_ip == "0.0.0.0" or
                response_ip.startswith("127.")
            )

            if is_failed:
                failed += 1
                regions[region] = regions.get(region, 0) + 1
        except Exception:
            continue

    fail_rate = failed / total if total > 0 else 0.0

    # 生成状态描述
    if fail_rate >= 0.20:
        status_emoji = "❌"
        status_text = "异常"
    elif fail_rate >= 0.10:
        status_emoji = "⚠️"
        status_text = "警告"
    else:
        status_emoji = "✅"
        status_text = "正常"

    return fail_rate, regions, f"{status_emoji} {status_text}"


def send_alert(message: str, config: Dict[str, Any]) -> None:
    """通过 Telegram 发送告警消息。"""
    token = config.get("telegram_bot_token")
    chat_id = config.get("telegram_chat_id")
    if not token or not chat_id:
        logging.error("Telegram 凭证未配置，跳过告警发送")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
    }
    try:
        requests.post(url, data=payload, timeout=10)
        logging.info("告警发送成功")
    except Exception as exc:
        logging.error("告警发送失败: %s", exc)


def monitor_all() -> None:
    """执行一轮监控：读取配置、调用 17CE、判定并发送告警。"""
    logging.info("开始新一轮检测")
    config = load_config()

    # 安全地解析阈值
    try:
        threshold_raw = config.get("alert_threshold", DEFAULT_THRESHOLD)
        threshold = float(threshold_raw)
        if not 0 <= threshold <= 1:
            logging.warning("告警阈值超出范围 [0,1]，使用默认值: %s", DEFAULT_THRESHOLD)
            threshold = DEFAULT_THRESHOLD
    except (ValueError, TypeError) as exc:
        logging.warning("告警阈值解析失败，使用默认值 %s: %s", DEFAULT_THRESHOLD, exc)
        threshold = DEFAULT_THRESHOLD

    alerts: List[str] = []
    api_failures: List[str] = []

    # 验证 sites 是否为列表
    sites = config.get("sites", [])
    if not isinstance(sites, list):
        logging.error("配置中的 sites 不是列表类型: %s，降级为空列表", type(sites))
        sites = []

    for site in sites:
        name = site.get("name", "未知站点")
        url = site.get("url", "")
        if not url:
            logging.warning("站点 %s 未配置 URL，跳过", name)
            continue

        results = call_17ce_api(url, config)

        # 区分 API 失败和站点异常
        if results is None:
            api_failures.append(name)
            logging.error("站点 %s 监控数据获取失败（17CE API调用失败）", name)
            continue

        operators, regions, error_types, fail_rate = analyze_results(results, threshold)
        if operators and regions and error_types:
            # HTML转义所有动态字段防止注入
            safe_name = html.escape(name)
            safe_url = html.escape(url)

            # 构建异常详情文本
            error_details = []
            for error_type, region_counts in error_types.items():
                # 按节点数排序，取前5个地区
                sorted_error_regions = sorted(region_counts.items(), key=lambda x: x[1], reverse=True)[:5]
                # 转义地区名称
                region_text = " ".join([f"{html.escape(r[0])}({r[1]})" for r in sorted_error_regions])
                error_details.append(f"{html.escape(error_type)}: {region_text}")

            msg = (
                f"<b>⚠️ 网站故障告警</b>\n"
                f"站点: {safe_name} ({safe_url})\n"
                f"异常占比: {fail_rate:.2%}\n\n"
                f"<b>【异常详情】</b>\n"
                f"{chr(10).join(error_details)}\n\n"
                f"受影响运营商: 电信{operators['电信']} "
                f"联通{operators['联通']} 移动{operators['移动']} 其他{operators['其他']}\n"
                f"检测时间: {time.strftime('%Y-%m-%d %H:%M:%S')}"
            )
            alerts.append(msg)

    # 发送告警
    if alerts:
        send_alert("\n\n".join(alerts), config)

    # 区分正常和 API 失败的情况
    if api_failures:
        logging.warning("以下站点监控数据获取失败: %s", ", ".join(api_failures))

    if not alerts and not api_failures:
        logging.info("所有站点正常")


def check_user_permission(chat_id: int, config: Dict[str, Any]) -> bool:
    """验证用户是否有权限操作 Bot。"""
    allowed_ids = config.get("allowed_chat_ids", [])
    # 支持字符串和整数格式的 Chat ID
    return str(chat_id) in [str(id) for id in allowed_ids]


async def cmd_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Telegram /add 命令，添加监控站点并持久化到 config.json。"""
    config = load_config()
    chat_id = update.effective_chat.id

    # 验证用户权限
    if not check_user_permission(chat_id, config):
        await update.message.reply_text("❌ 无权限操作此 Bot")
        logging.warning(f"未授权用户尝试操作 Bot: {chat_id}")
        return

    if len(context.args) < 2:
        await update.message.reply_text("📝 用法: /add <名称> <网址>\n💡 示例: /add 官网 www.example.com")
        return
    name = context.args[0]
    url = " ".join(context.args[1:])
    config.setdefault("sites", []).append({"name": name, "url": url})
    save_config(config)
    await update.message.reply_text(f"✅ 添加成功\n📌 {name} → {url}")


async def cmd_delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Telegram /delete 命令，删除监控站点。"""
    config = load_config()
    chat_id = update.effective_chat.id

    # 验证用户权限
    if not check_user_permission(chat_id, config):
        await update.message.reply_text("❌ 无权限操作此 Bot")
        logging.warning(f"未授权用户尝试操作 Bot: {chat_id}")
        return

    if len(context.args) < 1:
        await update.message.reply_text("📝 用法: /delete <名称>\n💡 示例: /delete 官网")
        return
    name = context.args[0]
    sites = config.get("sites", [])
    new_sites = [s for s in sites if s.get("name") != name]
    if len(new_sites) == len(sites):
        await update.message.reply_text(f"❌ 未找到名称为 '{name}' 的站点")
        return
    config["sites"] = new_sites
    save_config(config)
    await update.message.reply_text(f"🗑️ 删除成功\n📌 {name}")


async def cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Telegram /list 命令，列出当前监控站点。"""
    config = load_config()
    chat_id = update.effective_chat.id

    # 验证用户权限
    if not check_user_permission(chat_id, config):
        await update.message.reply_text("❌ 无权限操作此 Bot")
        logging.warning(f"未授权用户尝试操作 Bot: {chat_id}")
        return

    sites = config.get("sites", [])
    if not sites:
        await update.message.reply_text("📋 当前无监控站点")
        return
    # HTML 转义防止注入攻击
    lines = [f"• {html.escape(s.get('name', ''))} → {html.escape(s.get('url', ''))}" for s in sites]
    await update.message.reply_text(f"📋 <b>当前监控列表</b>（共 {len(sites)} 个站点）\n\n" + "\n".join(lines), parse_mode="HTML")


async def cmd_addmany(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Telegram /addmany 命令，批量添加监控站点。

    用法:
    /addmany 站点名
    网址1
    网址2
    网址3

    示例:
    /addmany 官网
    www.example.com
    backup.example.com
    cdn.example.com
    """
    config = load_config()
    chat_id = update.effective_chat.id

    # 验证用户权限
    if not check_user_permission(chat_id, config):
        await update.message.reply_text("❌ 无权限操作此 Bot")
        logging.warning(f"未授权用户尝试操作 Bot: {chat_id}")
        return

    # 解析多行消息
    message_text = update.message.text.strip()
    lines = [line.strip() for line in message_text.split("\n") if line.strip()]

    # 第一行是命令，第二行是站点名，后续是网址
    if len(lines) < 3:
        await update.message.reply_text(
            "📝 用法:\n"
            "/addmany 站点名\n"
            "网址1\n"
            "网址2\n\n"
            "💡 示例:\n"
            "/addmany 官网\n"
            "www.example.com\n"
            "backup.example.com"
        )
        return

    # 提取站点名（可能在第一行或第二行）
    if lines[0].startswith("/addmany"):
        # 检查命令行是否包含站点名
        cmd_parts = lines[0].split(maxsplit=1)
        if len(cmd_parts) > 1:
            # /addmany 站点名 在同一行
            base_name = cmd_parts[1]
            urls = lines[1:]
        else:
            # 站点名在第二行
            if len(lines) < 3:
                await update.message.reply_text("❌ 至少需要提供站点名和一个网址")
                return
            base_name = lines[1]
            urls = lines[2:]
    else:
        await update.message.reply_text("❌ 命令格式错误")
        return

    if not urls:
        await update.message.reply_text("❌ 至少需要提供一个网址")
        return

    # 批量添加站点
    added_sites = []
    for idx, url in enumerate(urls, start=1):
        if not url:
            continue
        site_name = f"{base_name}-{idx}" if len(urls) > 1 else base_name
        config.setdefault("sites", []).append({"name": site_name, "url": url})
        added_sites.append(f"• {site_name} → {url}")

    save_config(config)

    # 发送成功消息
    success_msg = "✅ 批量添加成功！\n\n" + "\n".join(added_sites) + f"\n\n📊 共添加 {len(added_sites)} 个站点"
    await update.message.reply_text(success_msg)
    logging.info(f"批量添加 {len(added_sites)} 个站点: {base_name}")


async def cmd_deletemany(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Telegram /deletemany 命令，批量删除监控站点。

    用法:
    /deletemany
    站点名1
    站点名2
    站点名3

    示例:
    /deletemany
    官网-1
    官网-2
    官网-3
    """
    config = load_config()
    chat_id = update.effective_chat.id

    # 验证用户权限
    if not check_user_permission(chat_id, config):
        await update.message.reply_text("❌ 无权限操作此 Bot")
        logging.warning(f"未授权用户尝试操作 Bot: {chat_id}")
        return

    # 解析多行消息
    message_text = update.message.text.strip()
    lines = [line.strip() for line in message_text.split("\n") if line.strip()]

    # 第一行是命令，后续是要删除的站点名
    if len(lines) < 2:
        await update.message.reply_text(
            "📝 用法:\n"
            "/deletemany\n"
            "站点名1\n"
            "站点名2\n\n"
            "💡 示例:\n"
            "/deletemany\n"
            "官网-1\n"
            "官网-2"
        )
        return

    # 提取要删除的站点名列表
    if lines[0].startswith("/deletemany"):
        # 检查命令行是否包含站点名
        cmd_parts = lines[0].split(maxsplit=1)
        if len(cmd_parts) > 1:
            # /deletemany 站点名 在同一行（兼容旧格式，作为前缀匹配）
            prefix = cmd_parts[1]
            delete_names = []
            # 查找所有匹配前缀的站点
            sites = config.get("sites", [])
            for site in sites:
                site_name = site.get("name", "")
                if site_name.startswith(f"{prefix}-") and site_name[len(prefix)+1:].isdigit():
                    delete_names.append(site_name)
        else:
            # 站点名在后续行
            delete_names = lines[1:]
    else:
        await update.message.reply_text("❌ 命令格式错误")
        return

    if not delete_names:
        await update.message.reply_text("❌ 至少需要提供一个站点名")
        return

    sites = config.get("sites", [])
    deleted_sites = []
    new_sites = []

    # 创建要删除的站点名集合，便于快速查找
    delete_set = set(delete_names)

    for site in sites:
        site_name = site.get("name", "")
        if site_name in delete_set:
            deleted_sites.append(f"• {site_name} → {site.get('url', '')}")
        else:
            new_sites.append(site)

    if not deleted_sites:
        await update.message.reply_text(f"❌ 未找到匹配的站点")
        return

    config["sites"] = new_sites
    save_config(config)

    # 发送成功消息
    success_msg = "🗑️ 批量删除成功！\n\n" + "\n".join(deleted_sites) + f"\n\n📊 共删除 {len(deleted_sites)} 个站点"
    await update.message.reply_text(success_msg)
    logging.info(f"批量删除 {len(deleted_sites)} 个站点")


async def cmd_check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Telegram /check 命令，检测所有站点并返回详细报告。"""
    config = load_config()
    chat_id = update.effective_chat.id

    # 验证用户权限
    if not check_user_permission(chat_id, config):
        await update.message.reply_text("❌ 无权限操作此 Bot")
        logging.warning(f"未授权用户尝试操作 Bot: {chat_id}")
        return

    sites = config.get("sites", [])
    if not sites:
        await update.message.reply_text("📋 当前无监控站点，请先使用 /add 添加站点")
        return

    # 发送进度提示
    progress_msg = await update.message.reply_text(
        f"🔍 检测中，请稍候...\n📊 正在检测 {len(sites)} 个站点"
    )

    # 收集检测结果
    results = []
    normal_count = 0
    warning_count = 0
    error_count = 0
    start_time = time.time()

    for idx, site in enumerate(sites, 1):
        # 超时保护：检测总时长不超过3分钟
        elapsed = time.time() - start_time
        if elapsed > 180:  # 3分钟
            await progress_msg.edit_text(
                f"⏱️ 检测超时（已检测 {idx-1}/{len(sites)} 个站点）\n"
                f"已检测站点结果将在下方显示"
            )
            break

        name = site.get("name", "未知")
        url = site.get("url", "")
        if not url:
            continue

        # 调用17CE API
        api_result = call_17ce_api(url, config)
        fail_rate, regions, status = analyze_results_detailed(api_result)

        # 分类统计
        if fail_rate >= 0.20:
            error_count += 1
        elif fail_rate >= 0.10:
            warning_count += 1
        else:
            normal_count += 1

        # 构建地区信息
        region_text = ""
        if regions:
            sorted_regions = sorted(regions.items(), key=lambda x: x[1], reverse=True)[:3]
            region_text = " | " + " ".join([f"{r[0]}({r[1]})" for r in sorted_regions])

        results.append({
            "name": name,
            "url": url,
            "fail_rate": fail_rate,
            "status": status,
            "region_text": region_text
        })

    # 删除进度消息
    try:
        await progress_msg.delete()
    except Exception:
        pass

    # 生成报告
    total_checked = len(results)
    report_lines = [
        f"🔍 <b>检测报告</b>",
        f"⏰ {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
    ]

    # 根据站点数量决定显示方式
    if total_checked <= 6:
        # 显示所有站点详情
        for r in results:
            report_lines.append(
                f"{r['status']} <b>{html.escape(r['name'])}</b> ({html.escape(r['url'])})\n"
                f"   失败率: {r['fail_rate']:.1%}{r['region_text']}\n"
            )
    else:
        # 只显示异常和警告站点
        report_lines.append(f"📊 <b>概览</b>")
        report_lines.append(f"✅ 正常: {normal_count} | ⚠️ 警告: {warning_count} | ❌ 异常: {error_count}\n")

        # 显示异常和警告站点
        abnormal_results = [r for r in results if r['fail_rate'] >= 0.10]
        if abnormal_results:
            report_lines.append(f"<b>⚠️ 需要关注的站点：</b>\n")
            for r in abnormal_results:
                report_lines.append(
                    f"{r['status']} <b>{html.escape(r['name'])}</b> ({html.escape(r['url'])})\n"
                    f"   失败率: {r['fail_rate']:.1%}{r['region_text']}\n"
                )
        else:
            report_lines.append("✅ 所有站点运行正常")

    report_lines.append(f"\n📊 总计: {total_checked} 个站点")

    await update.message.reply_text("\n".join(report_lines), parse_mode="HTML")
    logging.info(f"执行 /check 命令，检测 {total_checked} 个站点")


async def cmd_checkone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Telegram /checkone 命令，检测单个站点。"""
    config = load_config()
    chat_id = update.effective_chat.id

    # 验证用户权限
    if not check_user_permission(chat_id, config):
        await update.message.reply_text("❌ 无权限操作此 Bot")
        logging.warning(f"未授权用户尝试操作 Bot: {chat_id}")
        return

    if len(context.args) < 1:
        await update.message.reply_text(
            "📝 用法: /checkone <网址>\n"
            "💡 示例: /checkone www.example.com"
        )
        return

    url = " ".join(context.args)

    # 发送进度提示
    progress_msg = await update.message.reply_text(f"🔍 正在检测 {url}...")

    # 调用17CE API
    api_result = call_17ce_api(url, config)
    fail_rate, regions, status = analyze_results_detailed(api_result)

    # 删除进度消息
    try:
        await progress_msg.delete()
    except Exception:
        pass

    # 生成报告
    report_lines = [
        f"🔍 <b>单站点检测报告</b>",
        f"⏰ {time.strftime('%Y-%m-%d %H:%M:%S')}\n",
        f"🌐 网址: {html.escape(url)}",
        f"📊 失败率: {fail_rate:.2%}",
        f"🏷️ 状态: {status}\n"
    ]

    # 添加地区详情
    if regions:
        sorted_regions = sorted(regions.items(), key=lambda x: x[1], reverse=True)[:10]
        report_lines.append("<b>受影响地区：</b>")
        for region, count in sorted_regions:
            report_lines.append(f"• {html.escape(region)}: {count} 个节点")
    else:
        report_lines.append("✅ 所有地区检测正常")

    await update.message.reply_text("\n".join(report_lines), parse_mode="HTML")
    logging.info(f"执行 /checkone 命令，检测 {url}")


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Telegram /help 命令，显示帮助信息和所有可用命令。"""
    config = load_config()
    chat_id = update.effective_chat.id

    # 验证用户权限
    if not check_user_permission(chat_id, config):
        await update.message.reply_text("❌ 无权限操作此 Bot")
        logging.warning(f"未授权用户尝试操作 Bot: {chat_id}")
        return

    help_text = (
        "🤖 <b>TelePing 监控机器人</b>\n"
        "基于 17CE API 的多网址全国分布式拨测监控系统\n\n"

        "📋 <b>可用命令：</b>\n\n"

        "➕ <b>添加站点</b>\n"
        "• /add &#60;名称&#62; &#60;网址&#62;\n"
        "  添加单个监控站点\n"
        "  💡 示例: /add 官网 www.example.com\n\n"

        "📦 <b>批量添加</b>\n"
        "• /addmany &#60;站点名&#62;\n"
        "  &#60;网址1&#62;\n"
        "  &#60;网址2&#62;\n"
        "  批量添加监控站点（自动编号）\n"
        "  💡 示例:\n"
        "  /addmany 官网\n"
        "  www.a.com\n"
        "  www.b.com\n"
        "  结果: 官网-1, 官网-2 ...\n\n"

        "➖ <b>删除站点</b>\n"
        "• /delete &#60;名称&#62;\n"
        "  删除单个监控站点\n"
        "  💡 示例: /delete 官网\n\n"

        "💥 <b>批量删除</b>\n"
        "• /deletemany\n"
        "  &#60;站点名1&#62;\n"
        "  &#60;站点名2&#62;\n"
        "  批量删除指定站点\n"
        "  💡 示例:\n"
        "  /deletemany\n"
        "  官网-1\n"
        "  官网-2\n\n"

        "📋 <b>查看列表</b>\n"
        "• /list\n"
        "  查看当前所有监控站点\n\n"

        "🔍 <b>立即检测</b>\n"
        "• /check\n"
        "  检测所有站点并返回详细报告\n"
        "  ✅ 正常 (&lt;10%) | ⚠️ 警告 (10-20%) | ❌ 异常 (&gt;20%)\n\n"

        "🎯 <b>单站点检测</b>\n"
        "• /checkone &#60;网址&#62;\n"
        "  检测单个站点的详细状态\n"
        "  💡 示例: /checkone www.example.com\n\n"

        "❓ <b>帮助</b>\n"
        "• /help\n"
        "  显示此帮助信息\n\n"

        "⚠️ <b>告警策略</b>（满足任一即触发）：\n"
        "• 全国失败率 > 20%\n"
        "• 任意单地区失败节点 ≥ 3 个\n\n"

        "🔍 <b>检测频率</b>：每 15 分钟\n"
        "📊 <b>监控节点</b>：全国 200+ 节点（电信/联通/移动）"
    )

    await update.message.reply_text(help_text, parse_mode="HTML")


async def setup_bot_commands(app: Application) -> None:
    """设置Bot命令菜单，用户输入 / 时显示。"""
    commands = [
        BotCommand("help", "💡 使用帮助"),
        BotCommand("check", "🔍 检测所有站点"),
        BotCommand("checkone", "🎯 检测单个站点"),
        BotCommand("list", "📊 站点列表"),
        BotCommand("add", "➕ 添加站点"),
        BotCommand("addmany", "📦 批量添加"),
        BotCommand("delete", "🗑️ 删除站点"),
        BotCommand("deletemany", "💥 批量删除"),
    ]
    try:
        await app.bot.set_my_commands(commands)
        logging.info("Bot命令菜单设置成功")
    except Exception as exc:
        logging.error("Bot命令菜单设置失败: %s", exc)


def start_bot(config: Dict[str, Any]) -> Optional[Application]:
    """构建并返回 Telegram Bot Application 对象，由主线程运行。"""
    token = config.get("telegram_bot_token")
    if not token:
        logging.error("未配置 Telegram Bot Token，Bot 不会启动")
        return None

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("check", cmd_check))
    app.add_handler(CommandHandler("checkone", cmd_checkone))
    app.add_handler(CommandHandler("list", cmd_list))
    app.add_handler(CommandHandler("add", cmd_add))
    app.add_handler(CommandHandler("delete", cmd_delete))
    app.add_handler(CommandHandler("addmany", cmd_addmany))
    app.add_handler(CommandHandler("deletemany", cmd_deletemany))

    # 设置启动后的命令菜单初始化
    app.post_init = setup_bot_commands

    logging.info("Telegram Bot 已配置，准备在主线程运行")
    return app


def run_scheduler() -> None:
    """在子线程中运行定时任务调度器。"""
    logging.info("定时监控任务已启动")
    schedule.every(CHECK_INTERVAL_MINUTES).minutes.do(monitor_all)
    monitor_all()  # 立即执行一次

    while True:
        schedule.run_pending()
        time.sleep(1)


def main() -> None:
    """程序入口：初始化日志、启动定时任务（子线程）、运行 Bot（主线程）。"""
    setup_logging()
    logging.info("监控系统启动")
    config = load_config()

    # 启动定时监控任务（子线程）
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()

    # 构建 Bot 应用
    app = start_bot(config)
    if app:
        # 在主线程运行 Bot（避免 set_wakeup_fd 错误）
        logging.info("Telegram Bot 开始运行于主线程")
        app.run_polling()
    else:
        # 如果 Bot 未配置，则主线程保持运行
        logging.warning("Bot 未启动，仅运行定时监控")
        while True:
            time.sleep(60)


if __name__ == "__main__":
    main()
