# TelePing 多网址全国分布式拨测监控系统

简单、快速、实用的网站监控工具，基于 17CE API 和 Telegram Bot。

## 📋 项目特点

- **模块化设计**：核心监控逻辑在 `monitor.py`，城市节点配置在 `city_nodes_config.py`
- **零数据库**：使用 `config.json` 管理站点配置
- **分布式监控**：调用 17CE API，覆盖全国 33 个主要城市，每次检测 66 个节点（33城市 × 2节点/城市）
- **智能告警**：满足任一条件触发告警：全国失败率 > 20% 或 单地区失败节点 ≥ 3
- **地区显示**：告警消息显示异常类型、地区分布和受影响运营商
- **自助管理**：通过 Telegram Bot 命令管理监控站点
- **🔒 安全防护**：Chat ID 白名单，防止 Bot 被滥用
- **👥 群组支持**：支持个人和群组操作模式
- **⏰ 差异化检测**：工作日密集监控（9-11时、13-17时），周末轻量化（仅10:00）
- **💰 节约积分**：精准城市级配置，每次仅 66 个节点（相比省级配置节约 90%）

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
  "17ce_token": "YOUR_17CE_TOKEN",
  "allowed_chat_ids": ["YOUR_CHAT_ID_HERE"]
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

- `/help` - 显示所有命令和使用说明
- `/add <网址>` - 添加监控站点（自动从URL提取域名作为站点名称）
  - 示例：`/add https://www.example.com` → 自动创建名为 `example.com` 的站点
  - 重名处理：自动编号为 `example.com-2`、`example.com-3`
- `/addmany` - 批量添加监控站点（多行格式）
  ```
  /addmany
  https://www.example.com
  https://www.backup.com
  https://www.cdn.com
  ```
  结果：自动创建 `example.com`、`backup.com`、`cdn.com` 三个站点
- `/delete <网址|域名|名称>` - 删除监控站点（支持智能匹配）
  - 示例：`/delete example.com` 或 `/delete https://www.example.com`
- `/deletemany` - 批量删除监控站点（多行格式）
- `/list` - 查看当前监控列表
- `/check` - 立即检测所有站点并返回详细报告
- `/checkone <网址>` - 检测单个站点的详细状态

## 📁 项目结构

```
TelePing/
├── monitor.py                  # 主程序（监控逻辑、Bot 命令处理）
├── city_nodes_config.py        # 城市节点配置（33个主要城市）
├── config.json                 # 配置文件（凭证和站点列表）
├── requirements.txt            # Python 依赖
├── Dockerfile                  # Docker 镜像构建文件
├── docker-compose.yml          # Docker Compose 配置
├── .dockerignore               # Docker 构建忽略文件
├── .gitignore                  # Git 忽略文件
├── monitor.log                 # 日志文件（自动生成）
├── DEPLOY.md                   # 详细部署指南
├── GROUP_SETUP.md              # 群组配置指南
└── README.md                   # 本文件
```

## ⚙️ 配置说明

- `sites`: 监控站点列表
- `alert_threshold`: 告警阈值（默认 0.20，即 20% 节点失败）
- `telegram_bot_token`: Telegram Bot Token
- `telegram_chat_id`: 接收告警的 Chat ID
- `17ce_username`: 17CE 账号用户名
- `17ce_token`: 17CE API Token
- `allowed_chat_ids`: **🔒 安全白名单**，允许操作 Bot 的用户/群组 ID

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

### 检测频率

项目使用差异化检测策略（在 `monitor.py` 的 `run_scheduler()` 函数中配置）：

- **工作日**（周一至周五）：早上 9:00-11:00 和下午 13:00-17:00，每小时检测一次
- **周末**（周六、周日）：每天 10:00 检测一次

如需调整检测时间，请修改 `run_scheduler()` 函数中的 `weekday_times` 列表和周末时间配置。

### API 调用参数

修改 `monitor.py` 中的常量：

```python
RETRY_TIMES = 3                 # API 调用重试次数
SLEEP_BETWEEN_RETRY = 5         # 重试间隔（秒）
AUTO_DELETE_SECONDS = 60        # Bot消息自动删除时间（秒）
```

### 节点配置

修改 `city_nodes_config.py` 中的配置：

- `MAJOR_CITIES`：城市列表（默认 33 个主要城市）
- `num`：**每个城市分配的节点数**
  - 默认值：`2`（平衡覆盖和积分消耗）
  - 说明：实际节点数 = 城市数 × num
  - 示例：33城市 × 2节点/城市 = 66个节点/次
- `nodetype`：节点类型（1=IDC, 2=路由器）
- `isps`：运营商过滤（1=电信, 2=联通, 7=移动）
- `areas`：地区过滤（1=大陆）

**积分优化建议**：
- 日常监控：`num=2`（充分覆盖，仅66节点/次）✅ 推荐
- 精简模式：`num=1`（33节点/次，极致节约）
- 深度诊断：`num=3-5`（99-165节点/次，更多数据）

**为什么用城市而不是省份？**
- 更精准：直接覆盖主要城市，避免偏远地区干扰
- 更节约：66节点 vs 174节点（省级配置）
- 更实用：33个主要城市已覆盖绝大多数用户

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
A: 修改 `monitor.py` 中的 `run_scheduler()` 函数，添加更多检测时间点

**Q: 17CE API 调用失败？**
A: 检查网络连接、凭证配置，查看 `monitor.log` 获取详细错误

**Q: Telegram 收不到消息？**
A: 确认 `chat_id` 正确，确保服务器能访问 Telegram API

**Q: Bot 命令无响应？**
A: 检查 `allowed_chat_ids` 配置，确保你的 Chat ID 在白名单中

## 📄 设计原则

本项目遵循"**能跑 > 好看 > 优雅 > 完美**"的原则：

- 不使用数据库、消息队列、Web 框架
- 代码简单直接，易于理解和修改
- 快速上线，满足基本监控需求

## 📜 许可

MIT License - 自由使用和修改
