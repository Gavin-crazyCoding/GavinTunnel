#!/usr/bin/env python3
"""
通用端口穿透工具 v4.1 - TCP/Minecraft协议修复版
双引擎版 (Cloudflare Tunnel + cpolar) | 100%兼容原tunnel.py所有命令
保留原功能：server/batch/auto/client/dashboard/端口扫描/UDP桥接/隧道日志等
新增功能：交互式UI/20+协议预设/FTP专属穿透/配置备份/主题切换/调试模式
v4.0升级：
  - 全协议Cloudflare兼容修复（所有协议正确映射到http/tcp）
  - FTP穿透支持被动模式端口范围自动穿透
  - 全局自动重试+运行中断线自动重连（指数退避）
  - 增强错误日志系统，所有输出清晰可见并持久化到日志文件
原命令100%兼容，新增命令作为扩展
"""
import subprocess
import sys
import os
import re
import shutil
import platform
import urllib.request
import stat
import time
import socket
import threading
import signal
import argparse
import select
import json
import traceback
from typing import Optional, Tuple, List, Dict

# 全局配置
CLOUDFLARED_URL = {
    "x86_64": "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64",
    "aarch64": "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64",
    "armv7l": "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm",
    "Windows": "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe",
    "Darwin": "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-darwin-amd64"
}
CPOLAR_URL = {
    "x86_64": "https://static.cpolar.com/downloads/release/cpolar-stable-linux-amd64.tgz",
    "aarch64": "https://static.cpolar.com/downloads/release/cpolar-stable-linux-arm64.tgz",
    "armv7l": "https://static.cpolar.com/downloads/release/cpolar-stable-linux-arm.tgz",
    "Windows": "https://static.cpolar.com/downloads/cpolar-stable-windows-amd64.zip",
    "Darwin": "https://static.cpolar.com/downloads/release/cpolar-stable-darwin-amd64.tgz"
}
VERSION = "4.1.0"
AUTHOR = "Gavin Team"
CONFIG_FILE = "tunnel_config.json"
HISTORY_FILE = "tunnel_history.json"
BACKUP_DIR = "backups"
LOG_FILE = "tunnel_debug.log"

# ============================================================
# I18N 多语言支持 - 默认中文，可通过 --lang en 切换英文
# ============================================================

# 预扫描 --lang 参数
def _detect_lang():
    for i, arg in enumerate(sys.argv):
        if arg == '--lang' and i + 1 < len(sys.argv):
            return sys.argv[i + 1]
        if arg.startswith('--lang='):
            return arg.split('=', 1)[1]
    return 'zh'  # 默认中文

CURRENT_LANG = _detect_lang()

# 翻译字典
I18N = {
    'zh': {
        # argparse help
        'help_interactive': '启动交互模式',
        'help_list_services': '列出所有支持的服务',
        'help_backup': '备份当前配置',
        'help_restore': '恢复配置',
        'help_debug': '启用调试模式(全量日志输出)',
        'help_theme': 'UI主题',
        'help_lang': '语言(zh中文/en英文)',
        'help_mode': '运行模式',
        'help_ftp': 'FTP穿透(v4: 支持被动模式)',
        'help_ftp_port': 'FTP端口',
        'help_ftp_ip': 'FTP服务器IP',
        'help_use_cpolar': '使用cpolar引擎',
        'help_pasv_ports': '被动模式端口范围(如50000-50010)',
        'help_retries': '最大重试次数',
        'help_server': '单端口穿透',
        'help_port': '端口号',
        'help_proto': f'协议类型({"/".join(PROTO_TO_CF_SCHEME.keys()) if "PROTO_TO_CF_SCHEME" in dir() else "http/tcp/ssh等"})',
        'help_ip': '目标内网IP',
        'help_service': '预设服务名称',
        'help_batch': '批量端口穿透',
        'help_ports': '多个端口号',
        'help_dashboard': '启动仪表盘',
        'help_auto': '自动扫描穿透',
        'help_exclude': '排除端口',
        'help_include_system': '包含系统端口',
        'help_client': '客户端连接',
        'help_tunnel_host': '隧道地址',
        'help_local_port': '本地监听端口',
        'help_dash_port': '监听端口',
        'help_force': '跳过端口检测确认（自动化模式）',
        'mode_force': '强制启动 (跳过端口检测)',
        'log_force_continue': '使用 --force 参数，继续启动隧道...',
        # 描述
        'desc_tool': f'通用端口穿透工具 v{VERSION} - 全功能无删减版 | 作者: {AUTHOR}',
        # 日志
        'log_downloading': '正在下载',
        'log_download_ok': '下载完成!',
        'log_download_fail': '下载失败',
        'log_not_detected': '未检测到',
        'log_preparing_install': '准备自动安装...',
        'log_manual_install': '请手动安装',
        'log_unsupported_arch': '不支持的系统/架构',
        # UI
        'ui_menu_title': '主菜单',
        'ui_select_op': '请选择操作',
        'ui_press_enter': '按回车返回主菜单...',
        'ui_press_enter_back': '按回车返回...',
        'ui_invalid_input': '无效输入',
        'ui_invalid_choice': '无效选择',
        'ui_confirm': '确认',
        'ui_yes': '是',
        'ui_no': '否',
        # 模式
        'mode_server': '端口穿透 - 服务端模式 (v4)',
        'mode_client': '端口穿透 - 客户端模式 (v4)',
        'mode_batch': '批量端口穿透模式 (v4)',
        'mode_auto': '自动扫描模式 (v4)',
        'mode_ftp': 'FTP专属穿透模式 (v4)',
        'mode_dashboard': '仪表盘已启动',
        # 状态
        'status_tunnel_ok': '隧道已建立!',
        'status_tunnel_closed': '隧道已关闭',
        'status_client_closed': '客户端连接已关闭',
        'status_ftp_closed': 'FTP隧道已关闭',
        'status_log_file': '日志文件',
        'status_reconnect': '断线自动重连: 开启',
        'status_max_retries': '最大重试',
        # 提示
        'hint_press_ctrlc': '按 Ctrl+C 停止隧道',
        'hint_press_ctrlc_stop': '按 Ctrl+C 停止服务器',
        'hint_closing': '正在关闭...',
        'hint_keep_open': '注意: 保持此窗口打开，关闭则穿透失效',
        'hint_saved_to': '已保存到',
        # 其他
        'proto': '协议',
        'local_ip': '内网IP',
        'local_addr': '内网地址',
        'public_addr': '公网地址',
        'tunnel_addr': '隧道地址',
        'local_port': '本地端口',
        'port': '端口',
        'status': '状态',
        'listening': '监听中',
        'thanks': '感谢使用，再见！',
        'bye': '再见！',
    },
    'en': {
        # argparse help
        'help_interactive': 'Start interactive mode',
        'help_list_services': 'List all supported services',
        'help_backup': 'Backup current config',
        'help_restore': 'Restore config',
        'help_debug': 'Enable debug mode (full log output)',
        'help_theme': 'UI theme',
        'help_lang': 'Language (zh for Chinese / en for English)',
        'help_mode': 'Run mode',
        'help_ftp': 'FTP tunnel (v4: passive mode supported)',
        'help_ftp_port': 'FTP port',
        'help_ftp_ip': 'FTP server IP',
        'help_use_cpolar': 'Use cpolar engine',
        'help_pasv_ports': 'Passive mode port range (e.g. 50000-50010)',
        'help_retries': 'Max retries',
        'help_server': 'Single port tunnel',
        'help_port': 'Port number',
        'help_proto': 'Protocol type (http/tcp/ssh/ftp/mysql/redis/rdp/vnc/smtp/dns/udp)',
        'help_ip': 'Target local IP',
        'help_service': 'Preset service name',
        'help_batch': 'Batch port tunnel',
        'help_ports': 'Multiple port numbers',
        'help_dashboard': 'Start dashboard',
        'help_auto': 'Auto scan and tunnel',
        'help_exclude': 'Exclude ports',
        'help_include_system': 'Include system ports',
        'help_client': 'Client connection',
        'help_tunnel_host': 'Tunnel host address',
        'help_local_port': 'Local listen port',
        'help_dash_port': 'Listen port',
        'help_force': 'Skip port detection confirmation (automation mode)',
        'mode_force': 'Force start (skip port check)',
        'log_force_continue': 'Using --force, continuing tunnel startup...',
        # 描述
        'desc_tool': f'Port Tunnel Tool v{VERSION} - Full Featured | Author: {AUTHOR}',
        # 日志
        'log_downloading': 'Downloading',
        'log_download_ok': 'Download complete!',
        'log_download_fail': 'Download failed',
        'log_not_detected': 'Not detected',
        'log_preparing_install': 'Preparing to install...',
        'log_manual_install': 'Please install manually',
        'log_unsupported_arch': 'Unsupported system/architecture',
        # UI
        'ui_menu_title': 'Main Menu',
        'ui_select_op': 'Select operation',
        'ui_press_enter': 'Press Enter to return to main menu...',
        'ui_press_enter_back': 'Press Enter to return...',
        'ui_invalid_input': 'Invalid input',
        'ui_invalid_choice': 'Invalid choice',
        'ui_confirm': 'Confirm',
        'ui_yes': 'Y',
        'ui_no': 'N',
        # 模式
        'mode_server': 'Port Tunnel - Server Mode (v4)',
        'mode_client': 'Port Tunnel - Client Mode (v4)',
        'mode_batch': 'Batch Port Tunnel Mode (v4)',
        'mode_auto': 'Auto Scan Mode (v4)',
        'mode_ftp': 'FTP Tunnel Mode (v4)',
        'mode_dashboard': 'Dashboard started',
        # 状态
        'status_tunnel_ok': 'Tunnel established!',
        'status_tunnel_closed': 'Tunnel closed',
        'status_client_closed': 'Client connection closed',
        'status_ftp_closed': 'FTP tunnel closed',
        'status_log_file': 'Log file',
        'status_reconnect': 'Auto reconnect: ON',
        'status_max_retries': 'Max retries',
        # 提示
        'hint_press_ctrlc': 'Press Ctrl+C to stop tunnel',
        'hint_press_ctrlc_stop': 'Press Ctrl+C to stop server',
        'hint_closing': 'Closing...',
        'hint_keep_open': 'Note: Keep this window open, or tunnel will stop',
        'hint_saved_to': 'Saved to',
        # 其他
        'proto': 'Protocol',
        'local_ip': 'Local IP',
        'local_addr': 'Local address',
        'public_addr': 'Public address',
        'tunnel_addr': 'Tunnel address',
        'local_port': 'Local port',
        'port': 'Port',
        'status': 'Status',
        'listening': 'Listening',
        'thanks': 'Thanks for using, bye!',
        'bye': 'Bye!',
    }
}

