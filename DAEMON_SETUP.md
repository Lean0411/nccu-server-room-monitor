# NCCU 機房監控系統 - 背景運作設定指南

## 🎯 系統特色

✅ **穩定運行**: 自動錯誤恢復和重啟機制  
✅ **系統服務**: 開機自動啟動  
✅ **資源監控**: 防止記憶體洩漏和 CPU 過載  
✅ **詳細日誌**: 完整的運行記錄  
✅ **健康檢查**: 自動監控系統狀態  
✅ **優雅關閉**: 正確處理系統信號  

## 🚀 快速部署

### 1. 準備環境設定
```bash
# 複製環境變數範例
cp .env.example .env

# 編輯環境設定
nano .env
```

### 2. 安裝系統服務
```bash
# 安裝監控服務
./monitor_control.sh install

# 啟動服務
./monitor_control.sh start

# 檢查狀態
./monitor_control.sh status
```

### 3. 驗證運行
```bash
# 健康檢查
./monitor_control.sh health

# 查看即時日誌
./monitor_control.sh follow
```

## 📋 詳細設定步驟

### 步驟 1: 環境變數設定

編輯 `.env` 檔案，填入正確的設定：

```env
# 郵件設定 (Gmail 範例)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=monitor@nccu.edu.tw
SMTP_PASS=your_app_password

# 警報收件者
ALERT_TO=admin@nccu.edu.tw
```

**Gmail 設定注意事項:**
- 需要啟用「兩步驟驗證」
- 使用「應用程式密碼」而非一般密碼
- 前往：Google 帳戶 → 安全性 → 應用程式密碼

### 步驟 2: 系統服務安裝

```bash
# 1. 安裝服務
./monitor_control.sh install

# 2. 啟動服務
./monitor_control.sh start

# 3. 設定開機自動啟動 (已自動完成)
sudo systemctl enable nccu-monitor
```

### 步驟 3: 驗證安裝

```bash
# 檢查服務狀態
./monitor_control.sh status

# 系統健康檢查
./monitor_control.sh health

# 查看最近日誌
./monitor_control.sh logs
```

## 🛠️ 管理指令

### 基本控制
```bash
./monitor_control.sh start     # 啟動服務
./monitor_control.sh stop      # 停止服務
./monitor_control.sh restart   # 重啟服務
./monitor_control.sh status    # 查看狀態
```

### 日誌管理
```bash
./monitor_control.sh logs      # 查看最近日誌
./monitor_control.sh follow    # 即時監控日誌
```

### 系統維護
```bash
./monitor_control.sh health    # 健康檢查
./monitor_control.sh uninstall # 移除服務
```

## 📊 監控和日誌

### 日誌位置
- **應用程式日誌**: `logs/monitor.log`
- **系統服務日誌**: `sudo journalctl -u nccu-monitor`
- **看門狗日誌**: `logs/watchdog.log`

### 即時監控
```bash
# 方法 1: 使用控制腳本
./monitor_control.sh follow

# 方法 2: 直接查看系統日誌
sudo journalctl -u nccu-monitor -f

# 方法 3: 查看應用程式日誌
tail -f logs/monitor.log
```

## 🔍 健康檢查和看門狗

### 手動健康檢查
```bash
# 完整健康檢查
./monitor_control.sh health

# 看門狗單次檢查
python3 watchdog.py --check-once
```

### 自動看門狗設定
```bash
# 在 crontab 中設定每 5 分鐘檢查一次
crontab -e

# 加入以下行:
*/5 * * * * /usr/bin/python3 /home/pi/monitor/watchdog.py --check-once
```

## ⚙️ 進階設定

### 調整系統參數

編輯 `monitor_daemon.py` 中的參數：

```python
# 監控參數
self.BUFFER_SIZE = 20        # 影像緩衝區大小
self.CAP_INTERVAL = 5        # 擷取間隔(秒)
self.ROI = (100, 80, 200, 150)  # 感興趣區域

# 重啟參數
max_restarts = 10            # 最大重啟次數
```

### 資源限制調整

編輯 `nccu-monitor.service`：

```ini
# 資源限制
MemoryMax=1G        # 最大記憶體
CPUQuota=80%        # CPU 配額
```

## 🔧 故障排除

### 常見問題

**1. 服務啟動失敗**
```bash
# 檢查詳細錯誤
sudo journalctl -u nccu-monitor -n 50

# 檢查權限
ls -la /home/pi/monitor/
```

**2. 攝影機無法使用**
```bash
# 檢查攝影機設備
ls -la /dev/video*

# 檢查攝影機設定
sudo raspi-config
# Interface Options > Camera > Enable
```

**3. GPIO 權限問題**
```bash
# 檢查 GPIO 權限
ls -la /dev/gpiomem

# 確認使用者在 gpio 群組中
groups pi
```

**4. 郵件發送失敗**
```bash
# 測試郵件設定
python3 test_email.py

# 檢查網路連線
ping smtp.gmail.com
```

### 重置系統
```bash
# 停止並移除服務
./monitor_control.sh stop
./monitor_control.sh uninstall

# 清理日誌
rm -rf logs/*

# 重新安裝
./monitor_control.sh install
./monitor_control.sh start
```

## 📈 性能監控

### 系統資源監控
```bash
# 查看服務資源使用
sudo systemctl status nccu-monitor

# 查看程序詳細資訊
ps aux | grep monitor_daemon

# 查看記憶體使用
free -h
```

### 日誌分析
```bash
# 統計警報次數
grep -c "偵測到" logs/monitor.log

# 查看重啟記錄
grep "系統重啟" logs/monitor.log

# 分析錯誤頻率
grep "ERROR" logs/monitor.log | tail -20
```

## 🔄 系統更新

### 更新程式碼
```bash
# 停止服務
./monitor_control.sh stop

# 更新程式碼 (git pull 等)
git pull

# 重新啟動服務
./monitor_control.sh start
```

### 更新服務設定
```bash
# 修改服務檔案後
sudo systemctl daemon-reload
./monitor_control.sh restart
```

## 📞 緊急情況

### 緊急停止
```bash
# 立即停止服務
sudo systemctl stop nccu-monitor

# 或殺死程序
sudo pkill -f monitor_daemon.py
```

### 手動運行 (除錯模式)
```bash
# 停止背景服務
./monitor_control.sh stop

# 手動運行查看詳細輸出
python3 monitor_daemon.py
```

---

**支援聯絡**: Lean0411  
**專案位置**: https://github.com/Lean0411/nccu-server-room-monitor  
**更新日期**: 2025-06-19