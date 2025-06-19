# NCCU Server Room Monitor

**政大機房環境監控系統**

## 📋 專案概述

為 NCCU（國立政治大學）機房設計的智能環境監控系統，提供 7×24 小時不間斷的安全監控，確保伺服器設備運行環境的安全性與穩定性。

## 🎯 功能特色

### 環境監測
- 🔥 **火災偵測** - 火焰感測器即時偵測
- 💨 **煙霧偵測** - MQ-2 感測器早期預警
- 🌡️ **溫度監控** - 防止設備過熱
- 💧 **濕度監控** - 防止結露損壞設備
- 💧 **水位偵測** - 防止漏水事故

### 記錄與警報
- 📸 **即時影像擷取** - 事件發生時自動拍照
- 💾 **本地儲存** - 自動保存監控記錄
- 📧 **緊急警報** - Email 即時通知管理員
- 📊 **狀態監控** - 系統健康度檢查

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
monitor/
├── monitor_with_email.py      # 主監控程式
├── test_smoke_flame.py        # 煙霧火焰測試
├── test_email.py              # 郵件功能測試
├── test_camera_legacy.py      # 攝影機測試
├── check_all_sensors.py       # 感測器綜合檢查
├── system_status_check.py     # 系統狀態總覽
├── test_all_gpio.py           # GPIO 腳位檢測
├── test_water_sensor.py       # 水位感測器測試
├── test_water_pulldown.py     # 水位感測器替代測試
├── captures/                  # 影像儲存目錄
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
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASS=your_app_password
ALERT_TO=admin@nccu.edu.tw
```

### 3. 測試系統
```bash
# 檢查所有感測器
python3 system_status_check.py

# 測試個別元件
python3 test_smoke_flame.py
python3 test_email.py
python3 test_camera_legacy.py
```

### 4. 啟動監控
```bash
# 開始監控
python3 monitor_with_email.py

# 背景執行
nohup python3 monitor_with_email.py &
```

## ⚙️ 系統參數

- **監控間隔**: 5 秒
- **影像緩衝**: 最近 20 張
- **ROI 區域**: (100, 80, 200, 150)
- **解析度**: 640×480

## 📧 警報機制

系統偵測到異常時會：
1. 立即保存最近 20 張影像
2. 打包成 ZIP 檔案
3. 發送 Email 警報給管理員
4. 本地儲存事件記錄

## 🔧 維護與故障排除

### 常見問題
- **攝影機無法啟動**: 檢查 `raspi-config` 中是否啟用攝影機
- **感測器讀取失敗**: 檢查 GPIO 接線
- **郵件發送失敗**: 確認 `.env` 設定正確

### 診斷工具
```bash
# 系統整體檢查
python3 check_all_sensors.py

# GPIO 腳位測試
python3 test_all_gpio.py

# 網路與郵件測試
python3 test_email.py
```

## 🤝 貢獻者

- **開發**: Lean0411
- **技術支援**: Claude AI
- **部署環境**: NCCU 機房

## 📄 授權

此專案為 NCCU 內部使用，請遵守相關規範。

---

*最後更新: 2025-06-19*  
*專案版本: v1.0*