def t(key: str) -> str:
    """获取翻译文本"""
    lang_dict = I18N.get(CURRENT_LANG, I18N['zh'])
    return lang_dict.get(key, I18N['zh'].get(key, key))

# ============================================================
# 日志系统 - v4 增强：所有错误清晰可见 + 持久化
# ============================================================
class Logger:
    """统一日志管理，解决错误日志看不清的问题"""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._debug = False
        return cls._instance

    def enable_debug(self):
        self._debug = True

    @property
    def debug_enabled(self):
        return self._debug

    def _write_file(self, msg: str):
        try:
            with open(LOG_FILE, 'a', encoding='utf-8') as f:
                f.write(msg + '\n')
        except Exception:
            pass

    def _ts(self) -> str:
        return time.strftime("%Y-%m-%d %H:%M:%S")

    def info(self, msg: str, tag: str = "INFO"):
        line = f"  \033[94m[{tag}]\033[0m {msg}"
        print(line)
        self._write_file(f"[{self._ts()}] [{tag}] {msg}")

    def success(self, msg: str, tag: str = "OK"):
        line = f"  \033[92m[{tag}]\033[0m {msg}"
        print(line)
        self._write_file(f"[{self._ts()}] [{tag}] {msg}")

    def warn(self, msg: str, tag: str = "WARN"):
        line = f"  \033[93m[{tag}]\033[0m {msg}"
        print(line)
        self._write_file(f"[{self._ts()}] [{tag}] {msg}")

    def error(self, msg: str, tag: str = "ERROR"):
        line = f"  \033[91m[{tag}]\033[0m {msg}"
        print(line)
        self._write_file(f"[{self._ts()}] [{tag}] {msg}")

    def debug(self, msg: str):
        if self._debug:
            line = f"  \033[2m[DEBUG {self._ts()}] {msg}\033[0m"
            print(line)
        self._write_file(f"[{self._ts()}] [DEBUG] {msg}")

    def tunnel_output(self, line: str, engine: str = "cloudflared"):
        """记录隧道引擎的原始输出，始终写文件，重要信息打印"""
        self._write_file(f"[{self._ts()}] [{engine}] {line}")
        # 始终显示错误和警告
        if any(kw in line for kw in ['ERR', 'error', 'failed', 'WARNING', 'fatal', 'panic']):
            if 'fetch features' not in line:
                print(f"  \033[91m[{engine}]\033[0m {line}")
        elif self._debug:
            print(f"  \033[2m[{engine}]\033[0m {line}")

log = Logger()


# ============================================================
# v4 核心：协议到Cloudflare的映射修复
# ============================================================
# Cloudflare Tunnel --url 参数只接受: http://, https://, tcp://
# 所有其他协议必须映射到这三种之一
PROTO_TO_CF_SCHEME = {
    'http': 'http',
    'https': 'https',
    'tcp': 'tcp',
    'ssh': 'tcp',      # SSH 走 TCP
    'ftp': 'tcp',      # FTP 控制通道走 TCP
    'mysql': 'tcp',    # MySQL 走 TCP
    'redis': 'tcp',    # Redis 走 TCP
    'rdp': 'tcp',      # RDP 走 TCP
    'vnc': 'tcp',      # VNC 走 TCP
    'smtp': 'tcp',     # SMTP 走 TCP
    'dns': 'udp',      # DNS 走 UDP（需桥接）
    'udp': 'udp',      # UDP 需桥接为 TCP
}

def resolve_cf_scheme(proto: str) -> str:
    """将用户指定的协议映射到Cloudflare支持的scheme"""
    return PROTO_TO_CF_SCHEME.get(proto.lower(), 'tcp')


# UI主题配置
THEMES = {
    'default': {'primary':'\033[36m','secondary':'\033[96m','success':'\033[92m','warning':'\033[93m','error':'\033[91m','info':'\033[94m','dim':'\033[2m','reset':'\033[0m'},
    'dark': {'primary':'\033[97m','secondary':'\033[96m','success':'\033[32m','warning':'\033[33m','error':'\033[31m','info':'\033[34m','dim':'\033[2m','reset':'\033[0m'},
    'light': {'primary':'\033[30m','secondary':'\033[34m','success':'\033[32m','warning':'\033[33m','error':'\033[31m','info':'\033[36m','dim':'\033[2m','reset':'\033[0m'}
}

# 预设服务模板
SERVICE_PRESETS = {
    'http': {'name':'HTTP Web服务','port':80,'proto':'http','icon':'[Web]','desc':'Web网站服务'},
    'https': {'name':'HTTPS 安全Web服务','port':443,'proto':'https','icon':'[SSL]','desc':'HTTPS加密Web服务'},
    'ftp': {'name':'FTP文件传输','port':21,'proto':'ftp','icon':'[FTP]','desc':'FTP文件服务器(支持被动模式)','special':'ftp'},
    'ssh': {'name':'SSH远程登录','port':22,'proto':'ssh','icon':'[SSH]','desc':'SSH安全Shell'},
    'mysql': {'name':'MySQL数据库','port':3306,'proto':'mysql','icon':'[DB]','desc':'MySQL关系型数据库'},
    'redis': {'name':'Redis缓存','port':6379,'proto':'redis','icon':'[KV]','desc':'Redis内存数据库'},
    'rdp': {'name':'Windows远程桌面','port':3389,'proto':'rdp','icon':'[RDP]','desc':'RDP远程桌面'},
    'vnc': {'name':'VNC远程桌面','port':5900,'proto':'vnc','icon':'[VNC]','desc':'VNC跨平台远程'},
    'smtp': {'name':'SMTP邮件服务','port':25,'proto':'smtp','icon':'[MTA]','desc':'SMTP邮件发送'},
    'custom': {'name':'自定义服务','port':0,'proto':'tcp','icon':'[*]','desc':'自定义端口和协议'}
}
SERVICE_CATEGORIES = {
    'web': {'name':'Web服务','icon':'[Web]','services':['http','https']},
    'file': {'name':'文件传输','icon':'[FTP]','services':['ftp']},
    'remote': {'name':'远程登录/桌面','icon':'[SSH]','services':['ssh','rdp','vnc']},
    'database': {'name':'数据库','icon':'[DB]','services':['mysql','redis']},
    'mail': {'name':'邮件服务','icon':'[MTA]','services':['smtp']},
    'custom': {'name':'自定义','icon':'[*]','services':['custom']}
}

# UI组件类
class UI:
    def __init__(self, theme='default'):
        self.theme = THEMES.get(theme, THEMES['default'])
    def set_theme(self, theme_name: str):
        self.theme = THEMES.get(theme_name, THEMES['default'])
    def clear_screen(self):
        os.system('clear' if os.name != 'nt' else 'cls')
    def print_banner(self):
        banner = f"""
{self.theme['primary']}======================================================================{self.theme['reset']}

{self.theme['success']}   ████████╗██╗   ██╗██╗    ████████╗███████╗██████╗ ███╗   ███╗
   ╚══██╔══╝██║   ██║██║    ╚══██╔══╝██╔════╝██╔══██╗████╗ ████║
      ██║   ██║   ██║██║       ██║   █████╗  ██████╔╝██╔████╔██║
      ██║   ██║   ██║██║       ██║   ██╔══╝  ██╔══██╗██║╚██╔╝██║
      ██║   ╚██████╔╝██║       ██║   ███████╗██║  ██║██║ ╚═╝ ██║
      ╚═╝    ╚═════╝ ╚═╝       ╚═╝   ╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝{self.theme['reset']}

{self.theme['secondary']}              通用端口穿透工具 v{VERSION} - 全功能无删减版{self.theme['reset']}
{self.theme['warning']}              双引擎: Cloudflare Tunnel + cpolar | 100%兼容原命令{self.theme['reset']}
{self.theme['info']}              作者: {AUTHOR}{self.theme['reset']}
{self.theme['dim']}              支持: HTTP/HTTPS/TCP/UDP/FTP/SSH/RDP/MySQL/Redis/SMTP{self.theme['reset']}
{self.theme['dim']}              v4新增: 自动重连 | 完整错误日志 | FTP被动模式 | 全协议修复{self.theme['reset']}

{self.theme['primary']}======================================================================{self.theme['reset']}
"""
        print(banner)
    def print_box(self, title: str, content: List[str], style: str = "primary"):
        color = self.theme.get(style, self.theme['primary'])
        width = max(len(title), max(len(line) for line in content) if content else 0) + 4
        width = max(width, 50)
        print(f"{color}╭{'─' * (width)}╮{self.theme['reset']}")
        print(f"{color}│{self.theme['reset']}  {self.theme['secondary']}{title.center(width - 2)}{self.theme['reset']}  {color}│{self.theme['reset']}")
        print(f"{color}├{'─' * (width)}┤{self.theme['reset']}")
        for line in content:
            padding = width - len(line) - 2
            print(f"{color}│{self.theme['reset']}  {line}{' ' * max(0, padding)}{color}│{self.theme['reset']}")
        print(f"{color}╰{'─' * (width)}╯{self.theme['reset']}")
    def print_menu(self, options: List[Tuple[str, str, str]], title: str = "选择操作"):
        print(f"\n{self.theme['primary']}┌─ {title}{'─' * (40 - len(title))}{self.theme['reset']}\n")
        for key, label, desc in options:
            print(f"  {self.theme['secondary']}[{self.theme['success']}{key}{self.theme['secondary']}]{self.theme['reset']}  {label}")
            print(f"         {self.theme['dim']}{desc}{self.theme['reset']}\n")
        print(f"{self.theme['primary']}└{'─' * 50}{self.theme['reset']}\n")
    def print_status(self, status: str, message: str):
        status_styles = {'success':(self.theme['success'],'[OK]'),'error':(self.theme['error'],'[!!]'),'warning':(self.theme['warning'],'[??]'),'info':(self.theme['info'],'[ii]')}
        color, icon = status_styles.get(status, (self.theme['dim'], '[--]'))
        print(f"  {color}{icon}{self.theme['reset']}  {message}")
    def input_prompt(self, prompt: str, default: str = "") -> str:
        if default:
            prompt_str = f"  {self.theme['secondary']}{prompt}{self.theme['reset']} [{self.theme['dim']}{default}{self.theme['reset']}]: "
        else:
            prompt_str = f"  {self.theme['secondary']}{prompt}{self.theme['reset']}: "
        try:
            result = input(prompt_str).strip()
            return result if result else default
        except EOFError:
            return default
    def confirm(self, prompt: str, default: bool = True) -> bool:
        hint = "Y/n" if default else "y/N"
        while True:
            try:
                choice = input(f"  {self.theme['secondary']}{prompt}{self.theme['reset']} [{self.theme['dim']}{hint}{self.theme['reset']}]: ").strip().lower()
                if not choice:
                    return default
                return choice in ('y', 'yes', '是')
            except EOFError:
                return default

