#!/bin/bash
# NCCU 機房監控系統 - 控制腳本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="nccu-monitor"
SERVICE_FILE="nccu-monitor.service"
LOG_DIR="$SCRIPT_DIR/logs"

# 建立日誌目錄
mkdir -p "$LOG_DIR"

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_root() {
    if [[ $EUID -eq 0 ]]; then
        print_error "請不要使用 root 權限執行此腳本"
        exit 1
    fi
}

install_service() {
    print_status "安裝監控服務..."
    
    # 複製服務檔案
    sudo cp "$SCRIPT_DIR/$SERVICE_FILE" "/etc/systemd/system/"
    
    # 重新載入 systemd
    sudo systemctl daemon-reload
    
    # 啟用服務
    sudo systemctl enable "$SERVICE_NAME"
    
    print_success "監控服務安裝完成"
    print_status "使用 'sudo systemctl start $SERVICE_NAME' 啟動服務"
}

uninstall_service() {
    print_status "移除監控服務..."
    
    # 停止並禁用服務
    sudo systemctl stop "$SERVICE_NAME" 2>/dev/null
    sudo systemctl disable "$SERVICE_NAME" 2>/dev/null
    
    # 移除服務檔案
    sudo rm -f "/etc/systemd/system/$SERVICE_FILE"
    
    # 重新載入 systemd
    sudo systemctl daemon-reload
    
    print_success "監控服務已移除"
}

start_service() {
    print_status "啟動監控服務..."
    sudo systemctl start "$SERVICE_NAME"
    
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        print_success "監控服務啟動成功"
    else
        print_error "監控服務啟動失敗"
        exit 1
    fi
}

stop_service() {
    print_status "停止監控服務..."
    sudo systemctl stop "$SERVICE_NAME"
    print_success "監控服務已停止"
}

restart_service() {
    print_status "重啟監控服務..."
    sudo systemctl restart "$SERVICE_NAME"
    
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        print_success "監控服務重啟成功"
    else
        print_error "監控服務重啟失敗"
        exit 1
    fi
}

status_service() {
    echo "==================== 服務狀態 ===================="
    sudo systemctl status "$SERVICE_NAME" --no-pager
    
    echo -e "\n==================== 系統資源 ===================="
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        PID=$(sudo systemctl show "$SERVICE_NAME" --property=MainPID --value)
        if [ "$PID" != "0" ]; then
            echo "PID: $PID"
            echo "記憶體使用:"
            ps -p "$PID" -o pid,ppid,cmd,%mem,%cpu --no-headers
        fi
    else
        echo "服務未運行"
    fi
}

view_logs() {
    echo "==================== 監控日誌 ===================="
    
    if [ -f "$LOG_DIR/monitor.log" ]; then
        echo "最近的監控日誌:"
        tail -n 20 "$LOG_DIR/monitor.log"
    fi
    
    echo -e "\n==================== 系統日誌 ===================="
    echo "最近的系統日誌:"
    sudo journalctl -u "$SERVICE_NAME" -n 20 --no-pager
}

follow_logs() {
    print_status "即時監控日誌 (按 Ctrl+C 結束)"
    echo "==================== 即時日誌 ===================="
    
    # 同時顯示檔案日誌和系統日誌
    if [ -f "$LOG_DIR/monitor.log" ]; then
        tail -f "$LOG_DIR/monitor.log" &
        TAIL_PID=$!
    fi
    
    sudo journalctl -u "$SERVICE_NAME" -f --no-pager &
    JOURNAL_PID=$!
    
    # 等待中斷信號
    trap "kill $TAIL_PID $JOURNAL_PID 2>/dev/null; exit 0" INT
    wait
}

health_check() {
    echo "==================== 健康檢查 ===================="
    
    # 檢查服務狀態
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        print_success "服務運行正常"
        SERVICE_OK=true
    else
        print_error "服務未運行"
        SERVICE_OK=false
    fi
    
    # 檢查 GPIO 權限
    if [ -r "/dev/gpiomem" ]; then
        print_success "GPIO 權限正常"
    else
        print_warning "GPIO 權限可能有問題"
    fi
    
    # 檢查攝影機
    if [ -e "/dev/video0" ]; then
        print_success "攝影機設備存在"
    else
        print_warning "找不到攝影機設備"
    fi
    
    # 檢查 Python 套件
    python3 -c "
import sys
packages = ['picamera', 'PIL', 'board', 'digitalio', 'dotenv', 'numpy']
missing = []
for pkg in packages:
    try:
        __import__(pkg)
    except ImportError:
        missing.append(pkg)

if missing:
    print('缺少套件:', ', '.join(missing))
    sys.exit(1)
else:
    print('Python 套件檢查通過')
" && print_success "Python 環境正常" || print_error "Python 環境有問題"
    
    # 檢查環境變數檔案
    if [ -f "$SCRIPT_DIR/.env" ]; then
        print_success "環境設定檔存在"
    else
        print_warning "找不到 .env 設定檔"
    fi
    
    # 檢查日誌檔案
    if [ -f "$LOG_DIR/monitor.log" ]; then
        LOG_SIZE=$(stat -f%z "$LOG_DIR/monitor.log" 2>/dev/null || stat -c%s "$LOG_DIR/monitor.log" 2>/dev/null)
        if [ "$LOG_SIZE" -gt 0 ]; then
            print_success "日誌檔案正常 (${LOG_SIZE} bytes)"
        else
            print_warning "日誌檔案為空"
        fi
    else
        print_warning "找不到日誌檔案"
    fi
}

show_usage() {
    echo "NCCU 機房監控系統 - 控制腳本"
    echo "================================"
    echo "用法: $0 [command]"
    echo ""
    echo "指令:"
    echo "  install     安裝為系統服務"
    echo "  uninstall   移除系統服務"
    echo "  start       啟動監控服務"
    echo "  stop        停止監控服務"
    echo "  restart     重啟監控服務"
    echo "  status      顯示服務狀態"
    echo "  logs        顯示最近日誌"
    echo "  follow      即時顯示日誌"
    echo "  health      健康檢查"
    echo "  help        顯示此說明"
    echo ""
    echo "範例:"
    echo "  $0 install && $0 start    # 安裝並啟動服務"
    echo "  $0 logs                   # 查看日誌"
    echo "  $0 health                 # 系統檢查"
}

# 主程式
case "$1" in
    install)
        check_root
        install_service
        ;;
    uninstall)
        check_root
        uninstall_service
        ;;
    start)
        start_service
        ;;
    stop)
        stop_service
        ;;
    restart)
        restart_service
        ;;
    status)
        status_service
        ;;
    logs)
        view_logs
        ;;
    follow)
        follow_logs
        ;;
    health)
        health_check
        ;;
    help|--help|-h)
        show_usage
        ;;
    *)
        show_usage
        exit 1
        ;;
esac