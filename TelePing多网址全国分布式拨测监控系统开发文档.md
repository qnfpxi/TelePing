# TelePing多网址全国分布式拨测监控系统开发文档

**版本日期**：2025年12月24日  
**设计理念**：实用优先、快速上线、不要过度设计

## 1. 项目概述

### 1.1 项目背景

为了确保公司或个人旗下多个网站在中国境内的访问稳定性，本系统构建一套自动化监控体系。通过集成 17CE API，利用其全国200+分布式监控节点（覆盖多省份、电信/联通/移动三大运营商），模拟真实用户访问情况，绕过单点监控盲区。当检测到大面积故障时，通过 Telegram Bot 实时告警，并支持用户在 Telegram 中自助添加/删除/查看监控网址。

### 1.2 项目目标

- 支持多网址分布式 Ping + HTTP 检测
- 自定义告警阈值（默认全国 20% 节点不可达才告警）
- 通过 Telegram Bot 实现自助管理与实时告警
- 每 15 分钟自动检测一次
- 代码简单、易部署、免费优先（利用 17CE 免费 API 额度）

### 1.3 假设与约束

- 需要注册 17CE 账号获取 API Token（免费）
- 服务器需能访问 17CE API 和 Telegram API（推荐海外 VPS，或国内服务器+代理）
- 免费 API 有调用限额，高频或大量站点需考虑付费升级
- 无图形化界面，纯脚本运行

## 2. 功能需求规格

### 2.1 多目标监控管理

- 支持同时监控多个域名
- 站点列表存储在 `config.json` 文件中
- 通过 Telegram Bot 命令自助管理：
  - `/add <名称> <网址>`
  - `/delete <名称>`
  - `/list` 查看当前监控列表

### 2.2 分布式拨测（基于 17CE API）

- 使用 17CE 全国 200+ 节点（默认覆盖三大运营商）
- 检测指标：延迟、丢包率、HTTP 状态码、响应时间
- 支持指定运营商或全省份（本项目默认三大运营商全网）

### 2.3 异常判定逻辑

- 失败定义：节点丢包 100% 或 HTTP 状态码 ≠ 200
- 失败率 = 不可达节点数 / 总节点数
- 仅当失败率 > 20%（可配置）时触发告警，过滤局部波动

### 2.4 智能告警系统

- 告警渠道：Telegram Bot
- 多站点故障时聚合为一条消息发送（避免告警风暴）
- 告警内容包含：
  - 故障站点名称及网址
  - 全国异常占比
  - 主要受影响运营商及节点数
  - 检测时间

### 2.5 其他功能

- 每 15 分钟自动检测一次
- API 调用失败自动重试 3 次
- 简单日志记录到文件

## 3. 系统架构设计（简洁版）

```
Telegram Bot ←→ config.json（站点管理）
                  ↑
             Scheduler (每15分钟)
                  ↓
          17CE API 调用 → 结果解析 → 失败率计算
                  ↓
             若超阈值 → 聚合告警 → Telegram 发送
```

## 4. 技术栈

- Python 3.12+
- 核心库：
  - `requests`：调用 17CE API
  - `python-telegram-bot`：Bot 实现
  - `schedule`：定时任务
  - `json`, `time`, `hashlib`, `base64`, `logging`：标准库
- 依赖安装：
  
  ```bash
  pip install requests python-telegram-bot schedule
  ```

## 5. 重要开发原则：不要过度设计（Keep It Simple & Practical）

1. **目标是 3-5 天内上线可用版本**，不是造企业级监控平台
2. **总代码量控制在 500 行以内**，全部写在一个文件 `monitor.py`
3. **不使用数据库、消息队列、Web 框架、复杂设计模式**
4. **只用 config.json 存站点，不搞多用户、权限、历史记录**
5. **告警逻辑简单**：超阈值就发，不做恢复通知、静默期
6. **Bot 只实现 3 个命令**：add / delete / list
7. **错误处理适度**：重试 3 次 + 日志打印即可
8. **部署简单**：nohup 或 Crontab 运行
9. **后续功能先写 TODO**，等核心稳定再加