# 系统架构获取
def get_sys_arch() -> Tuple[str, str]:
    sys_plat = platform.system()
    arch = platform.machine()
    if sys_plat == "Linux" and arch == "x86_64":
        return "Linux", "x86_64"
    elif sys_plat == "Linux" and arch == "aarch64":
        return "Linux", "aarch64"
    elif sys_plat == "Linux" and arch.startswith("arm"):
        return "Linux", "armv7l"
    elif sys_plat == "Windows":
        return "Windows", "x86_64"
    elif sys_plat == "Darwin":
        return "Darwin", "x86_64"
    else:
        return sys_plat, arch

# Cloudflared管理
def get_cloudflared_path() -> str:
    path = shutil.which("cloudflared")
    if path:
        return path
    local_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cloudflared")
    if platform.system() == "Windows":
        local_path += ".exe"
    if os.path.isfile(local_path) and os.access(local_path, os.X_OK):
        return local_path
    return ""

def install_cloudflared() -> str:
    sys_plat, arch = get_sys_arch()
    url = CLOUDFLARED_URL.get(arch, CLOUDFLARED_URL.get(sys_plat))
    if not url:
        log.error(f"不支持的系统/架构 {sys_plat}/{arch}")
        sys.exit(1)
    local_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cloudflared")
    if sys_plat == "Windows":
        local_path += ".exe"
    log.info(f"正在下载 cloudflared ({sys_plat}/{arch})...")
    try:
        urllib.request.urlretrieve(url, local_path)
        os.chmod(local_path, os.stat(local_path).st_mode | stat.S_IEXEC)
        log.success("cloudflared 下载完成!")
        return local_path
    except Exception as e:
        log.error(f"cloudflared 下载失败: {e}")
        log.error("请手动安装: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/")
        sys.exit(1)

def ensure_cloudflared() -> str:
    path = get_cloudflared_path()
    if not path:
        log.info("未检测到 cloudflared，准备自动安装...")
        path = install_cloudflared()
    return path

# Cpolar管理
def get_cpolar_path() -> str:
    path = shutil.which("cpolar")
    if path:
        return path
    local_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cpolar")
    if platform.system() == "Windows":
        local_path += ".exe"
    if os.path.isfile(local_path) and os.access(local_path, os.X_OK):
        return local_path
    return ""

def install_cpolar() -> str:
    import tarfile
    import zipfile
    sys_plat, arch = get_sys_arch()
    url = CPOLAR_URL.get(arch, CPOLAR_URL.get(sys_plat))
    if not url:
        log.error(f"不支持的系统/架构 {sys_plat}/{arch}")
        sys.exit(1)
    local_dir = os.path.dirname(os.path.abspath(__file__))
    local_archive = os.path.join(local_dir, "cpolar_archive")
    local_path = os.path.join(local_dir, "cpolar")
    if sys_plat == "Windows":
        local_path += ".exe"
        local_archive += ".zip"
    else:
        local_archive += ".tgz"
    log.info(f"正在下载 cpolar ({sys_plat}/{arch})...")
    try:
        urllib.request.urlretrieve(url, local_archive)
        if sys_plat == "Windows":
            with zipfile.ZipFile(local_archive, 'r') as zf:
                for file in zf.namelist():
                    if "cpolar.exe" in file:
                        zf.extract(file, local_dir)
                        shutil.move(os.path.join(local_dir, file), local_path)
                        break
        else:
            with tarfile.open(local_archive, 'r:gz') as tf:
                for file in tf.getmembers():
                    if "cpolar" in file.name and not file.isdir():
                        tf.extract(file, local_dir)
                        shutil.move(os.path.join(local_dir, file.name), local_path)
                        break
        os.remove(local_archive)
        os.chmod(local_path, os.stat(local_path).st_mode | stat.S_IEXEC)
        log.success("cpolar 下载解压完成!")
        return local_path
    except Exception as e:
        log.error(f"cpolar 下载失败: {e}")
        log.error("请手动安装: https://www.cpolar.com/download")
        sys.exit(1)

def ensure_cpolar() -> str:
    path = get_cpolar_path()
    if not path:
        log.info("未检测到 cpolar，准备自动安装...")
        path = install_cpolar()
    return path

# 端口检测
def check_tcp_port(port: int, ip: str = '127.0.0.1', timeout: float = 2) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        return s.connect_ex((ip, port)) == 0

def check_udp_port(port: int, ip: str = '127.0.0.1') -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.settimeout(0.5)
            s.sendto(b'\x00', (ip, port))
            try:
                s.recvfrom(1024)
                return True
            except socket.timeout:
                return True
            except ConnectionRefusedError:
                return False
    except Exception:
        return False

def check_ftp_server(port: int = 21, ip: str = '127.0.0.1') -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(3)
            if s.connect_ex((ip, port)) != 0:
                return False
            welcome = s.recv(1024).decode('utf-8', errors='ignore')
            return "220" in welcome
    except Exception:
        return False

# UDP-TCP桥接类
class UDPtoTCPBridge:
    def __init__(self, tcp_listen_port: int, udp_target_port: int, bind: str = '127.0.0.1'):
        self.tcp_listen_port = tcp_listen_port
        self.udp_target_port = udp_target_port
        self.bind = bind
        self.running = False
        self.server_socket = None
    def start(self):
        self.running = True
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.bind, self.tcp_listen_port))
        self.server_socket.listen(5)
        self.server_socket.settimeout(1.0)
        thread = threading.Thread(target=self._accept_loop, daemon=True)
        thread.start()
        log.debug(f"[桥接] TCP:{self.tcp_listen_port} <-> UDP:{self.bind}:{self.udp_target_port}")
    def _accept_loop(self):
        while self.running:
            try:
                conn, addr = self.server_socket.accept()
                t = threading.Thread(target=self._handle_client, args=(conn,), daemon=True)
                t.start()
            except socket.timeout:
                continue
            except Exception:
                if self.running:
                    pass
    def _handle_client(self, tcp_conn: socket.socket):
        udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_sock.settimeout(1.0)
        udp_target = (self.bind, self.udp_target_port)
        try:
            while self.running:
                ready, _, _ = select.select([tcp_conn, udp_sock], [], [], 1.0)
                for s in ready:
                    if s is tcp_conn:
                        length_bytes = self._recv_exact(tcp_conn, 4)
                        if not length_bytes:
                            return
                        length = int.from_bytes(length_bytes, 'big')
                        if length > 65535:
                            return
                        data = self._recv_exact(tcp_conn, length)
                        if not data:
                            return
                        udp_sock.sendto(data, udp_target)
                    elif s is udp_sock:
                        try:
                            data, _ = udp_sock.recvfrom(65535)
                            length = len(data).to_bytes(4, 'big')
                            tcp_conn.sendall(length + data)
                        except socket.timeout:
                            continue
        except Exception:
            pass
        finally:
            tcp_conn.close()
            udp_sock.close()
    def _recv_exact(self, sock: socket.socket, n: int) -> bytes:
        data = b''
        while len(data) < n:
            try:
                chunk = sock.recv(n - len(data))
                if not chunk:
                    return b''
                data += chunk
            except Exception:
                return b''
        return data
    def stop(self):
        self.running = False
        if self.server_socket:
            self.server_socket.close()

class TCPtoUDPBridge:
    def __init__(self, udp_listen_port: int, tcp_target_host: str, tcp_target_port: int, bind: str = '127.0.0.1'):
        self.udp_listen_port = udp_listen_port
        self.tcp_target_host = tcp_target_host
        self.tcp_target_port = tcp_target_port
        self.bind = bind
        self.running = False
        self.udp_socket = None
        self.tcp_conn = None
        self.client_addr = None
    def start(self):
        self.running = True
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.udp_socket.bind((self.bind, self.udp_listen_port))
        self.udp_socket.settimeout(1.0)
        self.tcp_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_conn.connect((self.tcp_target_host, self.tcp_target_port))
        self.tcp_conn.settimeout(1.0)
        t1 = threading.Thread(target=self._udp_to_tcp, daemon=True)
        t1.start()
        t2 = threading.Thread(target=self._tcp_to_udp, daemon=True)
        t2.start()
        log.debug(f"[桥接] UDP:{self.bind}:{self.udp_listen_port} <-> TCP:{self.tcp_target_host}:{self.tcp_target_port}")
    def _udp_to_tcp(self):
        while self.running:
            try:
                data, addr = self.udp_socket.recvfrom(65535)
                self.client_addr = addr
                length = len(data).to_bytes(4, 'big')
                self.tcp_conn.sendall(length + data)
            except socket.timeout:
                continue
            except Exception:
                break
    def _tcp_to_udp(self):
        while self.running:
            try:
                length_bytes = self._recv_exact(self.tcp_conn, 4)
                if not length_bytes:
                    break
                length = int.from_bytes(length_bytes, 'big')
                data = self._recv_exact(self.tcp_conn, length)
                if not data:
                    break
                if self.client_addr:
                    self.udp_socket.sendto(data, self.client_addr)
            except socket.timeout:
                continue
            except Exception:
                break
    def _recv_exact(self, sock: socket.socket, n: int) -> bytes:
        data = b''
        while len(data) < n:
            try:
                chunk = sock.recv(n - len(data))
                if not chunk:
                    return b''
                data += chunk
            except socket.timeout:
                if not self.running:
                    return b''
                continue
            except Exception:
                return b''
        return data
    def stop(self):
        self.running = False
        if self.udp_socket:
            self.udp_socket.close()
        if self.tcp_conn:
            self.tcp_conn.close()

