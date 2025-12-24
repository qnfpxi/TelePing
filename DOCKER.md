# Docker 快速开始指南

## 🐳 一键部署

### 前置要求

确保服务器已安装 Docker 和 Docker Compose：

```bash
# 检查 Docker 版本
docker --version
docker-compose --version

# 如未安装，参考 DEPLOY.md 安装说明
```

### 快速部署

```bash
# 1. 克隆或上传项目到服务器
cd /path/to/TelePing

# 2. 编辑配置文件
vim config.json

# 填入你的凭证：
# - telegram_bot_token
# - telegram_chat_id
# - 17ce_username
# - 17ce_token
# - allowed_chat_ids

# 3. 一键启动
docker-compose up -d

# 4. 查看运行状态
docker-compose ps

# 5. 查看日志
docker-compose logs -f
```

## 📋 常用命令

```bash
# 查看实时日志
docker-compose logs -f

# 查看最近 100 行日志
docker-compose logs --tail=100

# 重启服务
docker-compose restart

# 停止服务
docker-compose stop

# 启动服务
docker-compose start

# 停止并删除容器
docker-compose down

# 更新代码后重新构建
docker-compose up -d --build

# 进入容器调试
docker exec -it teleping_monitor sh
```

## 🔧 配置修改

修改 `config.json` 后重启服务即可生效：

```bash
vim config.json
docker-compose restart
```

## 📊 健康检查

Docker 会自动监控容器健康状态：

```bash
# 查看健康状态
docker inspect teleping_monitor | grep -A 10 Health

# 查看容器详情
docker-compose ps
```

## 🚨 故障排查

### 容器无法启动

```bash
# 查看详细日志
docker-compose logs

# 检查配置文件
cat config.json

# 验证配置语法
docker-compose config
```

### 无法连接 Telegram

```bash
# 检查网络
docker exec teleping_monitor ping -c 3 api.telegram.org

# 检查配置
docker exec teleping_monitor cat config.json
```

### 查看 Python 错误

```bash
# 查看容器日志
docker-compose logs --tail=50

# 查看 monitor.log
tail -f monitor.log
```

## 🎯 优势

- ✅ **环境隔离**：不污染宿主机 Python 环境
- ✅ **自动重启**：容器崩溃自动恢复
- ✅ **日志轮转**：自动管理日志大小
- ✅ **跨平台**：Linux/macOS/Windows 统一部署
- ✅ **一键启动**：docker-compose up -d

## 📖 更多文档

- **详细部署指南**：[DEPLOY.md](DEPLOY.md)
- **群组配置**：[GROUP_SETUP.md](GROUP_SETUP.md)
- **项目说明**：[README.md](README.md)
