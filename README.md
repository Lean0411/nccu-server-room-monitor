# NCCU Server Room Monitor

**政大機房環境監控系統 - 優化版**

## 📋 專案概述

為 NCCU（國立政治大學）大仁樓 1F 機房設計的智能環境監控系統，提供 7×24 小時不間斷的安全監控，確保伺服器設備運行環境的安全性與穩定性。採用最新優化技術，提供更穩定的效能和更智慧的誤報防護機制。

## 🎯 功能特色

### 環境監測
- 🔥 **智慧火災偵測** - 火焰感測器連續 3 次偵測才觸發警報（防誤報）
- 💨 **煙霧偵測** - MQ-2 感測器連續 2 次偵測觸發警報
- 📸 **即時影像監控** - ROI 區域智慧擷取
- ⏰ **冷卻機制** - 5 分鐘內不重複發送同類型警報

### 效能優化
- 🧵 **多執行緒架構** - 非阻塞警報處理
- 💾 **記憶體優化** - 智慧資源管理與自動清理
- 📊 **動態效能監控** - FPS 監控與自適應調節
- 🔄 **自動重啟機制** - 錯誤恢復與系統穩定性

## 🛠️ 硬體需求

### 主控制器
- Raspberry Pi 4B
- MicroSD 卡 (32GB+)
- 電源供應器

### 感測器模組
- **Pi Camera** - 影像監控
- **MQ-2 煙霧感測器** (GPIO 17)
- **火焰感測器** (GPIO 27)
- **DHT22 溫濕度感測器** (GPIO 4)
- **水位感測器** (待確認 GPIO)

### 連接線材
- 杜邦線
- 4.7kΩ 電阻（DHT22 上拉）

## 📁 專案結構

```
nccu-server-room-monitor/
├── monitor_daemon.py          # 主監控程式（優化版）
├── monitor_daemon_backup.py   # 原始版本備份
├── nccu-monitor.service       # systemd 服務設定
├── test_sensitivity.py        # 感測器敏感度測試
├── test_smoke_flame.py        # 煙霧火焰測試
├── test_email.py              # 郵件功能測試
├── test_camera_legacy.py      # 攝影機測試
├── check_all_sensors.py       # 感測器綜合檢查
├── system_status_check.py     # 系統狀態總覽
├── system_demo.py             # 系統演示程式
├── demo_test.py               # 演示測試
├── captures/                  # 影像儲存目錄
├── logs/                      # 日誌儲存目錄
└── .env                       # 環境變數設定（需自行建立）
```

## 🚀 快速開始

### 1. 環境設定
```bash
# 安裝必要套件
sudo apt update
sudo apt install python3-pip
pip3 install -r requirements.txt

# 啟用攝影機
sudo raspi-config
# Interface Options > Camera > Enable
```

### 2. 設定環境變數
建立 `.env` 檔案：
```env
# SMTP 郵件設定
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASS=your_app_password
ALERT_TO=admin@nccu.edu.tw

# 監控參數（可選）
BUFFER_SIZE=20
CAP_INTERVAL=5
ROI=100,80,200,150
OUT_DIR=captures
```

### 3. 測試系統
```bash
# 檢查所有感測器
python3 system_status_check.py

# 測試感測器敏感度
python3 test_sensitivity.py

# 測試個別元件
python3 test_smoke_flame.py
python3 test_email.py
python3 test_camera_legacy.py
```

### 4. 服務化部署
```bash
# 安裝服務
sudo cp nccu-monitor.service /etc/systemd/system/
sudo systemctl enable nccu-monitor
sudo systemctl start nccu-monitor

# 檢查服務狀態
sudo systemctl status nccu-monitor

# 查看即時日誌
sudo journalctl -u nccu-monitor -f
```

## ⚙️ 系統參數

### 預設設定
- **監控間隔**: 5 秒
- **影像緩衝**: 最近 20 張
- **ROI 區域**: (100, 80, 200, 150)
- **解析度**: 640×480
- **火焰閾值**: 連續 3 次偵測
- **煙霧閾值**: 連續 2 次偵測
- **警報冷卻**: 5 分鐘

### 日誌管理
- **日誌大小**: 最大 10MB
- **備份數量**: 保留 5 個
- **檔案清理**: 自動刪除 7 天前檔案

## 📧 智慧警報機制

### 觸發條件
- **火災警報**: 火焰感測器連續 3 次偵測到信號
- **煙霧警報**: 煙霧感測器連續 2 次偵測到信號
- **冷卻機制**: 同類型警報 5 分鐘內不重複發送

### 警報流程
1. 感測器連續偵測達到閾值
2. 立即保存最近 20 張影像
3. 背景執行緒打包 ZIP 檔案
4. 非阻塞發送 Email 警報
5. 本地儲存事件記錄

## 🔧 維護與故障排除

### 常見問題
- **攝影機無法啟動**: 檢查 `raspi-config` 中是否啟用攝影機
- **感測器讀取失敗**: 檢查 GPIO 接線
- **郵件發送失敗**: 確認 `.env` 設定正確
- **頻繁誤報**: 使用 `test_sensitivity.py` 測試並調整閾值
- **記憶體不足**: 系統會自動清理舊檔案和優化記憶體使用

### 診斷工具
```bash
# 系統整體檢查
python3 check_all_sensors.py

# 感測器敏感度測試
python3 test_sensitivity.py

# 服務狀態檢查
sudo systemctl status nccu-monitor

# 查看系統日誌
sudo journalctl -u nccu-monitor --since "1 hour ago"

# 檢查磁碟空間
df -h

# 查看效能監控
tail -f logs/monitor.log | grep "FPS"
```

### 效能優化指標
- **FPS**: 正常應維持在 0.15-0.25 (每 5 秒一次)
- **記憶體**: 系統會自動清理超過 100 張影像
- **磁碟**: 自動刪除 7 天前的檔案
- **日誌**: 自動切割超過 10MB 的日誌檔

## 🤝 貢獻者

- **開發**: Lean0411
- **技術支援**: Claude AI
- **部署環境**: NCCU 機房

## 📄 授權

此專案為 NCCU 內部使用，請遵守相關規範。

## 📊 版本更新記錄

### v2.0 (2025-06-20) - 效能優化版
- ✨ 新增多執行緒非阻塞警報處理
- 🔧 實作智慧感測器閾值機制（火焰 3 次、煙霧 2 次）
- 💾 記憶體優化與自動資源清理
- 📈 動態 FPS 監控與效能調節
- 🗂️ 自動日誌切割與檔案清理
- 🛡️ 增強錯誤處理與重試機制
- ⚙️ 支援環境變數配置

### v1.0 (2025-06-19) - 基礎版本
- 🔥 基本火災與煙霧偵測
- 📸 影像擷取與警報發送
- 📧 Email 通知系統

---

*最後更新: 2025-06-20*  
*專案版本: v2.0 (優化版)*