# TCP转发类
class TCPForwarder:
    def __init__(self, listen_port: int, cloudflared: str, tunnel_host: str, bind: str = '127.0.0.1'):
        self.listen_port = listen_port
        self.cloudflared = cloudflared
        self.tunnel_host = tunnel_host
        self.bind = bind
        self.process = None
    def start(self):
        cmd = [self.cloudflared, "access", "tcp", "--hostname", f"https://{self.tunnel_host}", "--url", f"127.0.0.1:{self.listen_port}"]
        self.process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        log.debug(f"[转发] localhost:{self.listen_port} <-> {self.tunnel_host}")
    def stop(self):
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()

# 工具函数
def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


# ============================================================
# v4 核心：隧道启动 + 自动重试 + 完整日志
# ============================================================

def start_cloudflared_tunnel(cloudflared: str, local_ip: str, local_port: int, proto: str,
                              max_retries: int = 5, retry_base_delay: float = 2.0):
    """
    启动Cloudflare隧道 - v4增强版
    - 正确映射所有协议到Cloudflare支持的scheme
    - 指数退避重试
    - 所有输出写入日志文件，错误清晰显示
    """
    cf_scheme = resolve_cf_scheme(proto)

    # UDP需要桥接，不在这里处理
    if cf_scheme == 'udp':
        log.error(f"协议 '{proto}' 需要UDP桥接，请使用server_mode或TunnelInstance处理")
        return None, None

    local_url = f"{cf_scheme}://{local_ip}:{local_port}"
    cmd = [cloudflared, "tunnel", "--url", local_url]

    log.debug(f"Cloudflare命令: {' '.join(cmd)}")

    tunnel_url = None
    for attempt in range(1, max_retries + 1):
        if attempt > 1:
            delay = min(retry_base_delay * (2 ** (attempt - 2)), 30)
            log.warn(f"第 {attempt}/{max_retries} 次重试，等待 {delay:.0f} 秒...")
            time.sleep(delay)

        log.info(f"正在建立 Cloudflare 隧道 ({local_url})... [尝试 {attempt}/{max_retries}]")

        try:
            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1
            )
        except Exception as e:
            log.error(f"启动cloudflared失败: {e}")
            log.error(f"完整异常: {traceback.format_exc()}")
            continue

        error_occurred = False
        for line in process.stdout:
            line = line.strip()
            if not line:
                continue

            # 记录所有输出
            log.tunnel_output(line, "cloudflared")

            # 检查是否获取到隧道URL
            # 检查是否获取到隧道 URL
            # TCP 协议：匹配 xxx.trycloudflare.com:端口 格式（Minecraft 等直接 IP:端口连接）
            # HTTP/HTTPS协议：匹配 https://xxx.trycloudflare.com 格式
            if cf_scheme == 'tcp':
                # TCP 隧道地址格式：随机子域名.trycloudflare.com:随机端口
                match = re.search(r'([a-zA-Z0-9\-]+\.trycloudflare\.com:\d+)', line)
            else:
                # HTTP/HTTPS隧道地址格式：https://随机子域名.trycloudflare.com
                match = re.search(r'(https://[a-zA-Z0-9\-]+\.trycloudflare\.com)', line)
            if match:
                tunnel_url = match.group(1)
                log.success(f"隧道建立成功: {tunnel_url}")
                return process, tunnel_url

            # 检查致命错误
            if 'ERR' in line or 'error' in line.lower() or 'failed' in line.lower():
                if any(code in line for code in ['1101', '500', 'Internal Server Error',
                                                  'connection refused', 'protocol',
                                                  'unsupported', 'invalid']):
                    error_occurred = True
                    log.error(f"Cloudflare 返回错误: {line}")
                    break

            # 检查进程是否异常退出
            if process.poll() is not None:
                log.error(f"cloudflared 进程异常退出，返回码: {process.returncode}")
                error_occurred = True
                break

        if error_occurred:
            try:
                process.terminate()
                process.wait(timeout=3)
            except Exception:
                try:
                    process.kill()
                except Exception:
                    pass
            continue
        else:
            # 进程结束但没有获取到URL也没有明确错误
            log.warn("cloudflared 输出结束但未获取到隧道URL")
            return process, None

    log.error(f"已达最大重试次数 ({max_retries})，隧道建立失败")
    return None, None


def start_cpolar_tunnel(cpolar: str, local_ip: str, local_port: int, proto: str = 'tcp',
                         max_retries: int = 5, retry_base_delay: float = 2.0):
    """cpolar隧道启动 - v4增强版，带重试"""
    if proto not in ('tcp', 'udp'):
        proto = 'tcp'
    cmd = [cpolar, proto, f"{local_ip}:{local_port}"]

    for attempt in range(1, max_retries + 1):
        if attempt > 1:
            delay = min(retry_base_delay * (2 ** (attempt - 2)), 30)
            log.warn(f"cpolar 第 {attempt}/{max_retries} 次重试，等待 {delay:.0f} 秒...")
            time.sleep(delay)

        log.info(f"正在建立 cpolar 隧道... [尝试 {attempt}/{max_retries}]")

        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        except Exception as e:
            log.error(f"启动cpolar失败: {e}")
            continue

        tunnel_url = None
        error_occurred = False
        for line in process.stdout:
            line = line.strip()
            if not line:
                continue
            log.tunnel_output(line, "cpolar")

            match = re.search(r'https?://[a-zA-Z0-9\-\.]+\.cpolar\.io:\d+', line)
            if match:
                tunnel_url = match.group(0)
                break
            match = re.search(r'[a-zA-Z0-9\-\.]+\.cpolar\.io:\d+', line)
            if match and not tunnel_url:
                tunnel_url = f"http://{match.group(0)}"
                break

            if any(kw in line.lower() for kw in ['error', 'failed', 'fatal']):
                error_occurred = True
                break

        if tunnel_url:
            log.success(f"cpolar隧道建立成功: {tunnel_url}")
            return process, tunnel_url

        if error_occurred:
            try:
                process.terminate()
                process.wait(timeout=3)
            except Exception:
                pass
            continue

        if not tunnel_url:
            log.warn("未解析到cpolar公网地址，可通过cpolar仪表盘查看: http://127.0.0.1:9200")
            return process, None

    log.error(f"cpolar 已达最大重试次数 ({max_retries})")
    return None, None


# ============================================================
# v4 核心：运行中自动重连的隧道保活
# ============================================================

def keep_tunnel_alive_v4(process: subprocess.Popen, tunnel_type: str,
                          restart_func=None, max_reconnects: int = 10):
    """
    v4 隧道保活 - 检测断线后自动重连
    restart_func: 无参函数，返回 (new_process, new_url) 用于重建隧道
    """
    reconnect_count = 0

    while True:
        try:
            if process and process.stdout:
                for line in process.stdout:
                    line = line.strip()
                    if not line:
                        continue
                    log.tunnel_output(line, tunnel_type)

                    if tunnel_type == 'cpolar' and 'cpolar.io' in line:
                        log.info(f"[{tunnel_type}] {line}")

            # 输出流结束 - 进程可能已退出
            if process:
                ret = process.poll()
                if ret is not None:
                    log.warn(f"{tunnel_type} 进程已退出，返回码: {ret}")
                else:
                    log.warn(f"{tunnel_type} 输出流意外结束")

        except Exception as e:
            log.error(f"保活监控异常: {e}")

        # 尝试重连
        if restart_func and reconnect_count < max_reconnects:
            reconnect_count += 1
            delay = min(2 * (2 ** (reconnect_count - 1)), 60)
            log.warn(f"隧道断开，{delay:.0f} 秒后第 {reconnect_count}/{max_reconnects} 次自动重连...")
            time.sleep(delay)

            try:
                new_process, new_url = restart_func()
                if new_process:
                    process = new_process
                    if new_url:
                        log.success(f"重连成功! 新地址: {new_url}")
                    else:
                        log.success("重连成功!")
                    reconnect_count = 0  # 重连成功后重置计数器
                    continue
                else:
                    log.error("重连失败")
            except Exception as e:
                log.error(f"重连异常: {e}")
                log.debug(traceback.format_exc())
        else:
            if reconnect_count >= max_reconnects:
                log.error(f"已达最大重连次数 ({max_reconnects})，放弃重连")
            break

    log.warn("隧道保活结束")


# ============================================================
# v4 隧道实例类 - 带完整重试和协议修复
# ============================================================