**口诀**：能跑 > 好看 > 优雅 > 完美

## 6. 实施指南

### 6.1 准备工作（1-2 小时）

1. **注册 17CE 并获取 API 凭证**
   
   - 访问 https://www.17ce.com/ 注册登录
   - 进入“API 接口”页面，获取 **username** 和 **token**（也称 pwd）

2. **创建 Telegram Bot**
   
   - Telegram 中搜索 @BotFather，输入 /newbot 创建机器人
   - 获取 **BOT_TOKEN**
   - 和你的 Bot 聊天一次，然后访问 https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates 获取 **CHAT_ID**（或用 @userinfobot）

### 6.2 项目结构

```
project_folder/
├── monitor.py          # 主脚本（全部代码在此）
├── config.json         # 配置文件
├── monitor.log         # 日志文件（运行后自动生成）
└── requirements.txt    # 依赖列表
```

**requirements.txt 内容**：

```
requests
python-telegram-bot
schedule
```

**config.json 初始模板**：

```json
{
  "sites": [
    {"name": "测试站点", "url": "www.baidu.com"}
  ],
  "alert_threshold": 0.20,
  "telegram_bot_token": "YOUR_BOT_TOKEN_HERE",
  "telegram_chat_id": "YOUR_CHAT_ID_HERE",
  "17ce_username": "YOUR_17CE_USERNAME",
  "17ce_token": "YOUR_17CE_TOKEN"
}
```

### 6.3 完整代码（monitor.py）——可直接复制使用

