# NCCU 機房監控系統 - 效能與儲存優化指南

## 🎯 優化總覽

經過效能和儲存空間分析，以下是針對長期運行的關鍵優化項目：

### 📊 **效能優化 (Performance)**
- ✅ 降低影像解析度 320×240 (原 640×480)
- ✅ 增加擷取間隔 10秒 (原 5秒)  
- ✅ 減少緩衝區大小 15張 (原 20張)
- ✅ 降低 JPEG 品質 75% (節省空間)
- ✅ 非同步郵件發送 (避免阻塞)
- ✅ 智能警報冷卻 (防止重複警報)

### 💾 **儲存優化 (Storage)**
- ✅ 自動清理舊檔案 (超過 7天)
- ✅ 容量限制 1GB (自動清理)
- ✅ 日誌輪轉 (避免日誌過大)
- ✅ 圖片壓縮優化
- ✅ 空目錄清理

## 🚀 **部署優化版本**

### 1. 替換成優化版本
```bash
# 停止現有服務
./monitor_control.sh stop

# 備份原版本
cp monitor_daemon.py monitor_daemon_original.py

# 使用優化版本
cp monitor_optimized.py monitor_daemon.py

# 更新環境設定
cp .env.optimized .env
nano .env  # 填入您的 SMTP 設定

# 重新啟動
./monitor_control.sh start
```

### 2. 驗證優化效果
```bash
# 檢查系統狀態
./monitor_control.sh status

# 執行效能分析
python3 performance_analysis.py

# 檢查儲存空間
python3 storage_cleanup.py --info
```

## 📊 **效能分析工具**

### 基本使用
```bash
# 完整效能分析
python3 performance_analysis.py

# 只分析記憶體
python3 performance_analysis.py --memory

# 只分析儲存空間
python3 performance_analysis.py --storage

# 產生優化建議
python3 performance_analysis.py --recommendations
```

### 定期分析設定
```bash
# 加入 crontab 定期分析
crontab -e

# 每小時保存效能統計
0 * * * * /usr/bin/python3 /home/pi/monitor/performance_analysis.py --save

# 每天早上產生效能報告
0 8 * * * /usr/bin/python3 /home/pi/monitor/performance_analysis.py > /home/pi/monitor/logs/daily_report.log
```

## 🧹 **儲存空間管理**

### 手動清理
```bash
# 檢查目前狀況
python3 storage_cleanup.py --info

# 模擬清理（不實際刪除）
python3 storage_cleanup.py --dry-run

# 執行清理（保留 7天，限制 500MB）
python3 storage_cleanup.py --age 7 --size 500

# 只清理舊檔案
python3 storage_cleanup.py --age-only --age 3

# 只清理日誌
python3 storage_cleanup.py --logs-only
```

### 自動清理設定
```bash
# 加入 crontab 自動清理
crontab -e

# 每天凌晨 2點自動清理
0 2 * * * /usr/bin/python3 /home/pi/monitor/storage_cleanup.py --age 7 --size 1000

# 每週日深度清理
0 3 * * 0 /usr/bin/python3 /home/pi/monitor/storage_cleanup.py --age 3 --size 500
```

## ⚙️ **優化參數說明**

### 環境變數調整
```env
# 效能相關
BUFFER_SIZE=15              # 影像緩衝區 (記憶體使用)
CAP_INTERVAL=10             # 擷取間隔 (CPU使用)
IMAGE_QUALITY=75            # 影像品質 (檔案大小)
ALERT_COOLDOWN=300          # 警報間隔 (避免重複)

# 儲存管理
MAX_STORAGE_GB=1.0          # 最大儲存空間
MAX_AGE_DAYS=7              # 檔案保留天數

# 系統資源
MAX_MEMORY_MB=256           # 記憶體限制
MAX_CPU_PERCENT=80          # CPU限制
```

### 針對不同環境的建議設定

**🟢 低負載環境 (測試/開發)**
```env
BUFFER_SIZE=10
CAP_INTERVAL=15
IMAGE_QUALITY=60
MAX_STORAGE_GB=0.5
MAX_AGE_DAYS=3
```

**🟡 標準環境 (一般機房)**
```env
BUFFER_SIZE=15
CAP_INTERVAL=10
IMAGE_QUALITY=75
MAX_STORAGE_GB=1.0
MAX_AGE_DAYS=7
```

**🔴 高負載環境 (關鍵機房)**
```env
BUFFER_SIZE=20
CAP_INTERVAL=8
IMAGE_QUALITY=85
MAX_STORAGE_GB=2.0
MAX_AGE_DAYS=14
```

## 📈 **效能監控指標**

### 關鍵指標
- **FPS**: 應保持在預期值 (1/CAP_INTERVAL)
- **記憶體使用**: 建議 < 200MB
- **CPU 使用**: 建議 < 50%
- **儲存空間**: 監控增長速度

### 警報閾值
- 記憶體使用 > 80% → 減少 BUFFER_SIZE
- CPU 使用 > 80% → 增加 CAP_INTERVAL
- 儲存空間 > 90% → 加強清理頻率
- FPS 異常 → 檢查硬體問題

## 🔧 **故障排除**

### 常見效能問題

**1. 記憶體使用過高**
```bash
# 檢查記憶體洩漏
python3 performance_analysis.py --memory

# 減少緩衝區大小
echo "BUFFER_SIZE=10" >> .env

# 重啟服務
./monitor_control.sh restart
```

**2. 儲存空間不足**
```bash
# 立即清理
python3 storage_cleanup.py --age 1 --size 200

# 調整保留策略
echo "MAX_AGE_DAYS=3" >> .env
echo "MAX_STORAGE_GB=0.5" >> .env
```

**3. CPU 使用率過高**
```bash
# 降低擷取頻率
echo "CAP_INTERVAL=15" >> .env

# 降低影像品質
echo "IMAGE_QUALITY=60" >> .env

# 重啟服務
./monitor_control.sh restart
```

### 系統健康檢查
```bash
# 綜合健康檢查
./monitor_control.sh health

# 效能分析
python3 performance_analysis.py

# 查看系統資源
htop
df -h
free -h
```

## 📱 **監控建議**

### 日常監控任務
```bash
# 每日檢查 (建議加入 cron)
#!/bin/bash
echo "=== $(date) 每日監控報告 ===" >> /home/pi/monitor/logs/daily_check.log
./monitor_control.sh status >> /home/pi/monitor/logs/daily_check.log
python3 performance_analysis.py --recommendations >> /home/pi/monitor/logs/daily_check.log
python3 storage_cleanup.py --info >> /home/pi/monitor/logs/daily_check.log
echo "" >> /home/pi/monitor/logs/daily_check.log
```

### 週期性維護
- **每日**: 檢查服務狀態和基本指標
- **每週**: 執行效能分析和儲存清理  
- **每月**: 檢查硬體狀況和更新系統
- **每季**: 評估參數設定和優化策略

## 🎯 **預期優化效果**

### 效能提升
- 記憶體使用減少 **30-40%**
- CPU 使用減少 **20-30%**
- 磁碟 I/O 減少 **40-50%**

### 儲存節省
- 檔案大小減少 **25-35%**
- 自動清理節省 **60-80%** 空間
- 日誌管理節省 **90%** 空間

### 穩定性改善
- 減少記憶體洩漏風險
- 避免磁碟空間耗盡
- 降低系統負載

---

**💡 建議**: 先在測試環境驗證優化效果，確認無問題後再部署到生產環境。