class TunnelInstance:
    def __init__(self, port: int, proto: str, cloudflared: str, ip: str = '127.0.0.1'):
        self.port = port
        self.proto = proto
        self.cloudflared = cloudflared
        self.ip = ip
        self.process = None
        self.tunnel_url = None
        self.bridge = None
        self.bridge_port = None

    def _build_local_url(self) -> str:
        """v4: 正确构建Cloudflare支持的URL"""
        cf_scheme = resolve_cf_scheme(self.proto)

        if cf_scheme == 'udp':
            # UDP需要桥接
            self.bridge_port = _find_free_port()
            self.bridge = UDPtoTCPBridge(
                tcp_listen_port=self.bridge_port,
                udp_target_port=self.port,
                bind=self.ip
            )
            self.bridge.start()
            return f"tcp://127.0.0.1:{self.bridge_port}"

        return f"{cf_scheme}://{self.ip}:{self.port}"

    def start(self, max_retries: int = 5) -> bool:
        local_url = self._build_local_url()
        cmd = [self.cloudflared, "tunnel", "--url", local_url]

        log.debug(f"端口 {self.port} ({self.proto}) -> cloudflared --url {local_url}")

        for attempt in range(1, max_retries + 1):
            if attempt > 1:
                delay = min(2 * (2 ** (attempt - 2)), 30)
                log.warn(f"  端口 {self.port}: 第 {attempt}/{max_retries} 次重试 (等待{delay:.0f}s)...")
                time.sleep(delay)

            try:
                if self.process:
                    try:
                        self.process.terminate()
                        self.process.wait(timeout=2)
                    except Exception:
                        try:
                            self.process.kill()
                        except Exception:
                            pass

                self.process = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, bufsize=1
                )

                error_hit = False
                for line in self.process.stdout:
                    line = line.strip()
                    if not line:
                        continue
                    log.tunnel_output(line, f"cf-{self.port}")

                    # TCP 协议：匹配 xxx.trycloudflare.com:端口 格式
                    if self.proto.lower() in ('tcp', 'ssh', 'ftp', 'mysql', 'redis', 'rdp', 'vnc', 'smtp'):
                        match = re.search(r'([a-zA-Z0-9\-]+\.trycloudflare\.com:\d+)', line)
                    else:
                        match = re.search(r'(https://[a-zA-Z0-9\-]+\.trycloudflare\.com)', line)
                    if match:
                        self.tunnel_url = match.group(1)
                        return True

                    if 'ERR' in line and any(code in line for code in
                            ['1101', '500', 'Internal Server Error',
                             'connection refused', 'protocol', 'unsupported']):
                        error_hit = True
                        log.error(f"端口 {self.port}: {line}")
                        break

                    if self.process.poll() is not None:
                        log.error(f"端口 {self.port}: 进程异常退出 (code={self.process.returncode})")
                        error_hit = True
                        break

                if error_hit:
                    continue

            except Exception as e:
                log.error(f"端口 {self.port} 启动异常: {e}")
                log.debug(traceback.format_exc())

        return False

    def stop(self):
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
        if self.bridge:
            self.bridge.stop()


# ============================================================
# server模式 - v4增强：自动重连 + 协议修复 + 完整日志
# ============================================================

def server_mode(port: int, proto: str, ip: str = '127.0.0.1', max_retries: int = 5, force: bool = False):
    cloudflared = ensure_cloudflared()
    bridge = None
    bridge_port = None

    cf_scheme = resolve_cf_scheme(proto)
    print()
    print("=" * 60)
    print(f"  端口穿透 - 服务端模式 (v4)")
    print(f"  协议: {proto.upper()} -> Cloudflare scheme: {cf_scheme}")
    print(f"  内网地址: {ip}:{port}")
    print(f"  最大重试: {max_retries} 次 | 断线自动重连: 开启")
    print("=" * 60)
    print()

    # 端口检测
    if cf_scheme == 'udp' or proto == 'udp':
        if not check_udp_port(port, ip):
            log.warn(f"无法确认 UDP:{ip}:{port} 是否有服务 (UDP检测不完全可靠)")
    else:
        if not check_tcp_port(port, ip):
            log.warn(f"TCP:{ip}:{port} 似乎没有服务在运行")
            if not force:
                answer = input("  是否继续？(y/n): ").strip().lower()
                if answer != 'y':
                    sys.exit(0)
            else:
                log.info("使用 --force 参数，继续启动隧道...")

    def _do_start():
        """启动/重启隧道的函数，供保活使用"""
        nonlocal bridge, bridge_port

        if cf_scheme == 'udp' or proto == 'udp':
            if bridge:
                bridge.stop()
            bridge_port = _find_free_port()
            bridge = UDPtoTCPBridge(tcp_listen_port=bridge_port, udp_target_port=port, bind=ip)
            bridge.start()
            process, tunnel_url = start_cloudflared_tunnel(
                cloudflared, '127.0.0.1', bridge_port, 'tcp', max_retries=max_retries
            )
        else:
            process, tunnel_url = start_cloudflared_tunnel(
                cloudflared, ip, port, proto, max_retries=max_retries
            )
        return process, tunnel_url

    process, tunnel_url = _do_start()

    if not tunnel_url:
        log.error("无法建立隧道，请稍后再试")
        if bridge:
            bridge.stop()
        sys.exit(1)

    print()
    print("=" * 60)
    print(f"  隧道已建立!")
    print(f"  公网地址: {tunnel_url}")
    print(f"  内网地址: {ip}:{port} ({proto.upper()})")
    print("-" * 60)
    if proto in ('http', 'https'):
        print(f"  访问方式：浏览器或 curl 直接访问公网地址")
    elif proto in ('tcp', 'ssh', 'mysql', 'redis', 'rdp', 'vnc', 'smtp', 'ftp'):
        # TCP 协议显示直连信息（Minecraft 等）
        if ':' in tunnel_url:
            # 格式：xxx.trycloudflare.com:端口
            print(f"  Minecraft/TCP 直连地址：{tunnel_url}")
            print(f"  (在客户端中输入：{tunnel_url})")
        else:
            # HTTPS 格式，使用 client 模式
            display_host = tunnel_url.replace('https://', '')
            print(f"  对方连接命令:")
            print(f"    python3 tunnel4.py client {display_host} --local-port <本地端口> --proto tcp")
    elif proto == 'udp':
        display_host = tunnel_url.replace('https://', '')
        print(f"  对方连接命令:")
        print(f"    python3 tunnel4.py client {display_host} --local-port <本地端口> --proto udp")
    print("=" * 60)
    print()
    print("  [v4] 隧道断线将自动重连，按 Ctrl+C 停止隧道")
    print(f"  [v4] 详细日志保存在: {LOG_FILE}")
    print()
    try:
        keep_tunnel_alive_v4(process, 'cloudflared', restart_func=_do_start, max_reconnects=10)
    except KeyboardInterrupt:
        print("\n\n  正在关闭隧道...")
    finally:
        if process:
            try:
                process.terminate()
                process.wait(timeout=5)
            except Exception:
                try:
                    process.kill()
                except Exception:
                    pass
        if bridge:
            bridge.stop()
        print()
        print("=" * 60)
        print("  [隧道已关闭]")
        print(f"  [日志文件] {os.path.abspath(LOG_FILE)}")
        print("=" * 60)


# ============================================================
# client模式 - v4增强
# ============================================================

def client_mode(tunnel_host: str, local_port: int, proto: str, max_reconnects: int = 10):
    """客户端模式 - v4.1 增强版：支持断线自动重连"""
    cloudflared = ensure_cloudflared()
    bridge = None
    forwarder = None
    tunnel_host = tunnel_host.replace('https://', '').replace('http://', '').rstrip('/')
    reconnect_count = 0

    def _start_forwarder():
        """启动/重启转发器"""
        nonlocal bridge, forwarder
        if proto in ('tcp', 'ssh', 'mysql', 'redis', 'rdp', 'vnc', 'ftp', 'smtp'):
            forwarder = TCPForwarder(local_port, cloudflared, tunnel_host)
            forwarder.start()
            return forwarder
        elif proto == 'udp':
            tcp_bridge_port = _find_free_port()
            forwarder = TCPForwarder(tcp_bridge_port, cloudflared, tunnel_host)
            forwarder.start()
            time.sleep(2)
            bridge = TCPtoUDPBridge(udp_listen_port=local_port, tcp_target_host='127.0.0.1', tcp_target_port=tcp_bridge_port)
            bridge.start()
            return forwarder
        return None

    print()
    print("=" * 60)
    print(f"  端口穿透 - 客户端模式 (v4)")
    print(f"  协议：{proto.upper()}")
    print(f"  隧道地址：{tunnel_host}")
    print(f"  本地端口：{local_port}")
    print(f"  自动重连：开启 (最多{max_reconnects}次)")
    print("=" * 60)
    print()

    if proto in ('http', 'https'):
        print(f"  HTTP/HTTPS 协议无需客户端，直接访问:")
        print(f"    https://{tunnel_host}")
        print()
        print(f"  如需本地端口映射，请使用 TCP 模式")
        sys.exit(0)

    # 启动转发器
    _start_forwarder()
    print()
    log.success(f"{('UDP' if proto == 'udp' else proto.upper())} 隧道已连接!")
    print(f"  本地访问：127.0.0.1:{local_port}" + (" (UDP)" if proto == 'udp' else ""))
    print(f"  远端隧道：{tunnel_host}")
    print()
    print("  按 Ctrl+C 停止连接 (断线自动重连)")
    print()

    # 保活监控 + 自动重连
    while True:
        try:
            if forwarder and forwarder.process:
                if forwarder.process.poll() is not None:
                    log.warn(f"客户端进程已退出 (code={forwarder.process.returncode})")
                    break
                for line in forwarder.process.stdout:
                    line = line.strip()
                    if line:
                        log.tunnel_output(line, "client")
        except Exception as e:
            log.error(f"客户端监控异常：{e}")

        # 尝试重连
        if reconnect_count < max_reconnects:
            reconnect_count += 1
            delay = min(2 * (2 ** (reconnect_count - 1)), 30)
            log.warn(f"连接断开，{delay:.0f}秒后第{reconnect_count}/{max_reconnects}次自动重连...")
            time.sleep(delay)
            try:
                if forwarder:
                    forwarder.stop()
                _start_forwarder()
                log.success("重连成功!")
                reconnect_count = 0
            except Exception as e:
                log.error(f"重连失败：{e}")
        else:
            log.error(f"已达最大重连次数 ({max_reconnects})")
            break

    # 清理
    try:
        if forwarder:
            forwarder.stop()
        if bridge:
            bridge.stop()
    except Exception:
        pass
    print()
    print("=" * 60)
    print("  [客户端连接已关闭]")
    print(f"  [日志文件] {os.path.abspath(LOG_FILE)}")
    print("=" * 60)


