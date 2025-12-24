# TelePing 配置与启动指南

## 📊 项目状态

✅ **已完成开发**，可直接上线使用！

**项目统计**：
- 代码行数：262 行（单文件实现）
- 函数数量：12 个
- 依赖包数：3 个（requests, python-telegram-bot, schedule）

---

## 🚀 快速上线步骤

### 步骤 1：准备凭证

#### 1.1 注册 17CE 并获取 API 凭证

1. 访问 https://www.17ce.com/ 注册登录
2. 进入"API 接口"页面
3. 获取以下信息：
   - **username**：你的 17CE 用户名
   - **token**：API Token（也称为 pwd）

#### 1.2 创建 Telegram Bot

1. Telegram 中搜索 **@BotFather**
2. 发送 `/newbot` 命令创建机器人
3. 按提示设置 Bot 名称和用户名
4. 获取 **BOT_TOKEN**（类似：`123456789:ABCdefGHIjklMNOpqrsTUVwxyz`）

#### 1.3 获取个人 Chat ID

方法一（推荐）：
1. 和你的 Bot 发送任意一条消息
2. 访问：`https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
3. 在返回的 JSON 中找到 `"chat":{"id":123456789}` 的数字

方法二：
1. Telegram 搜索 **@userinfobot**
2. 点击 Start，获取你的 Chat ID

#### 1.4 获取群组 Chat ID（可选）

如果你想让群组内的成员都能操作 Bot：

1. **将 Bot 添加到群组**
   - 在群组中点击群组名称 → "添加成员"
   - 搜索你的 Bot 用户名
   - 添加成功

2. **给 Bot 管理员权限**（推荐，避免消息接收问题）
   - 群组设置 → 管理员 → 添加管理员
   - 选择你的 Bot

3. **获取群组 Chat ID**

   方法 A - 使用 API：
   - 在群组中发送任意消息（如：`Hello Bot`）
   - 访问：`https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
   - 在返回的 JSON 中找到：
     ```json
     {
       "message": {
         "chat": {
           "id": -1001234567890,  // ← 群组 Chat ID（负数）
           "title": "我的监控群组",
           "type": "supergroup"
         }
       }
     }
     ```

   方法 B - 使用专用 Bot：
   - 群组中添加 **@getidsbot** 或 **@userinfobot**
   - Bot 会自动回复群组 ID

**注意**：
- 个人 Chat ID 是正数（如 `123456789`）
- 群组 Chat ID 是负数（如 `-1001234567890`）
- 两种格式都可以添加到 `allowed_chat_ids`

---

### 步骤 2：安装依赖

```bash
cd /Users/admin/TelePing
pip3 install -r requirements.txt
```

**依赖说明**：
- `requests`：调用 17CE API
- `python-telegram-bot`：Telegram Bot 功能
- `schedule`：定时任务调度

---

### 步骤 3：配置凭证

编辑 `config.json` 文件，填入你的凭证：

```json
{
  "sites": [
    { "name": "测试站点", "url": "www.baidu.com" }
  ],
  "alert_threshold": 0.20,
  "telegram_bot_token": "123456789:ABCdefGHIjklMNOpqrsTUVwxyz",
  "telegram_chat_id": "123456789",
  "17ce_username": "your_username",
  "17ce_token": "your_token_here",
  "allowed_chat_ids": ["123456789"]
}
```

**配置说明**：
- `sites`：监控站点列表，可添加多个
- `alert_threshold`：告警阈值（0.20 = 20% 节点失败）
- `telegram_bot_token`：你的 Bot Token
- `telegram_chat_id`：接收告警的 Chat ID
- `17ce_username`：17CE 用户名
- `17ce_token`：17CE API Token
- `allowed_chat_ids`：**🔒 安全白名单**，允许操作 Bot 的 Chat ID 列表

**🔐 安全说明**：
- `allowed_chat_ids` 是 **Chat ID 白名单**，只有列表中的用户才能操作 Bot
- 支持多个用户：`["123456789", "987654321"]`
- **支持群组**：添加群组 ID 后，群组内所有成员都能操作
- **强烈建议**：至少添加你自己的 Chat ID
- 未授权用户发送命令会收到"❌ 无权限操作此 Bot"提示
- 未授权尝试会记录到 `monitor.log` 中

**🎯 配置场景示例**：

**场景 1：仅个人操作**
```json
{
  "telegram_chat_id": "123456789",
  "allowed_chat_ids": ["123456789"]
}
```
效果：只有你能私聊 Bot 操作，告警发给你个人

**场景 2：个人操作 + 群组告警**
```json
{
  "telegram_chat_id": "-1001234567890",   // 告警发到群组
  "allowed_chat_ids": ["123456789"]       // 只有你能操作
}
```
效果：告警在群组公开，只有你能私聊 Bot 操作

