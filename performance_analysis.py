#!/usr/bin/env python3
"""
NCCU 機房監控系統 - 效能分析工具
分析系統資源使用和效能瓶頸
"""

import os
import time
import psutil
import logging
from datetime import datetime, timedelta
from pathlib import Path
import json

class PerformanceAnalyzer:
    """效能分析器"""
    
    def __init__(self):
        self.log_dir = Path("logs")
        self.log_dir.mkdir(exist_ok=True)
        self.report_file = self.log_dir / "performance_report.json"
        self.baseline_memory = None
        self.baseline_cpu = None
        
    def get_current_stats(self):
        """取得當前系統統計"""
        try:
            # 取得程序資訊
            monitor_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'memory_info', 'cpu_percent']):
                if 'monitor' in proc.info['name'].lower():
                    monitor_processes.append({
                        'pid': proc.info['pid'],
                        'name': proc.info['name'],
                        'memory_mb': proc.info['memory_info'].rss / 1024 / 1024,
                        'cpu_percent': proc.info['cpu_percent']
                    })
            
            # 系統整體資源
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            stats = {
                'timestamp': datetime.now().isoformat(),
                'system': {
                    'cpu_percent': psutil.cpu_percent(interval=1),
                    'memory_percent': memory.percent,
                    'memory_available_mb': memory.available / 1024 / 1024,
                    'disk_free_gb': disk.free / 1024 / 1024 / 1024,
                    'disk_used_percent': (disk.used / disk.total) * 100,
                    'load_average': os.getloadavg()[0] if hasattr(os, 'getloadavg') else 0
                },
                'monitor_processes': monitor_processes,
                'captures_dir_size': self.get_captures_size()
            }
            
            return stats
            
        except Exception as e:
            logging.error(f"取得系統統計失敗: {e}")
            return None
    
    def get_captures_size(self):
        """取得 captures 目錄大小"""
        try:
            captures_dir = Path("captures")
            if not captures_dir.exists():
                return 0
                
            total_size = 0
            file_count = 0
            for file_path in captures_dir.rglob('*'):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
                    file_count += 1
            
            return {
                'size_mb': total_size / 1024 / 1024,
                'file_count': file_count
            }
        except Exception:
            return {'size_mb': 0, 'file_count': 0}
    
    def analyze_memory_usage(self):
        """分析記憶體使用情況"""
        print("📊 記憶體使用分析")
        print("=" * 50)
        
        try:
            # 系統記憶體
            memory = psutil.virtual_memory()
            print(f"系統記憶體:")
            print(f"  總量: {memory.total / 1024 / 1024 / 1024:.1f} GB")
            print(f"  可用: {memory.available / 1024 / 1024:.0f} MB ({100 - memory.percent:.1f}%)")
            print(f"  使用: {memory.used / 1024 / 1024:.0f} MB ({memory.percent:.1f}%)")
            
            # 監控程序記憶體
            print(f"\n監控程序記憶體:")
            for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
                if 'monitor' in proc.info['name'].lower():
                    memory_mb = proc.info['memory_info'].rss / 1024 / 1024
                    print(f"  {proc.info['name']} (PID: {proc.info['pid']}): {memory_mb:.1f} MB")
            
        except Exception as e:
            print(f"記憶體分析失敗: {e}")
    
    def analyze_storage_usage(self):
        """分析儲存使用情況"""
        print("\n💾 儲存空間分析")
        print("=" * 50)
        
        try:
            # 系統磁碟空間
            disk = psutil.disk_usage('/')
            print(f"系統磁碟:")
            print(f"  總量: {disk.total / 1024 / 1024 / 1024:.1f} GB")
            print(f"  可用: {disk.free / 1024 / 1024 / 1024:.1f} GB")
            print(f"  使用: {disk.used / 1024 / 1024 / 1024:.1f} GB ({(disk.used/disk.total)*100:.1f}%)")
            
            # Captures 目錄分析
            captures_info = self.get_captures_size()
            print(f"\nCaptures 目錄:")
            print(f"  大小: {captures_info['size_mb']:.1f} MB")
            print(f"  檔案數: {captures_info['file_count']}")
            
            if captures_info['file_count'] > 0:
                avg_size = captures_info['size_mb'] / captures_info['file_count']
                print(f"  平均檔案大小: {avg_size:.2f} MB")
            
            # 日誌檔案分析
            log_size = 0
            log_count = 0
            log_dir = Path("logs")
            if log_dir.exists():
                for log_file in log_dir.glob("*.log*"):
                    log_size += log_file.stat().st_size
                    log_count += 1
            
            print(f"\n日誌檔案:")
            print(f"  大小: {log_size / 1024 / 1024:.1f} MB")
            print(f"  檔案數: {log_count}")
            
        except Exception as e:
            print(f"儲存分析失敗: {e}")
    
    def analyze_performance_trends(self):
        """分析效能趨勢"""
        print("\n📈 效能趨勢分析")
        print("=" * 50)
        
        try:
            if not self.report_file.exists():
                print("沒有歷史效能資料")
                return
            
            with open(self.report_file, 'r') as f:
                reports = [json.loads(line) for line in f.readlines()[-10:]]  # 最近 10 筆記錄
            
            if not reports:
                print("沒有有效的效能資料")
                return
            
            # CPU 趨勢
            cpu_values = [r['system']['cpu_percent'] for r in reports]
            print(f"CPU 使用率趨勢:")
            print(f"  平均: {sum(cpu_values) / len(cpu_values):.1f}%")
            print(f"  最高: {max(cpu_values):.1f}%")
            print(f"  最低: {min(cpu_values):.1f}%")
            
            # 記憶體趨勢
            memory_values = [r['system']['memory_percent'] for r in reports]
            print(f"\n記憶體使用率趨勢:")
            print(f"  平均: {sum(memory_values) / len(memory_values):.1f}%")
            print(f"  最高: {max(memory_values):.1f}%")
            print(f"  最低: {min(memory_values):.1f}%")
            
            # 儲存空間趨勢
            if 'captures_dir_size' in reports[-1]:
                storage_values = [r.get('captures_dir_size', {}).get('size_mb', 0) for r in reports]
                storage_growth = storage_values[-1] - storage_values[0] if len(storage_values) > 1 else 0
                print(f"\nCaptures 儲存空間:")
                print(f"  當前: {storage_values[-1]:.1f} MB")
                print(f"  成長: {storage_growth:.1f} MB")
                
                if len(storage_values) > 1:
                    avg_growth = storage_growth / (len(storage_values) - 1)
                    print(f"  平均成長: {avg_growth:.2f} MB/記錄")
            
        except Exception as e:
            print(f"趨勢分析失敗: {e}")
    
    def generate_optimization_recommendations(self):
        """產生優化建議"""
        print("\n💡 優化建議")
        print("=" * 50)
        
        try:
            stats = self.get_current_stats()
            if not stats:
                print("無法取得系統資訊")
                return
            
            recommendations = []
            
            # CPU 使用率建議
            if stats['system']['cpu_percent'] > 80:
                recommendations.append("🔴 CPU 使用率過高，建議增加 CAP_INTERVAL 或降低影像品質")
            elif stats['system']['cpu_percent'] > 60:
                recommendations.append("🟡 CPU 使用率偏高，考慮優化影像處理參數")
            
            # 記憶體使用建議
            if stats['system']['memory_percent'] > 80:
                recommendations.append("🔴 記憶體使用率過高，建議減少 BUFFER_SIZE")
            elif stats['system']['memory_percent'] > 60:
                recommendations.append("🟡 記憶體使用率偏高，監控是否有記憶體洩漏")
            
            # 儲存空間建議
            if stats['system']['disk_used_percent'] > 90:
                recommendations.append("🔴 磁碟空間不足，需要立即清理")
            elif stats['system']['disk_used_percent'] > 80:
                recommendations.append("🟡 磁碟空間偏少，建議啟用自動清理")
            
            # Captures 目錄大小建議
            captures_size = stats['captures_dir_size']['size_mb']
            if captures_size > 500:
                recommendations.append("🔴 Captures 目錄過大，建議清理舊檔案")
            elif captures_size > 200:
                recommendations.append("🟡 Captures 目錄較大，建議設定自動清理")
            
            # 監控程序建議
            for proc in stats['monitor_processes']:
                if proc['memory_mb'] > 200:
                    recommendations.append(f"🔴 程序 {proc['name']} 記憶體使用過高: {proc['memory_mb']:.1f} MB")
                elif proc['memory_mb'] > 100:
                    recommendations.append(f"🟡 程序 {proc['name']} 記憶體使用偏高: {proc['memory_mb']:.1f} MB")
            
            if recommendations:
                for rec in recommendations:
                    print(f"  {rec}")
            else:
                print("  ✅ 系統運行狀況良好，無需特別優化")
            
            # 具體參數建議
            print(f"\n🎯 建議的環境變數設定:")
            
            if stats['system']['memory_percent'] > 70:
                print(f"  BUFFER_SIZE=10          # 減少記憶體使用")
            
            if stats['system']['cpu_percent'] > 70:
                print(f"  CAP_INTERVAL=15         # 降低 CPU 負載")
                print(f"  IMAGE_QUALITY=60        # 降低影像品質")
            
            if captures_size > 300:
                print(f"  MAX_STORAGE_GB=0.5      # 限制儲存空間")
                print(f"  MAX_AGE_DAYS=3          # 縮短保留時間")
            
        except Exception as e:
            print(f"優化建議產生失敗: {e}")
    
    def save_performance_report(self):
        """保存效能報告"""
        try:
            stats = self.get_current_stats()
            if stats:
                with open(self.report_file, 'a') as f:
                    f.write(json.dumps(stats) + '\n')
                print(f"效能報告已保存到 {self.report_file}")
        except Exception as e:
            print(f"保存效能報告失敗: {e}")
    
    def run_full_analysis(self):
        """執行完整分析"""
        print("🔍 NCCU 機房監控系統 - 效能分析報告")
        print("=" * 60)
        print(f"分析時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        self.analyze_memory_usage()
        self.analyze_storage_usage()
        self.analyze_performance_trends()
        self.generate_optimization_recommendations()
        self.save_performance_report()
        
        print("\n" + "=" * 60)
        print("分析完成！建議定期執行此分析以監控系統效能。")

def main():
    """主程式"""
    import argparse
    
    parser = argparse.ArgumentParser(description="NCCU 監控系統效能分析")
    parser.add_argument("--memory", action="store_true", help="只分析記憶體使用")
    parser.add_argument("--storage", action="store_true", help="只分析儲存空間")
    parser.add_argument("--trends", action="store_true", help="只分析效能趨勢")
    parser.add_argument("--recommendations", action="store_true", help="只產生優化建議")
    parser.add_argument("--save", action="store_true", help="只保存當前統計")
    
    args = parser.parse_args()
    
    analyzer = PerformanceAnalyzer()
    
    if args.memory:
        analyzer.analyze_memory_usage()
    elif args.storage:
        analyzer.analyze_storage_usage()
    elif args.trends:
        analyzer.analyze_performance_trends()
    elif args.recommendations:
        analyzer.generate_optimization_recommendations()
    elif args.save:
        analyzer.save_performance_report()
    else:
        analyzer.run_full_analysis()

if __name__ == "__main__":
    main()