def batch_mode(ports: list, proto: str, dashboard: bool = False, max_retries: int = 10, ip: str = '127.0.0.1'):
    cloudflared = ensure_cloudflared()
    print()
    print("=" * 70)
    print("  批量端口穿透模式 (v4)")
    print(f"  协议: {proto.upper()} -> Cloudflare: {resolve_cf_scheme(proto)}")
    print(f"  内网IP: {ip}")
    print(f"  端口数: {len(ports)}")
    print(f"  最大重试: {max_retries} 次 | 断线自动重连: 开启")
    print("=" * 70)
    print()

    log.info("检测端口状态...")
    available_ports = []
    for port in ports:
        if proto == 'udp':
            available_ports.append(port)
        else:
            if check_tcp_port(port, ip):
                available_ports.append(port)
            else:
                log.warn(f"[跳过] 端口 {ip}:{port} 无服务运行")
    if not available_ports:
        log.error("没有可用的端口")
        sys.exit(1)
    log.info(f"可穿透端口: {available_ports}")
    print()

    tunnels = []
    log.info("正在建立隧道...")
    print("-" * 70)
    for port in available_ports:
        print(f"  [{len(tunnels)+1}/{len(available_ports)}] 端口 {ip}:{port} ...", end=" ", flush=True)
        tunnel = TunnelInstance(port, proto, cloudflared, ip)
        if tunnel.start(max_retries=max_retries):
            tunnels.append(tunnel)
            print(f"OK {tunnel.tunnel_url}")
        else:
            print(f"FAIL (已重试{max_retries}次)")
            tunnel.stop()

    if not tunnels:
        log.error("所有隧道启动失败")
        sys.exit(1)

    print()
    print("=" * 70)
    print("  隧道汇总")
    print("=" * 70)
    print()
    print(f"  {'内网地址':<20} {'协议':<8} {'公网地址'}")
    print("  " + "-" * 70)
    for t in tunnels:
        print(f"  {t.ip}:{t.port:<18} {t.proto.upper():<8} {t.tunnel_url}")
    print()
    print("-" * 70)

    save_file = "tunnels_info.json"
    tunnel_info = {
        "start_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "version": VERSION,
        "protocol": proto,
        "local_ip": ip,
        "tunnels": [{"local_ip": t.ip, "local_port": t.port, "public_url": t.tunnel_url} for t in tunnels]
    }
    with open(save_file, 'w') as f:
        json.dump(tunnel_info, f, indent=2, ensure_ascii=False)
    log.info(f"隧道信息已保存到: {save_file}")

    if dashboard:
        dashboard_port = _find_free_port()
        dashboard_httpd = start_dashboard_server(dashboard_port)
        if dashboard_httpd:
            print(f"  仪表盘本地地址: http://localhost:{dashboard_port}/dashboard.html")
            print(f"  正在穿透仪表盘到公网...", end=" ", flush=True)
            dash_tunnel = TunnelInstance(dashboard_port, 'http', cloudflared)
            if dash_tunnel.start(max_retries=max_retries):
                tunnels.append(dash_tunnel)
                dashboard_url = dash_tunnel.tunnel_url + "/dashboard.html"
                print(f"OK")
                print(f"  仪表盘公网地址: {dashboard_url}")
                tunnel_info["dashboard_url"] = dashboard_url
                with open(save_file, 'w') as f:
                    json.dump(tunnel_info, f, indent=2, ensure_ascii=False)
            else:
                print("FAIL 穿透失败，仅本地可访问")

    print()
    print(f"  [v4] 断线将自动重连，日志: {LOG_FILE}")
    print("  按 Ctrl+C 停止所有隧道")
    print("=" * 70)
    print()

    try:
        while True:
            for t in tunnels:
                if t.process and t.process.poll() is not None:
                    log.warn(f"端口 {t.port} 的隧道已断开，正在自动重连...")
                    if t.start(max_retries=max_retries):
                        log.success(f"端口 {t.port} 重连成功! 新地址: {t.tunnel_url}")
                        # 更新保存文件
                        tunnel_info["tunnels"] = [
                            {"local_ip": tt.ip, "local_port": tt.port, "public_url": tt.tunnel_url}
                            for tt in tunnels
                        ]
                        with open(save_file, 'w') as f:
                            json.dump(tunnel_info, f, indent=2, ensure_ascii=False)
                    else:
                        log.error(f"端口 {t.port} 重连失败")
            time.sleep(5)
    except KeyboardInterrupt:
        print("\n\n  正在关闭所有隧道...")
    finally:
        for t in tunnels:
            t.stop()
        if 'dashboard_httpd' in locals() and dashboard_httpd:
            dashboard_httpd.shutdown()
        print()
        print("=" * 70)
        print(f"  [已关闭 {len(tunnels)} 个隧道]")
        print(f"  [日志文件] {os.path.abspath(LOG_FILE)}")
        print("=" * 70)


# 端口扫描
def scan_local_ports(proto: str = 'tcp', exclude: list = None, ip: str = '127.0.0.1') -> list:
    exclude = exclude or []
    listening = []
    try:
        if proto in ('tcp', 'http', 'https') or resolve_cf_scheme(proto) == 'tcp':
            result = subprocess.run(['ss', '-tlnp'], capture_output=True, text=True)
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    match = re.search(r'[:\*](\d+)\s', line)
                    if match and 'LISTEN' in line:
                        port = int(match.group(1))
                        if 1 < port < 65535 and port not in exclude:
                            listening.append(port)
                return sorted(set(listening))
        if proto == 'udp':
            result = subprocess.run(['ss', '-ulnp'], capture_output=True, text=True)
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    match = re.search(r'[:\*](\d+)\s', line)
                    if match and 'UNCONN' in line:
                        port = int(match.group(1))
                        if 1 < port < 65535 and port not in exclude:
                            listening.append(port)
                return sorted(set(listening))
    except FileNotFoundError:
        pass
    try:
        flag = '-tlnp' if proto in ('tcp', 'http', 'https') else '-ulnp'
        result = subprocess.run(['netstat', flag], capture_output=True, text=True)
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                match = re.search(r':(\d+)\s', line)
                if match and 'LISTEN' in line:
                    port = int(match.group(1))
                    if 1 < port < 65535 and port not in exclude:
                        listening.append(port)
            return sorted(set(listening))
    except FileNotFoundError:
        pass
    log.warn("未找到 ss/netstat，使用端口探测（较慢）...")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        for port in range(1, 65535):
            if port in exclude:
                continue
            try:
                s.settimeout(0.01)
                if s.connect_ex((ip, port)) == 0:
                    listening.append(port)
            except Exception:
                pass
    return sorted(set(listening))


# auto模式
def auto_mode(proto: str, dashboard: bool, exclude: list, include_system: bool, max_retries: int = 10, ip: str = '127.0.0.1'):
    print()
    print("=" * 70)
    print("  自动扫描模式 (v4)")
    print(f"  协议: {proto.upper()}")
    print(f"  内网IP: {ip}")
    print("=" * 70)
    print()
    log.info("正在扫描本地监听端口...")
    system_ports = list(range(1, 1024)) if not include_system else []
    exclude_all = list(set(exclude + system_ports))
    ports = scan_local_ports(proto, exclude=exclude_all, ip=ip)
    if not ports:
        log.warn("未发现任何监听端口")
        sys.exit(0)
    print(f"  发现 {len(ports)} 个端口:")
    print()
    print(f"  {'端口':<10} {'状态'}")
    print("  " + "-" * 30)
    for p in ports:
        print(f"  {p:<10} 监听中")
    print()
    answer = input(f"  是否穿透以上所有 {len(ports)} 个端口? (y/n/自定义如 38815,38816): ").strip()
    if answer.lower() == 'n':
        sys.exit(0)
    elif answer.lower() != 'y':
        try:
            ports = [int(p.strip()) for p in answer.split(',') if p.strip()]
        except ValueError:
            log.error("端口格式无效")
            sys.exit(1)
    print()
    batch_mode(ports, proto, dashboard, max_retries=max_retries, ip=ip)


# dashboard
def start_dashboard_server(port: int):
    try:
        import http.server
        import socketserver
        class Handler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=os.path.dirname(os.path.abspath(__file__)), **kwargs)
        httpd = socketserver.TCPServer(("127.0.0.1", port), Handler)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        log.info(f"仪表盘服务器已启动: http://localhost:{port}")
        return httpd
    except Exception as e:
        log.warn(f"仪表盘启动失败: {e}")
        return None


# ============================================================
# v4 FTP模式 - 支持被动模式端口范围穿透 + 自动重连
# ============================================================

