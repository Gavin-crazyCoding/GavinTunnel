# 通用端口穿透工具 v4.0

<div align="center">

**双引擎驱动 | 全协议支持 | 自动重连 | FTP专属优化**

[![Version](https://img.shields.io/badge/version-4.0.0-blue.svg)](https://github.com)
[![Python](https://img.shields.io/badge/python-3.6+-green.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)

</div>

---

## 目录

- [简介](#简介)
- [核心特性](#核心特性)
- [快速开始](#快速开始)
- [使用指南](#使用指南)
- [命令参考](#命令参考)
- [配置说明](#配置说明)
- [常见问题](#常见问题)
- [技术细节](#技术细节)

---

## 简介

`tunnel4.py` 是一款功能强大的端口穿透工具，基于 **Cloudflare Tunnel** 和 **cpolar** 双引擎驱动，可将内网服务安全地暴露到公网。

### 适用场景

- 远程访问内网 Web 服务、数据库、FTP 服务器
- 远程桌面连接（RDP/VNC）
- SSH 远程管理
- 开发环境公网测试
- FTP 文件传输（支持被动模式）

---

## 核心特性

### v4.0 新增功能

| 功能 | 描述 |
|------|------|
| **双引擎支持** | Cloudflare Tunnel + cpolar，自动切换备用方案 |
| **全协议兼容** | HTTP/HTTPS/TCP/UDP/SSH/FTP/MySQL/Redis/RDP/VNC/SMTP/DNS |
| **自动重试机制** | 隧道建立失败自动重试（指数退避算法） |
| **断线自动重连** | 运行中检测断线并自动恢复连接（最多 10 次） |
| **FTP专属优化** | 支持被动模式端口范围穿透 |
| **增强日志系统** | 完整错误日志持久化到 `tunnel_debug.log` |
| **交互式 UI** | 美观的命令行界面，支持主题切换 |
| **多语言支持** | 中文/英文切换 (`--lang zh/en`) |
| **配置备份** | 一键备份/恢复隧道配置 |

### 协议自动映射

所有协议自动映射到 Cloudflare 支持的 scheme：

```
HTTP     -> http://
HTTPS    -> https://
TCP/SSH/FTP/MySQL/Redis/RDP/VNC/SMTP -> tcp://
UDP/DNS  -> udp:// (需桥接)
```

---

## 快速开始

### 环境要求

- Python 3.6+
- Linux / macOS / Windows
- 支持架构：x86_64, aarch64, armv7l

### 安装

#### 第一步：安装 Cloudflared（必须）

> **重要提示**：程序的自动安装功能尚未完善，**请手动前往官网下载安装**。

**Cloudflare Tunnel 官方下载地址：**
- 官网：https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/
- GitHub：https://github.com/cloudflare/cloudflared/releases/latest

**Linux 快速安装：**
```bash
# AMD64 架构
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
chmod +x cloudflared-linux-amd64
sudo mv cloudflared-linux-amd64 /usr/local/bin/cloudflared

# ARM64 架构（树莓派等）
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64
chmod +x cloudflared-linux-arm64
sudo mv cloudflared-linux-arm64 /usr/local/bin/cloudflared

# 验证安装
cloudflared --version
```

**Windows 安装：**
1. 访问上述官网下载 `cloudflared-windows-amd64.exe`
2. 重命名为 `cloudflared.exe`
3. 放到系统 PATH 目录或与 `tunnel4.py` 同目录

#### 第二步：运行 tunnel4.py

```bash
# 下载 tunnel4.py
wget https://github.com/your-repo/tunnel4.py -O tunnel4.py
chmod +x tunnel4.py

# 运行
python3 tunnel4.py
```

> **注意**：cpolar 引擎可在首次运行时自动下载，但 Cloudflared 建议手动安装以获得最佳兼容性。

### 一键启动示例

```bash
# SSH 穿透（最常用）
python3 tunnel4.py server 22 --proto ssh

# Web 服务穿透
python3 tunnel4.py server 80 --proto http

# MySQL 数据库穿透
python3 tunnel4.py server 3306 --proto mysql

# FTP 穿透（含被动模式）
python3 tunnel4.py ftp --port 21 --pasv-ports 50000-50010
```

---

## 使用指南

### 1. 交互式模式（推荐新手）

直接运行进入交互式界面：

```bash
python3 tunnel4.py
```

界面预览：
```
======================================================================
   ████████╗██╗   ██╗██╗    ████████╗███████╗██████╗ ███╗   ███╗
   ╚══██╔══╝██║   ██║██║    ╚══██╔══╝██╔════╝██╔══██╗████╗ ████║
      ██║   ██║   ██║██║       ██║   █████╗  ██████╔╝██╔████╔██║
      ██║   ██║   ██║██║       ██║   ██╔══╝  ██╔══██╗██║╚██╔╝██║
      ██║   ╚██████╔╝██║       ██║   ███████╗██║  ██║██║ ╚═╝ ██║
      ╚═╝    ╚═════╝ ╚═╝       ╚═╝   ╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝

              通用端口穿透工具 v4.0.0 - 全功能无删减版
              双引擎：Cloudflare Tunnel + cpolar | 100%兼容原命令
              作者：Gavin Team
======================================================================

主菜单
选择操作
```

### 2. 命令行模式

#### 单端口穿透

```bash
# 基本用法
python3 tunnel4.py server <端口> --proto <协议>

# SSH 穿透示例
python3 tunnel4.py server 22 --proto ssh --ip 127.0.0.1

# 强制启动（跳过端口检测）
python3 tunnel4.py server 22 --proto ssh --force
```

#### 批量端口穿透

```bash
# 同时穿透多个端口
python3 tunnel4.py batch 22 3306 6379 --proto tcp

# 带仪表盘
python3 tunnel4.py batch 22 3306 6379 --proto tcp --dashboard
```

#### 自动扫描穿透

```bash
# 自动扫描并穿透所有监听端口
python3 tunnel4.py auto

# 排除特定端口
python3 tunnel4.py auto --exclude 22 80

# 包含系统端口 (1-1023)
python3 tunnel4.py auto --include-system
```

#### FTP专属穿透

```bash
# 仅控制通道
python3 tunnel4.py ftp --port 21 --ip 127.0.0.1

# 含被动模式端口范围
python3 tunnel4.py ftp --port 21 --pasv-ports 50000-50010

# 使用 cpolar 引擎
python3 tunnel4.py ftp --port 21 --use-cpolar
```

#### 客户端连接

```bash
# 连接到远程隧道
python3 tunnel4.py client <隧道地址> --local-port <本地端口> --proto tcp

# 示例
python3 tunnel4.py client abc123.trycloudflare.com --local-port 2222 --proto tcp
```

---

## 命令参考

### 全局参数

| 参数 | 简写 | 描述 |
|------|------|------|
| `--interactive` | `-i` | 启动交互模式 |
| `--version` | `-v` | 显示版本号 |
| `--debug` | | 启用调试模式（全量日志） |
| `--theme` | | UI 主题 (default/dark/light) |
| `--lang` | | 语言 (zh/en) |
| `--force` | `-f` | 跳过端口检测确认 |
| `--backup` | | 备份配置 |
| `--restore` | | 恢复配置 |
| `--list-services` | | 列出支持的服务 |

### 子命令

| 子命令 | 描述 | 示例 |
|--------|------|------|
| `server` | 单端口穿透 | `server 22 --proto ssh` |
| `batch` | 批量端口穿透 | `batch 22 3306 6379` |
| `auto` | 自动扫描穿透 | `auto --dashboard` |
| `ftp` | FTP专属穿透 | `ftp --port 21 --pasv-ports 50000-50010` |
| `client` | 客户端连接 | `client abc.cloudflare.com --local-port 2222` |
| `dashboard` | 启动仪表盘 | `dashboard --port 8000` |

---

## 配置说明

### 预设服务

| 服务 | 端口 | 协议 | 描述 |
|------|------|------|------|
| HTTP | 80 | http | Web 网站服务 |
| HTTPS | 443 | https | HTTPS 加密 Web 服务 |
| FTP | 21 | ftp | FTP 文件服务器 |
| SSH | 22 | ssh | SSH 安全 Shell |
| MySQL | 3306 | mysql | MySQL 数据库 |
| Redis | 6379 | redis | Redis 缓存 |
| RDP | 3389 | rdp | Windows 远程桌面 |
| VNC | 5900 | vnc | VNC 远程桌面 |
| SMTP | 25 | smtp | SMTP 邮件服务 |

### 配置文件

- `tunnel_config.json` - 隧道配置
- `tunnel_history.json` - 历史记录
- `tunnel_debug.log` - 调试日志
- `tunnels_info.json` - 隧道信息（批量模式生成）

### 备份与恢复

```bash
# 备份当前配置
python3 tunnel4.py --backup

# 恢复配置
python3 tunnel4.py --restore
```

---

## 常见问题

### Q1: 隧道建立失败怎么办？

**解决方案：**
1. 检查目标端口是否有服务运行
2. 使用 `--force` 参数跳过检测
3. 尝试切换引擎（Cloudflare/cpolar）
4. 查看日志文件 `tunnel_debug.log`

### Q2: FTP 文件传输失败？

**解决方案：**
确保同时穿透了被动模式端口：
```bash
python3 tunnel4.py ftp --port 21 --pasv-ports 50000-50010
```
并在 FTP 服务器配置相同的被动端口范围。

### Q3: 如何保持隧道长期运行？

**建议方案：**
- 使用 `screen` 或 `tmux` 后台运行
- 配合 systemd 创建服务
- 使用 `nohup`:
  ```bash
  nohup python3 tunnel4.py server 22 --proto ssh &
  ```

### Q4: UDP 协议如何使用？

UDP 协议需要桥接为 TCP 传输：
```bash
# DNS 服务穿透
python3 tunnel4.py server 53 --proto dns
```

### Q5: 程序提示找不到 cloudflared 怎么办？

**请手动安装 Cloudflared，不要等待程序自动下载。**

自动安装功能目前尚未完善，建议直接前往官网下载：

- **官方文档**：https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/
- **GitHub 下载**：https://github.com/cloudflare/cloudflared/releases/latest

安装后确保 `cloudflared` 命令可在终端中执行：
```bash
cloudflared --version  # 应显示版本号
```

---

## 已知问题

- **自动安装 cloudflared 功能不完善** - 请手动前往官网安装（见 Q5）
- 某些架构的自动下载可能失败 - 建议使用官方提供的安装包

---

## 技术细节

### 架构设计

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  内网服务    │────▶│ tunnel4.py   │────▶│  公网地址   │
│  (本地端口)  │     │ (协议映射)   │     │ (Cloudflare)│
└─────────────┘     └──────────────┘     └─────────────┘
```

### 日志系统

所有输出同时写入终端和日志文件：
- INFO - 一般信息
- SUCCESS - 成功状态
- WARN - 警告信息
- ERROR - 错误信息（红色高亮）
- DEBUG - 调试信息（需 `--debug` 启用）

### 自动重连机制

1. **建立失败重试**: 指数退避（2s → 4s → 8s → ... → 30s）
2. **运行中断线重连**: 检测进程退出自动重建隧道
3. **最大重连次数**: 10 次（可配置）

---

## 相关脚本

### ftp-tunnel.sh

FTP 隧道一键启动脚本：

```bash
# 用法
./ftp-tunnel.sh [端口] [IP] [被动端口范围]

# 示例
./ftp-tunnel.sh 21 127.0.0.1 50000-50010
```

### server.py

简易 HTTP 测试服务器（绑定 38830 端口）：

```bash
python3 server.py
# 访问：http://localhost:38830
```

---

## 更新日志

### v4.0.0 (2026-03-28)
- 全协议 Cloudflare 兼容性修复
- FTP 被动模式端口范围穿透
- 全局自动重试 + 断线自动重连
- 增强错误日志系统
- 交互式 UI + 主题切换
- 配置备份/恢复功能

### v3.x
- 基础隧道功能
- Server/Batch/Auto/Client 模式

---

## 致谢

- [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/)
- [cpolar](https://www.cpolar.com/)

---

## 许可证

MIT License

---

<div align="center">

**作者**: Gavin Team  
**版本**: v4.0.0  
**更新日期**: 2026-03-28

如有问题，请查看日志文件 `tunnel_debug.log`

</div>
