# TelePing 多网址全国分布式拨测监控系统

简单、快速、实用的网站监控工具，基于 17CE API 和 Telegram Bot。

## 📋 项目特点

- **单文件实现**：所有代码在 `monitor.py` 中，总代码量约 400 行
- **零数据库**：使用 `config.json` 管理站点配置
- **分布式监控**：调用 17CE API，利用全国 200+ 节点检测
- **智能告警**：全国失败率 > 20% 或单地区失败节点 ≥ 3 时告警
- **地区显示**：按异常类型显示受影响地区分布
- **自助管理**：通过 Telegram Bot 命令管理监控站点
- **🔒 安全防护**：Chat ID 白名单，防止 Bot 被滥用
- **👥 群组支持**：支持个人和群组操作模式
- **🐳 Docker 支持**：一键部署，自动重启，日志轮转

## 🚀 快速开始

### 1. 准备工作

**注册 17CE 账号**
1. 访问 https://www.17ce.com/ 注册登录
2. 进入"API 接口"页面，获取 `username` 和 `token`

**创建 Telegram Bot**
1. Telegram 搜索 @BotFather，输入 `/newbot` 创建机器人
2. 获取 `BOT_TOKEN`
3. 和你的 Bot 聊天一次，访问 `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates` 获取 `CHAT_ID`

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置

编辑 `config.json`，填入你的凭证：

```json
{
  "sites": [
    { "name": "测试站点", "url": "www.baidu.com" }
  ],
  "alert_threshold": 0.20,
  "telegram_bot_token": "YOUR_BOT_TOKEN_HERE",
  "telegram_chat_id": "YOUR_CHAT_ID_HERE",
  "17ce_username": "YOUR_17CE_USERNAME",
  "17ce_token": "YOUR_17CE_TOKEN"
}
```

### 4. 运行

#### 方式一：Docker 部署（⭐ 推荐）

```bash
# 一键启动
docker-compose up -d

# 查看日志
docker-compose logs -f
```

#### 方式二：直接运行

```bash
# 前台运行（测试）
python3 monitor.py

# 后台运行
nohup python3 monitor.py > output.log 2>&1 &
```

## 📱 Telegram Bot 命令

- `/add <名称> <网址>` - 添加监控站点
  - 示例：`/add 官网 www.example.com`
- `/addmany <站点名>,<网址1>,<网址2>,...` - 批量添加监控站点（自动编号）
  - 示例：`/addmany 官网,www.example.com,backup.example.com,cdn.example.com`
  - 结果：自动创建 `官网-1`, `官网-2`, `官网-3` 三个站点
- `/delete <名称>` - 删除监控站点
  - 示例：`/delete 官网`
- `/list` - 查看当前监控列表

## 📁 项目结构

```
TelePing/
├── monitor.py                  # 主程序（所有功能）
├── config.json                 # 配置文件
├── requirements.txt            # Python 依赖
├── Dockerfile                  # Docker 镜像构建文件
├── docker-compose.yml          # Docker Compose 配置
├── .dockerignore               # Docker 构建忽略文件
├── monitor.log                 # 日志文件（自动生成）
├── DEPLOY.md                   # 详细部署指南
├── GROUP_SETUP.md              # 群组配置指南
└── README.md                   # 本文件
```

## ⚙️ 配置说明

- `sites`: 监控站点列表
- `alert_threshold`: 全国告警阈值（默认 0.20，即 20% 节点失败）
- `telegram_bot_token`: Telegram Bot Token
- `telegram_chat_id`: 接收告警的 Chat ID
- `17ce_username`: 17CE 账号用户名
- `17ce_token`: 17CE API Token
- `allowed_chat_ids`: **🔒 安全白名单**，允许操作 Bot 的用户/群组 ID

### 🚨 智能告警策略

告警触发条件（满足任一即可）：
1. **全国告警**：失败率 > `alert_threshold`（默认 20%）
2. **区域告警**：任意单个地区失败节点 ≥ 3 个

**举例说明**：
- 场景 1：全国 200 个节点，50 个失败 → **触发全国告警**（25% > 20%）
- 场景 2：北京 5 个节点，3 个失败 → **触发区域告警**（北京失败 3 个）
- 场景 3：全国 200 个节点，仅 2 个失败 → 不告警（未达到任何条件）

## 📚 详细文档

- **[DEPLOY.md](DEPLOY.md)** - 完整的部署指南（推荐阅读）
  - 详细的凭证获取步骤
  - 多种部署方式（nohup、screen、systemd）
  - 配置说明和使用场景
  - 常见问题解答

- **[GROUP_SETUP.md](GROUP_SETUP.md)** - 群组配置指南
  - 如何添加 Bot 到群组
  - 获取群组 Chat ID
  - 群组权限配置
  - 多种使用场景示例

## 🔧 高级配置

修改 `monitor.py` 中的常量：

```python
CHECK_INTERVAL_MINUTES = 15     # 检测间隔（分钟）
RETRY_TIMES = 3                 # API 调用重试次数
SLEEP_BETWEEN_RETRY = 5         # 重试间隔（秒）
```

## 📝 日志

所有运行日志记录在 `monitor.log` 文件中，包括：
- 检测开始/结束时间
- API 调用成功/失败
- 告警发送状态
- 错误信息

查看日志：
```bash
tail -f monitor.log
```

## ❓ 常见问题

**Q: 告警太频繁怎么办？**
A: 调高 `config.json` 中的 `alert_threshold` 值（如改为 0.30）

**Q: 想增加检测频率？**
A: 修改 `monitor.py` 中的 `CHECK_INTERVAL_MINUTES` 常量

**Q: 17CE API 调用失败？**
A: 检查网络连接、凭证配置，查看 `monitor.log` 获取详细错误

**Q: Telegram 收不到消息？**
A: 确认 `chat_id` 正确，确保服务器能访问 Telegram API

## 📄 设计原则

本项目遵循"**能跑 > 好看 > 优雅 > 完美**"的原则：
- 不使用数据库、消息队列、Web 框架
- 代码简单直接，易于理解和修改
- 快速上线，满足基本监控需求

## 📜 许可

MIT License - 自由使用和修改