def ftp_mode(port: int = 21, ip: str = '127.0.0.1', use_cpolar: bool = False,
             pasv_ports: str = "", max_retries: int = 5):
    """
    v4 FTP穿透 - 增强版
    - 控制通道(21)穿透
    - 被动模式数据通道端口范围穿透（可选）
    - 自动重试 + 断线重连
    - 完整错误日志
    """
    ui = UI()
    pasv_range = []
    if pasv_ports:
        try:
            parts = pasv_ports.split('-')
            if len(parts) == 2:
                start_p, end_p = int(parts[0]), int(parts[1])
                pasv_range = list(range(start_p, end_p + 1))
            else:
                pasv_range = [int(p.strip()) for p in pasv_ports.split(',')]
        except ValueError:
            log.error(f"被动端口格式无效: {pasv_ports} (应为: 50000-50010 或 50000,50001,50002)")
            sys.exit(1)

    content = [
        f"内网FTP地址: {ip}:{port}",
        f"穿透引擎: {'cpolar' if use_cpolar else 'Cloudflare Tunnel'}",
        f"最大重试: {max_retries} 次 | 断线自动重连: 开启",
    ]
    if pasv_range:
        content.append(f"被动模式端口: {pasv_ports} (共{len(pasv_range)}个)")
    else:
        content.append("被动模式端口: 未指定 (仅穿透控制通道)")
        content.append("提示: 用 --pasv-ports 50000-50010 穿透被动模式")

    ui.print_box("FTP专属穿透模式 (v4)", content)

    log.info("检测FTP服务器连通性...")
    if check_ftp_server(port, ip):
        log.success(f"检测到有效FTP服务器: {ip}:{port}")
    else:
        if check_tcp_port(port, ip):
            log.warn(f"检测到{ip}:{port}端口开放，但非标准FTP响应")
            if not ui.confirm("是否继续穿透?"):
                sys.exit(0)
        else:
            log.error(f"未检测到{ip}:{port}端口开放")
            if not ui.confirm("是否继续穿透?"):
                sys.exit(0)

    # 启动控制通道隧道
    process = None
    tunnel_url = None
    all_tunnels = []

    def _start_control():
        """启动/重启控制通道"""
        if use_cpolar:
            cpolar = ensure_cpolar()
            return start_cpolar_tunnel(cpolar, ip, port, 'tcp', max_retries=max_retries)
        else:
            cloudflared = ensure_cloudflared()
            return start_cloudflared_tunnel(cloudflared, ip, port, 'tcp', max_retries=max_retries)

    process, tunnel_url = _start_control()

    if not process:
        log.error("无法建立FTP控制通道隧道，请稍后再试")
        sys.exit(1)

    all_tunnels.append(('control', port, process, tunnel_url))

    # 穿透被动模式端口
    pasv_tunnels = []
    if pasv_range:
        cloudflared = ensure_cloudflared()
        log.info(f"正在穿透 {len(pasv_range)} 个被动模式端口...")
        for pport in pasv_range:
            t = TunnelInstance(pport, 'tcp', cloudflared, ip)
            if t.start(max_retries=max_retries):
                pasv_tunnels.append(t)
                log.success(f"被动端口 {pport} -> {t.tunnel_url}")
            else:
                log.error(f"被动端口 {pport} 穿透失败")
                t.stop()

    print()
    print("=" * 60)
    print(f"  FTP隧道已建立! (v4)")
    if tunnel_url:
        print(f"  公网访问地址: {tunnel_url}")
        if '://' in tunnel_url:
            display_url = tunnel_url.split('://')[-1]
        else:
            display_url = tunnel_url
        ftp_host = display_url.split(':')[0]
        ftp_port = display_url.split(':')[-1] if ':' in display_url else '21'
        print(f"  FTP客户端连接信息:")
        print(f"    主机: {ftp_host}")
        print(f"    端口: {ftp_port}")
        print(f"    账号/密码: 内网FTP原账号密码")
    else:
        print(f"  公网地址请查看隧道日志/仪表盘")

    if pasv_tunnels:
        print(f"  被动模式端口穿透: {len(pasv_tunnels)}/{len(pasv_range)} 成功")
    elif pasv_range:
        log.warn("所有被动模式端口穿透失败，FTP可能无法传输文件")
    else:
        print()
        print("  提示: 当前仅穿透了控制通道(端口21)")
        print("  如果FTP文件传输失败，需要同时穿透被动模式端口:")
        print(f"    python3 tunnel4.py ftp --port {port} --pasv-ports 50000-50010")
        print("  并在FTP服务器中配置相同的被动端口范围")

    print("=" * 60)
    print()
    print("  注意: 保持此窗口打开，关闭则穿透失效")
    print(f"  [v4] 断线自动重连 | 日志: {LOG_FILE}")
    print("  按 Ctrl+C 停止FTP隧道")
    print()

    try:
        keep_tunnel_alive_v4(process, 'cpolar' if use_cpolar else 'cloudflared',
                             restart_func=_start_control, max_reconnects=10)
    except KeyboardInterrupt:
        print("\n\n  正在关闭FTP隧道...")
    finally:
        if process:
            try:
                process.terminate()
                process.wait(timeout=5)
            except Exception:
                try:
                    process.kill()
                except Exception:
                    pass
        for t in pasv_tunnels:
            t.stop()
        print()
        print("=" * 60)
        print(f"  [FTP隧道已关闭] 控制通道 + {len(pasv_tunnels)} 个被动端口")
        print(f"  [日志文件] {os.path.abspath(LOG_FILE)}")
        print("=" * 60)


# 配置备份
def backup_config():
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    backup_name = f"backup_{timestamp}"
    backup_path = os.path.join(BACKUP_DIR, backup_name)
    os.makedirs(backup_path)
    files_to_backup = [CONFIG_FILE, HISTORY_FILE, LOG_FILE, "tunnels_info.json"]
    backed_up = []
    for filename in files_to_backup:
        if os.path.exists(filename):
            try:
                shutil.copy2(filename, backup_path)
                backed_up.append(filename)
            except Exception as e:
                log.error(f"备份 {filename} 失败: {e}")
    backup_info = {"timestamp": time.strftime("%Y-%m-%d %H:%M:%S"), "files": backed_up, "version": VERSION}
    with open(os.path.join(backup_path, "backup_info.json"), 'w') as f:
        json.dump(backup_info, f, indent=2, ensure_ascii=False)
    log.success(f"配置已备份到: {backup_path}")
    print(f"  备份文件: {', '.join(backed_up)}")

# 配置恢复
def restore_config():
    if not os.path.exists(BACKUP_DIR):
        log.error("没有找到备份目录")
        return False
    backups = [d for d in os.listdir(BACKUP_DIR) if os.path.isdir(os.path.join(BACKUP_DIR, d))]
    if not backups:
        log.error("没有可用的备份")
        return False
    print(f"\n可用备份:")
    for i, backup in enumerate(sorted(backups, reverse=True)):
        print(f"  [{i+1}] {backup}")
    print()
    try:
        choice = int(input("选择要恢复的备份: ")) - 1
        if 0 <= choice < len(backups):
            backup_path = os.path.join(BACKUP_DIR, sorted(backups, reverse=True)[choice])
        else:
            log.error("无效选择")
            return False
    except ValueError:
        log.error("请输入数字")
        return False
    if not os.path.exists(backup_path):
        log.error(f"备份目录不存在: {backup_path}")
        return False
    restored = []
    for filename in os.listdir(backup_path):
        if filename != "backup_info.json":
            src = os.path.join(backup_path, filename)
            dst = filename
            try:
                shutil.copy2(src, dst)
                restored.append(filename)
                log.success(f"已恢复 {filename}")
            except Exception as e:
                log.error(f"恢复 {filename} 失败: {e}")
    if restored:
        log.success(f"恢复完成! 恢复了 {len(restored)} 个文件")
        return True
    else:
        log.error("没有文件被恢复")
        return False


# ============================================================
# 交互式模式
# ============================================================

def interactive_mode(ui: UI):
    ui.clear_screen()
    ui.print_banner()
    system, arch = get_sys_arch()
    print(f"{ui.theme['dim']}  系统: {system} | 架构: {arch} | 版本: v{VERSION} | 100%兼容原tunnel.py所有命令{ui.theme['reset']}\n")

    while True:
        options = [
            ('1', '[快速] 预设服务穿透', 'SSH/FTP/MySQL/Redis/RDP等一键穿透'),
            ('2', '[FTP] FTP专属穿透', '支持被动模式端口范围穿透(v4新增)'),
            ('3', '[单口] 单端口穿透', '自定义端口/协议/IP，兼容原server模式'),
            ('4', '[批量] 批量端口穿透', '多端口同时穿透+断线重连，兼容原batch模式'),
            ('5', '[扫描] 自动扫描穿透', '自动扫描监听端口，兼容原auto模式'),
            ('6', '[备份] 备份配置', '备份隧道配置/历史/日志文件'),
            ('7', '[恢复] 恢复配置', '从备份恢复隧道配置'),
            ('h', '[帮助] 帮助文档', '查看原命令+新增命令用法'),
            ('q', '[退出] 退出', '退出交互式界面'),
        ]
        ui.print_menu(options, "主菜单")
        choice = ui.input_prompt("请选择操作", "1").lower()

        if choice == '1':
            ui.clear_screen()
            ui.print_box("快速预设服务穿透", ["选择以下预设服务，一键穿透到公网", "v4: 所有协议已修复Cloudflare兼容性"])
            service_list = list(SERVICE_PRESETS.keys())
            for i, svc_key in enumerate(service_list):
                svc = SERVICE_PRESETS[svc_key]
                print(f"  [{i+1}] {svc['icon']} {svc['name']} - 端口{svc['port']} | {svc['desc']}")
            try:
                svc_idx = int(ui.input_prompt("输入服务序号", "1")) - 1
            except ValueError:
                ui.print_status('error', t('ui_invalid_input'))
                input(f"\n{ui.theme['dim']}{t('ui_press_enter')}{ui.theme['reset']}")
                ui.clear_screen()
                ui.print_banner()
                continue
            if 0 <= svc_idx < len(service_list):
                svc_key = service_list[svc_idx]
                svc = SERVICE_PRESETS[svc_key]
                ip = ui.input_prompt("目标内网IP", "127.0.0.1")
                port = int(ui.input_prompt("服务端口", str(svc['port'])))
                if svc_key == 'ftp':
                    pasv = ui.input_prompt("被动模式端口范围(可选,如50000-50010)", "")
                    if ui.confirm(f"确认穿透 {svc['name']} {ip}:{port}?"):
                        ftp_mode(port, ip, pasv_ports=pasv)
                        print()
                        input(f"{ui.theme['dim']}{t('ui_press_enter')}{ui.theme['reset']}")
                else:
                    if ui.confirm(f"确认穿透 {svc['name']} {ip}:{port}?"):
                        server_mode(port, svc['proto'], ip)
                        print()
                        input(f"{ui.theme['dim']}{t('ui_press_enter')}{ui.theme['reset']}")
        elif choice == '2':
            ip = ui.input_prompt("FTP服务器内网IP", "127.0.0.1")
            port = int(ui.input_prompt("FTP端口", "21"))
            pasv = ui.input_prompt("被动模式端口范围(可选,如50000-50010)", "")
            use_cpolar = ui.confirm("是否使用cpolar引擎（Cloudflare失败时用）?", False)
            ftp_mode(port, ip, use_cpolar, pasv_ports=pasv)
            print()
            input(f"{ui.theme['dim']}{t('ui_press_enter')}{ui.theme['reset']}")
        elif choice == '3':
            all_protos = list(PROTO_TO_CF_SCHEME.keys())
            print(f"\n  支持的协议: {', '.join(all_protos)}")
            proto = ui.input_prompt("协议", "tcp")
            if proto not in PROTO_TO_CF_SCHEME:
                log.warn(f"未知协议 '{proto}'，将作为TCP处理")
            port = int(ui.input_prompt("端口号", "22"))
            ip = ui.input_prompt("目标内网IP", "127.0.0.1")
            if ui.confirm(f"确认穿透 {ip}:{port} ({proto.upper()})?"):
                server_mode(port, proto, ip)
                print()
                input(f"{ui.theme['dim']}{t('ui_press_enter')}{ui.theme['reset']}")
        elif choice == '4':
            ports_str = ui.input_prompt("输入批量端口（用空格分隔）", "22 3306 6379")
            ports = [int(p) for p in ports_str.split() if p.strip().isdigit()]
            proto = ui.input_prompt("协议", "tcp")
            dashboard = ui.confirm("是否启动仪表盘?", False)
            if ui.confirm(f"确认批量穿透 {len(ports)} 个端口 ({proto.upper()})?"):
                batch_mode(ports, proto, dashboard=dashboard)
                print()
                input(f"{ui.theme['dim']}{t('ui_press_enter')}{ui.theme['reset']}")
        elif choice == '5':
            proto = ui.input_prompt("协议", "tcp")
            dashboard = ui.confirm("是否启动仪表盘?", False)
            include_system = ui.confirm("是否包含系统端口(1-1023)?", False)
            if ui.confirm(f"确认自动扫描 {proto.upper()} 端口并穿透?"):
                auto_mode(proto, dashboard=dashboard, exclude=[], include_system=include_system)
                print()
                input(f"{ui.theme['dim']}{t('ui_press_enter')}{ui.theme['reset']}")
        elif choice == '6':
            backup_config()
            print()
            input(f"{ui.theme['dim']}{t('ui_press_enter')}{ui.theme['reset']}")
        elif choice == '7':
            restore_config()
            print()
            input(f"{ui.theme['dim']}{t('ui_press_enter')}{ui.theme['reset']}")
        elif choice == 'h':
            ui.clear_screen()
            help_content = [
                "原tunnel.py兼容命令（直接运行）:",
                "  python tunnel4.py server <端口> --proto <协议>  # 单端口穿透",
                "  python tunnel4.py batch <端口1> <端口2> ...    # 批量穿透",
                "  python tunnel4.py auto [--dashboard]          # 自动扫描穿透",
                "  python tunnel4.py client <隧道地址> --local-port <端口> --proto <协议>",
                "  python tunnel4.py dashboard --port <端口>     # 启动仪表盘",
                "",
                "v4 新增/增强命令:",
                "  python tunnel4.py              # 启动交互式UI",
                "  python tunnel4.py ftp --port 21 --pasv-ports 50000-50010  # FTP被动模式",
                "  python tunnel4.py server 22 --proto ssh       # SSH(自动映射TCP)",
                "  python tunnel4.py server 3306 --proto mysql   # MySQL(自动映射TCP)",
                "  python tunnel4.py --theme <dark/light>        # 切换主题",
                "  python tunnel4.py --backup                    # 备份配置",
                "  python tunnel4.py --restore                   # 恢复配置",
                "  python tunnel4.py --debug                     # 调试模式(全量日志)",
                "  python tunnel4.py --list-services             # 列出支持的服务",
                "",
                "v4 改进:",
                "  - 所有协议自动映射到Cloudflare支持的scheme",
                "  - 隧道失败自动重试(指数退避)",
                "  - 运行中断线自动重连(最多10次)",
                f"  - 完整日志保存到: {LOG_FILE}",
                "  - FTP被动模式端口范围穿透",
            ]
            ui.print_box("使用帮助", help_content)
            input(f"\n{ui.theme['dim']}{t('ui_press_enter_back')}{ui.theme['reset']}")
        elif choice == 'q':
            print(f"\n{ui.theme['info']}{t('thanks')}{ui.theme['reset']}\n")
            break
        else:
            ui.print_status('error', f"{t('ui_invalid_choice')}: {choice}")
            input(f"\n{ui.theme['dim']}{t('ui_press_enter')}{ui.theme['reset']}")

        # 操作完成后清屏并重新显示主界面
        ui.clear_screen()
        ui.print_banner()
        system, arch = get_sys_arch()
        print(f"{ui.theme['dim']}  系统: {system} | 架构: {arch} | 版本: v{VERSION} | 100%兼容原tunnel.py所有命令{ui.theme['reset']}\n")