```python
import requests
import time
import hashlib
import base64
import json
import logging
import schedule
import threading
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ==================== 配置与日志 ====================
CONFIG_FILE = "config.json"
LOG_FILE = "monitor.log"

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def load_config():
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"加载配置失败: {e}")
        return {"sites": [], "alert_threshold": 0.20}

def save_config(config):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    except Exception as e:
        logging.error(f"保存配置失败: {e}")

# ==================== 17CE API 调用 ====================
def call_17ce_api(url, config, retries=3):
    username = config.get("17ce_username")
    token = config.get("17ce_token")
    if not username or not token:
        logging.error("17CE 凭证未配置")
        return None

    for attempt in range(retries):
        try:
            ut = int(time.time())
            pwd_md5 = hashlib.md5(token.encode()).hexdigest()[3:22]
            sign_str = pwd_md5 + username + str(ut)
            sign = hashlib.md5(base64.b64encode(sign_str.encode())).hexdigest()

            api_url = "https://api.17ce.com/get.php"
            params = {
                "url": url,
                "host": url,
                "pro_ids": "",          # 空 = 全省份
                "isp_ids": "1,2,3",     # 1电信 2联通 3移动
                "num": 1,
                "username": username,
                "ut": ut,
                "sign": sign
            }
            response = requests.get(api_url, params=params, timeout=30)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logging.warning(f"17CE API 调用失败（第{attempt+1}次）: {e}")
            time.sleep(5)
    return None

# ==================== 结果分析 ====================
def analyze_results(results, threshold):
    if not results or "data" not in results:
        return None, 0.0

    data = results["data"]
    total = len(data)
    if total == 0:
        return None, 0.0

    failed = 0
    operators = {"电信": 0, "联通": 0, "移动": 0, "其他": 0}

    for node in data:
        # 根据实际返回字段调整（常见字段：status, loss, isp_name）
        status = node.get("status", 0)
        loss = node.get("loss", 0)
        isp = node.get("isp_name", "") or node.get("isp", "")

        if int(status) != 200 or float(loss) >= 100:
            failed += 1
            if "电信" in isp:
                operators["电信"] += 1
            elif "联通" in isp:
                operators["联通"] += 1
            elif "移动" in isp:
                operators["移动"] += 1
            else:
                operators["其他"] += 1

    fail_rate = failed / total
    if fail_rate > threshold:
        return operators, fail_rate
    return None, 0.0

# ==================== 告警发送 ====================
def send_alert(message, config):
    token = config.get("telegram_bot_token")
    chat_id = config.get("telegram_chat_id")
    if not token or not chat_id:
        logging.error("Telegram 凭证未配置")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        requests.post(url, data=payload, timeout=10)
        logging.info("告警发送成功")
    except Exception as e:
        logging.error(f"告警发送失败: {e}")

# ==================== 监控主逻辑 ====================
def monitor_all():
    logging.info("开始新一轮检测")
    config = load_config()
    alerts = []

    for site in config.get("sites", []):
        name = site["name"]
        url = site["url"]
        results = call_17ce_api(url, config)
        operators, fail_rate = analyze_results(results, config["alert_threshold"])

        if operators:
            msg = (
                f"<b>⚠️ 网站故障告警</b>\n"
                f"站点: {name} ({url})\n"
                f"异常占比: {fail_rate:.2%}\n"
                f"受影响运营商节点: 电信{operators['电信']} 联通{operators['联通']} 移动{operators['移动']} 其他{operators['其他']}\n"
                f"检测时间: {time.strftime('%Y-%m-%d %H:%M:%S')}"
            )
            alerts.append(msg)

    if alerts:
        send_alert("\n\n".join(alerts), config)
    else:
        logging.info("所有站点正常")

# ==================== Telegram Bot 命令 ====================
async def cmd_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("用法: /add <名称> <网址>\n示例: /add 官网 www.example.com")
        return
    name, url = context.args[0], " ".join(context.args[1:])
    config = load_config()
    config["sites"].append({"name": name, "url": url})
    save_config(config)
    await update.message.reply_text(f"✅ 添加成功: {name} ({url})")

async def cmd_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        await update.message.reply_text("用法: /delete <名称>")
        return
    name = context.args[0]
    config = load_config()
    new_sites = [s for s in config["sites"] if s["name"] != name]
    if len(new_sites) == len(config["sites"]):
        await update.message.reply_text(f"❌ 未找到名称为 '{name}' 的站点")
    else:
        config["sites"] = new_sites
        save_config(config)
        await update.message.reply_text(f"✅ 删除成功: {name}")

async def cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    config = load_config()
    if not config["sites"]:
        await update.message.reply_text("当前无监控站点")
        return
    lines = [f"• {s['name']} → {s['url']}" for s in config["sites"]]
    await update.message.reply_text("<b>当前监控列表：</b>\n" + "\n".join(lines), parse_mode="HTML")

# ==================== 主程序 ====================
if __name__ == "__main__":
    logging.info("监控系统启动")
    config = load_config()

    # 启动 Bot
    app = Application.builder().token(config["telegram_bot_token"]).build()
    app.add_handler(CommandHandler("add", cmd_add))
    app.add_handler(CommandHandler("delete", cmd_delete))
    app.add_handler(CommandHandler("list", cmd_list))

    bot_thread = threading.Thread(target=app.run_polling, daemon=True)
    bot_thread.start()

    # 定时任务
    schedule.every(15).minutes.do(monitor_all)

    # 首次立即运行一次
    monitor_all()

    # 主循环
    while True:
        schedule.run_pending()
        time.sleep(1)
```

### 6.4 部署步骤

1. 将 `monitor.py` 和 `config.json` 上传到服务器
2. 安装依赖：`pip install -r requirements.txt`
3. 后台运行：
   
   ```bash
   nohup python monitor.py > output.log 2>&1 &
   ```
   
   或使用 screen/tmux

## 7. 测试与维护

1. 手动运行 `python monitor.py`，观察日志和 Telegram 是否收到首次检测结果
2. 用 Bot 发送 `/list`、`/add` 测试自助功能
3. 临时改一个不存在的域名测试告警
4. 查看 `monitor.log` 排查问题

**常见问题**：

- API 返回字段变化 → 调整 `analyze_results` 中的 key 名称
- 调用频率超限 → 降低检测频率或升级 17CE 付费
- Telegram 收不到消息 → 检查 chat_id 和网络

## 8. 参考资源

- 17CE API 文档：https://www.17ce.com/doc/API%20Reference/
- python-telegram-bot 文档：https://docs.python-telegram-bot.org/
- 项目完全自制，可自由修改