**场景 3：群组公开操作**
```json
{
  "telegram_chat_id": "-1001234567890",
  "allowed_chat_ids": ["-1001234567890"]  // 群组内所有人都能操作
}
```
效果：告警和操作都在群组内，任何成员都能发命令

**场景 4：多个管理员 + 群组告警**
```json
{
  "telegram_chat_id": "-1001234567890",
  "allowed_chat_ids": [
    "123456789",    // 管理员 A
    "987654321",    // 管理员 B
    "-1001234567890" // 或群组内所有人
  ]
}
```
效果：告警在群组，多人可以操作

---

### 步骤 4：测试运行

#### 4.1 前台测试

```bash
python3 monitor.py
```

**观察日志**：
```
INFO - 监控系统启动
INFO - Telegram Bot 已启动
INFO - 开始新一轮检测
INFO - 所有站点正常
```

#### 4.2 测试 Bot 命令

**个人聊天测试**：
在 Telegram 中给你的 Bot 发送：
- `/list` - 查看当前监控站点
- `/add 官网 www.example.com` - 添加站点
- `/addmany 官网,www.example.com,backup.example.com,cdn.example.com` - 批量添加站点
- `/delete 测试站点` - 删除站点

**群组聊天测试**（如果配置了群组）：
在群组中发送：
- `/list` - 查看当前监控站点
- `/add 站点名 网址` - 添加站点（群组内任何人都能看到）
- `/addmany 站点名,网址1,网址2,网址3` - 批量添加站点（自动编号为 站点名-1、站点名-2...）
- `/delete 站点名` - 删除站点

**验证权限**：
- 如果你在白名单中 → 命令正常执行
- 如果你不在白名单中 → 收到"❌ 无权限操作此 Bot"
- 查看日志：`tail -f monitor.log | grep "未授权"`

#### 4.3 验证告警

首次运行会立即检测一次，如果站点正常，不会发送告警。

**告警发送位置**：
- `telegram_chat_id` 是个人 ID → 告警发到个人聊天
- `telegram_chat_id` 是群组 ID → 告警发到群组

---

### 步骤 5：后台运行（生产环境）

#### 方法一：Docker 部署（⭐ 强烈推荐）

**优势**：
- ✅ 一键启动，无需配置 Python 环境
- ✅ 容器隔离，不影响宿主机环境
- ✅ 自动重启，崩溃后自动恢复
- ✅ 日志管理，自动轮转日志文件
- ✅ 跨平台，Linux/macOS/Windows 统一部署

**前置要求**：
```bash
# 安装 Docker 和 Docker Compose
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y docker.io docker-compose

# CentOS/RHEL
sudo yum install -y docker docker-compose

# macOS（使用 Homebrew）
brew install docker docker-compose
```

**一键启动**：
```bash
# 1. 确保已配置 config.json
# 2. 启动服务（首次会自动构建镜像）
docker-compose up -d

# 查看运行状态
docker-compose ps

# 查看实时日志
docker-compose logs -f

# 查看最近 100 行日志
docker-compose logs --tail=100
```

**常用管理命令**：
```bash
# 停止服务
docker-compose stop

# 重启服务
docker-compose restart

# 停止并删除容器
docker-compose down

# 更新代码后重新构建
docker-compose up -d --build

# 进入容器内部（调试）
docker exec -it teleping_monitor sh
```

**查看日志文件**：
```bash
# 宿主机上查看（配置了卷映射）
tail -f monitor.log

# 或在容器内查看
docker exec teleping_monitor tail -f /app/monitor.log
```

**配置文件修改**：
```bash
# 修改 config.json 后重启服务即可生效
vim config.json
docker-compose restart
```

**健康检查**：
```bash
# Docker 会自动监控容器健康状态
docker inspect teleping_monitor | grep -A 10 Health
```

---

#### 方法二：nohup

```bash
nohup python3 monitor.py > output.log 2>&1 &
```

查看日志：
```bash
tail -f monitor.log
```

查看进程：
```bash
ps aux | grep monitor.py
```

停止服务：
```bash
pkill -f monitor.py
```

#### 方法三：screen

```bash
screen -S teleping
python3 monitor.py
# 按 Ctrl+A 然后 D 离开
```

恢复查看：
```bash
screen -r teleping
```

#### 方法四：systemd（适用于 Linux 服务器）

创建服务文件 `/etc/systemd/system/teleping.service`：