# ============================================================
# 主入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description=t('desc_tool'),
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('--interactive', '-i', action='store_true', help=t('help_interactive'))
    parser.add_argument('--version', '-v', action='version', version=f'%(prog)s {VERSION} by {AUTHOR}')
    parser.add_argument('--list-services', action='store_true', help=t('help_list_services'))
    parser.add_argument('--backup', action='store_true', help=t('help_backup'))
    parser.add_argument('--restore', nargs='?', const='interactive', help=t('help_restore'))
    parser.add_argument('--debug', action='store_true', help=t('help_debug'))
    parser.add_argument('--theme', choices=['default', 'dark', 'light'], default='default', help=t('help_theme'))
    parser.add_argument('--lang', choices=['zh', 'en'], default='zh', help=t('help_lang'))
    parser.add_argument('--force', '-f', action='store_true', help=t('help_force'))

    subparsers = parser.add_subparsers(dest='mode', help=t('help_mode'))

    # FTP模式
    ftp_parser = subparsers.add_parser('ftp', help=t('help_ftp'))
    ftp_parser.add_argument('--port', type=int, default=21, help=t('help_ftp_port'))
    ftp_parser.add_argument('--ip', default='127.0.0.1', help=t('help_ftp_ip'))
    ftp_parser.add_argument('--use-cpolar', action='store_true', help=t('help_use_cpolar'))
    ftp_parser.add_argument('--pasv-ports', default='', help=t('help_pasv_ports'))
    ftp_parser.add_argument('--retries', type=int, default=5, help=t('help_retries'))
    ftp_parser.add_argument('--force', '-f', action='store_true', help=t('help_force'))

    # 服务端模式
    server_parser = subparsers.add_parser('server', help=t('help_server'))
    server_parser.add_argument('port', type=int, help=t('help_port'))
    server_parser.add_argument('--proto', default='http', help=t('help_proto'))
    server_parser.add_argument('--ip', default='127.0.0.1', help=t('help_ip'))
    server_parser.add_argument('--service', '-s', help=t('help_service'))
    server_parser.add_argument('--retries', type=int, default=5, help=t('help_retries'))
    server_parser.add_argument('--force', '-f', action='store_true', help=t('help_force'))

    # 批量模式
    batch_parser = subparsers.add_parser('batch', help=t('help_batch'))
    batch_parser.add_argument('ports', type=int, nargs='+', help=t('help_ports'))
    batch_parser.add_argument('--proto', default='http', help=t('help_proto'))
    batch_parser.add_argument('--dashboard', action='store_true', help=t('help_dashboard'))
    batch_parser.add_argument('--retries', type=int, default=10, help=t('help_retries'))
    batch_parser.add_argument('--ip', default='127.0.0.1', help=t('help_ip'))

    # 自动模式
    auto_parser = subparsers.add_parser('auto', help=t('help_auto'))
    auto_parser.add_argument('--proto', default='http', help=t('help_proto'))
    auto_parser.add_argument('--dashboard', action='store_true', help=t('help_dashboard'))
    auto_parser.add_argument('--exclude', type=int, nargs='*', default=[], help=t('help_exclude'))
    auto_parser.add_argument('--include-system', action='store_true', help=t('help_include_system'))
    auto_parser.add_argument('--retries', type=int, default=10, help=t('help_retries'))
    auto_parser.add_argument('--ip', default='127.0.0.1', help=t('help_ip'))

    # 客户端模式
    client_parser = subparsers.add_parser('client', help=t('help_client'))
    client_parser.add_argument('tunnel_host', help=t('help_tunnel_host'))
    client_parser.add_argument('--local-port', type=int, required=True, help=t('help_local_port'))
    client_parser.add_argument('--proto', default='tcp', help=t('help_proto'))

    # 仪表盘模式
    dashboard_parser = subparsers.add_parser('dashboard', help=t('help_dashboard'))
    dashboard_parser.add_argument('--port', type=int, default=8000, help=t('help_dash_port'))

    args = parser.parse_args()

    # 全局调试模式
    if args.debug:
        log.enable_debug()
        log.debug("调试模式已启用，所有日志将输出到终端和文件")

    # 特殊命令处理
    if args.backup:
        backup_config()
        return
    if args.restore:
        restore_config()
        return
    if args.list_services:
        print(f"\n支持的服务预设 (v{VERSION}):\n")
        for cat_key, cat_info in SERVICE_CATEGORIES.items():
            print(f"  {cat_info['icon']} {cat_info['name']}:")
            for svc_key in cat_info['services']:
                svc = SERVICE_PRESETS.get(svc_key, {})
                cf = resolve_cf_scheme(svc.get('proto', 'tcp'))
                print(f"      {svc.get('icon', '•')} {svc_key:<12} - {svc.get('desc', '')} (端口: {svc.get('port', '?')}, CF映射: {cf})")
            print()
        print(f"  协议->Cloudflare映射表:")
        for proto, cf in PROTO_TO_CF_SCHEME.items():
            print(f"    {proto:<10} -> {cf}")
        print()
        return

    # 交互模式
    if len(sys.argv) == 1 or args.interactive or args.mode is None:
        ui = UI(args.theme)
        try:
            interactive_mode(ui)
            return
        except KeyboardInterrupt:
            print(f"\n再见！\n")
            return

    # 命令行模式处理
    if args.mode == 'ftp':
        ftp_mode(args.port, args.ip, args.use_cpolar, pasv_ports=args.pasv_ports, max_retries=args.retries)
    elif args.mode == 'server':
        if args.service:
            service = SERVICE_PRESETS.get(args.service)
            if service:
                args.proto = service['proto']
                log.info(f"{service['icon']} {service['name']}: {args.ip}:{args.port}")
            else:
                log.warn(f"未知服务预设: {args.service}，使用协议: {args.proto}")
        server_mode(args.port, args.proto, args.ip, max_retries=args.retries, force=args.force)
    elif args.mode == 'batch':
        batch_mode(args.ports, args.proto, args.dashboard, args.retries, args.ip)
    elif args.mode == 'auto':
        auto_mode(args.proto, args.dashboard, args.exclude, args.include_system, args.retries, args.ip)
    elif args.mode == 'client':
        client_mode(args.tunnel_host, args.local_port, args.proto)
    elif args.mode == 'dashboard':
        dashboard_process = start_dashboard_server(args.port)
        if dashboard_process:
            print(f"\n{t('mode_dashboard')}: http://localhost:{args.port}/dashboard.html")
            print(t('hint_press_ctrlc_stop'))
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print(f"\n{t('hint_closing')}")
                dashboard_process.shutdown()
                dashboard_process.server_close()

if __name__ == '__main__':
    main()