```ini
[Unit]
Description=TelePing Monitor Service
After=network.target

[Service]
Type=simple
User=admin
WorkingDirectory=/Users/admin/TelePing
ExecStart=/usr/bin/python3 monitor.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启动服务：
```bash
sudo systemctl start teleping
sudo systemctl enable teleping  # 开机自启
sudo systemctl status teleping  # 查看状态
```

---

## ⚙️ 高级配置

### 修改检测频率

编辑 `monitor.py` 第 19 行：

```python
CHECK_INTERVAL_MINUTES = 15  # 改为你想要的分钟数
```

### 调整告警阈值

修改 `config.json`：

```json
{
  "alert_threshold": 0.30  // 30% 节点失败才告警
}
```

### 修改重试次数

编辑 `monitor.py` 第 17 行：

```python
RETRY_TIMES = 3  # API 调用失败重试次数
```

---

## 📱 告警消息格式

当检测到故障时，你会收到如下格式的 Telegram 消息：

```
⚠️ 网站故障告警
站点: 官网 (www.example.com)
异常占比: 35.60%

【异常详情】
DNS解析失败(0.0.0.0): 北京(3) 上海(2) 广东(3)
DNS劫持(127.x.x.x): 河南(2) 湖北(1)
连接超时/丢包100%: 四川(1) 云南(2)

受影响运营商: 电信5 联通3 移动8 其他0
检测时间: 2025-12-24 21:30:15
```

**异常类型说明**：
- **DNS解析失败(0.0.0.0)** - 域名无法解析，DNS服务器问题
- **DNS劫持(127.x.x.x)** - DNS被劫持，返回本地回环地址
- **连接超时/丢包100%** - 网络不通，无法连接服务器
- **404页面不存在** - 页面或资源不存在
- **500/502/503服务器错误** - 服务器内部错误或网关错误
- **无法连接** - 网络连接失败

---

## 🔍 日志说明

**日志文件**：`monitor.log`

**日志内容**：
- 系统启动/关闭
- 每轮检测的开始/结束
- API 调用成功/失败
- 告警发送状态
- 错误信息

**查看最新日志**：
```bash
tail -f monitor.log
```

**搜索错误**：
```bash
grep ERROR monitor.log
```

---

## ❓ 常见问题

### Q1：告警太频繁怎么办？

**解决方案**：
- 提高 `alert_threshold`（如改为 0.30）
- 增加检测间隔（如改为 30 分钟）

### Q2：17CE API 调用失败？

**排查步骤**：
1. 检查网络连接
2. 确认 `17ce_username` 和 `17ce_token` 正确
3. 查看 `monitor.log` 中的详细错误信息
4. 确认 17CE 免费额度是否用完

### Q3：Telegram 收不到消息？

**排查步骤**：
1. 确认 `telegram_bot_token` 正确
2. 确认 `telegram_chat_id` 正确（是数字，不是用户名）
3. 检查服务器是否能访问 Telegram API
4. 尝试手动发送测试消息

### Q4：Bot 命令不响应？

**排查步骤**：
1. 确认 Bot 正在运行（`ps aux | grep monitor.py`）
2. 查看 `monitor.log` 是否有错误
3. 确认在 Telegram 中和正确的 Bot 对话
4. 重启服务试试

---

## 📊 监控建议

### 初期运行（1-7 天）

- **检测频率**：15 分钟
- **告警阈值**：20%
- **监控站点**：2-5 个核心站点
- **观察重点**：
  - 17CE API 调用是否稳定
  - 告警频率是否合理
  - 误报情况

### 稳定运行

根据初期观察调整：
- 如果告警太多 → 提高阈值到 30%
- 如果 API 额度紧张 → 降低频率到 30 分钟
- 如果一切正常 → 逐步增加监控站点

---

## 🎯 后续优化方向

如果 17CE 免费额度不够用，可考虑：

1. **降低检测频率**：15 分钟 → 30 分钟
2. **付费升级 17CE**：获取更多调用额度
3. **分批检测**：将站点分组，轮流检测
4. **自建节点**：部署多个小型检测节点（复杂度高）

---

## ✅ 验收清单

上线前请确认：

- [ ] 依赖已安装（`pip3 list | grep -E "requests|telegram|schedule"`）
- [ ] 配置已填写（检查 `config.json` 所有字段）
- [ ] 前台测试通过（运行无报错）
- [ ] Bot 命令可用（`/list` 有响应）
- [ ] 日志正常生成（`ls -lh monitor.log`）
- [ ] 后台运行正常（`ps aux | grep monitor.py`）

---

## 📞 技术支持

- GitHub Issues：项目问题反馈
- 17CE 文档：https://www.17ce.com/doc/
- python-telegram-bot 文档：https://docs.python-telegram-bot.org/

---

**祝你使用愉快！🎉**
