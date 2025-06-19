#!/usr/bin/env python3
"""
NCCU 機房監控系統 - 儲存空間清理工具
手動和自動清理舊檔案，管理儲存空間
"""

import os
import time
import shutil
import logging
from datetime import datetime, timedelta
from pathlib import Path
import argparse

class StorageCleanup:
    """儲存空間清理工具"""
    
    def __init__(self, base_dir="captures", log_dir="logs"):
        self.base_dir = Path(base_dir)
        self.log_dir = Path(log_dir)
        self.base_dir.mkdir(exist_ok=True)
        self.log_dir.mkdir(exist_ok=True)
        
        # 設定日誌
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - [CLEANUP] - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_dir / "cleanup.log"),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def get_directory_info(self, directory):
        """取得目錄資訊"""
        try:
            directory = Path(directory)
            if not directory.exists():
                return None
            
            total_size = 0
            file_count = 0
            oldest_file = None
            newest_file = None
            
            for file_path in directory.rglob('*'):
                if file_path.is_file():
                    stat = file_path.stat()
                    total_size += stat.st_size
                    file_count += 1
                    
                    if oldest_file is None or stat.st_mtime < oldest_file[1]:
                        oldest_file = (file_path, stat.st_mtime)
                    
                    if newest_file is None or stat.st_mtime > newest_file[1]:
                        newest_file = (file_path, stat.st_mtime)
            
            return {
                'total_size_mb': total_size / 1024 / 1024,
                'file_count': file_count,
                'oldest_file': oldest_file[0] if oldest_file else None,
                'oldest_time': datetime.fromtimestamp(oldest_file[1]) if oldest_file else None,
                'newest_file': newest_file[0] if newest_file else None,
                'newest_time': datetime.fromtimestamp(newest_file[1]) if newest_file else None
            }
            
        except Exception as e:
            self.logger.error(f"取得目錄資訊失敗: {e}")
            return None
    
    def cleanup_by_age(self, max_age_days, dry_run=False):
        """按年齡清理檔案"""
        cutoff_time = time.time() - (max_age_days * 24 * 3600)
        cutoff_date = datetime.fromtimestamp(cutoff_time)
        
        self.logger.info(f"清理 {max_age_days} 天前的檔案 (早於 {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')})")
        
        deleted_files = []
        deleted_size = 0
        
        try:
            for file_path in self.base_dir.rglob('*'):
                if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                    file_size = file_path.stat().st_size
                    file_age = datetime.fromtimestamp(file_path.stat().st_mtime)
                    
                    if dry_run:
                        self.logger.info(f"[模擬] 將刪除: {file_path} ({file_size/1024/1024:.1f} MB, {file_age})")
                    else:
                        try:
                            file_path.unlink()
                            deleted_files.append(str(file_path))
                            deleted_size += file_size
                            self.logger.info(f"已刪除: {file_path} ({file_size/1024/1024:.1f} MB)")
                        except Exception as e:
                            self.logger.error(f"刪除檔案失敗 {file_path}: {e}")
            
            if not dry_run and deleted_files:
                self.logger.info(f"年齡清理完成: 刪除 {len(deleted_files)} 個檔案, 釋放 {deleted_size/1024/1024:.1f} MB")
            elif dry_run:
                self.logger.info(f"模擬清理: 將刪除 {len(deleted_files)} 個檔案, 將釋放 {deleted_size/1024/1024:.1f} MB")
            else:
                self.logger.info("沒有需要清理的舊檔案")
                
            return deleted_files, deleted_size
            
        except Exception as e:
            self.logger.error(f"年齡清理失敗: {e}")
            return [], 0
    
    def cleanup_by_size(self, max_size_mb, keep_recent_hours=24, dry_run=False):
        """按大小清理檔案（保留最近的檔案）"""
        max_size_bytes = max_size_mb * 1024 * 1024
        keep_recent_time = time.time() - (keep_recent_hours * 3600)
        
        self.logger.info(f"清理超過 {max_size_mb} MB 的檔案 (保留最近 {keep_recent_hours} 小時)")
        
        # 取得所有檔案並按時間排序
        files_info = []
        total_size = 0
        
        for file_path in self.base_dir.rglob('*'):
            if file_path.is_file():
                stat = file_path.stat()
                files_info.append({
                    'path': file_path,
                    'size': stat.st_size,
                    'mtime': stat.st_mtime,
                    'is_recent': stat.st_mtime > keep_recent_time
                })
                total_size += stat.st_size
        
        if total_size <= max_size_bytes:
            self.logger.info(f"目前大小 {total_size/1024/1024:.1f} MB 未超過限制")
            return [], 0
        
        # 按時間排序（舊的先刪除），但保護最近的檔案
        files_info.sort(key=lambda x: x['mtime'])
        
        deleted_files = []
        deleted_size = 0
        current_size = total_size
        
        for file_info in files_info:
            if current_size <= max_size_bytes:
                break
            
            # 保護最近的檔案
            if file_info['is_recent']:
                self.logger.debug(f"保護最近檔案: {file_info['path']}")
                continue
            
            if dry_run:
                self.logger.info(f"[模擬] 將刪除: {file_info['path']} ({file_info['size']/1024/1024:.1f} MB)")
            else:
                try:
                    file_info['path'].unlink()
                    deleted_files.append(str(file_info['path']))
                    deleted_size += file_info['size']
                    current_size -= file_info['size']
                    self.logger.info(f"已刪除: {file_info['path']} ({file_info['size']/1024/1024:.1f} MB)")
                except Exception as e:
                    self.logger.error(f"刪除檔案失敗 {file_info['path']}: {e}")
        
        if not dry_run and deleted_files:
            self.logger.info(f"大小清理完成: 刪除 {len(deleted_files)} 個檔案, 釋放 {deleted_size/1024/1024:.1f} MB")
            self.logger.info(f"目前大小: {current_size/1024/1024:.1f} MB")
        elif dry_run:
            target_size = current_size - deleted_size
            self.logger.info(f"模擬清理: 將刪除 {len(deleted_files)} 個檔案, 目標大小 {target_size/1024/1024:.1f} MB")
        
        return deleted_files, deleted_size
    
    def cleanup_empty_directories(self, dry_run=False):
        """清理空目錄"""
        deleted_dirs = []
        
        try:
            # 從最深層開始清理
            for dir_path in sorted(self.base_dir.rglob('*'), key=lambda p: len(p.parts), reverse=True):
                if dir_path.is_dir() and dir_path != self.base_dir:
                    try:
                        # 檢查是否為空目錄
                        if not any(dir_path.iterdir()):
                            if dry_run:
                                self.logger.info(f"[模擬] 將刪除空目錄: {dir_path}")
                            else:
                                dir_path.rmdir()
                                deleted_dirs.append(str(dir_path))
                                self.logger.info(f"已刪除空目錄: {dir_path}")
                    except Exception as e:
                        self.logger.debug(f"無法刪除目錄 {dir_path}: {e}")
            
            if not dry_run and deleted_dirs:
                self.logger.info(f"清理空目錄完成: 刪除 {len(deleted_dirs)} 個目錄")
            
            return deleted_dirs
            
        except Exception as e:
            self.logger.error(f"清理空目錄失敗: {e}")
            return []
    
    def cleanup_log_files(self, max_log_age_days=14, max_log_size_mb=50, dry_run=False):
        """清理日誌檔案"""
        self.logger.info(f"清理日誌檔案: 超過 {max_log_age_days} 天或總大小超過 {max_log_size_mb} MB")
        
        deleted_files = []
        deleted_size = 0
        
        try:
            # 按年齡清理
            cutoff_time = time.time() - (max_log_age_days * 24 * 3600)
            log_files = []
            total_log_size = 0
            
            for log_file in self.log_dir.glob('*.log*'):
                if log_file.is_file():
                    stat = log_file.stat()
                    log_files.append({
                        'path': log_file,
                        'size': stat.st_size,
                        'mtime': stat.st_mtime
                    })
                    total_log_size += stat.st_size
                    
                    # 清理過期日誌
                    if stat.st_mtime < cutoff_time:
                        if dry_run:
                            self.logger.info(f"[模擬] 將刪除過期日誌: {log_file}")
                        else:
                            log_file.unlink()
                            deleted_files.append(str(log_file))
                            deleted_size += stat.st_size
                            self.logger.info(f"已刪除過期日誌: {log_file}")
            
            # 按大小清理（保留最新的日誌）
            max_log_size_bytes = max_log_size_mb * 1024 * 1024
            if total_log_size > max_log_size_bytes:
                # 重新掃描（排除已刪除的檔案）
                current_log_files = []
                current_log_size = 0
                
                for log_file in self.log_dir.glob('*.log*'):
                    if log_file.is_file():
                        stat = log_file.stat()
                        current_log_files.append({
                            'path': log_file,
                            'size': stat.st_size,
                            'mtime': stat.st_mtime
                        })
                        current_log_size += stat.st_size
                
                # 按時間排序（舊的先刪除）
                current_log_files.sort(key=lambda x: x['mtime'])
                
                for log_info in current_log_files:
                    if current_log_size <= max_log_size_bytes:
                        break
                    
                    # 保留最新的主日誌檔案
                    if log_info['path'].name == 'monitor.log':
                        continue
                    
                    if dry_run:
                        self.logger.info(f"[模擬] 將刪除日誌: {log_info['path']} ({log_info['size']/1024/1024:.1f} MB)")
                    else:
                        try:
                            log_info['path'].unlink()
                            deleted_files.append(str(log_info['path']))
                            deleted_size += log_info['size']
                            current_log_size -= log_info['size']
                            self.logger.info(f"已刪除日誌: {log_info['path']}")
                        except Exception as e:
                            self.logger.error(f"刪除日誌失敗 {log_info['path']}: {e}")
            
            if not dry_run and deleted_files:
                self.logger.info(f"日誌清理完成: 刪除 {len(deleted_files)} 個檔案, 釋放 {deleted_size/1024/1024:.1f} MB")
            
            return deleted_files, deleted_size
            
        except Exception as e:
            self.logger.error(f"日誌清理失敗: {e}")
            return [], 0
    
    def run_comprehensive_cleanup(self, max_age_days=7, max_size_mb=500, max_log_age_days=14, dry_run=False):
        """執行綜合清理"""
        self.logger.info("=" * 60)
        self.logger.info("開始綜合儲存空間清理")
        self.logger.info("=" * 60)
        
        if dry_run:
            self.logger.info("🔍 模擬模式 - 不會實際刪除檔案")
        
        # 清理前狀態
        before_info = self.get_directory_info(self.base_dir)
        if before_info:
            self.logger.info(f"清理前狀態: {before_info['file_count']} 個檔案, {before_info['total_size_mb']:.1f} MB")
        
        total_deleted_files = 0
        total_freed_mb = 0
        
        # 1. 按年齡清理
        self.logger.info("\n1️⃣ 按年齡清理檔案...")
        age_files, age_size = self.cleanup_by_age(max_age_days, dry_run)
        total_deleted_files += len(age_files)
        total_freed_mb += age_size / 1024 / 1024
        
        # 2. 按大小清理
        self.logger.info("\n2️⃣ 按大小清理檔案...")
        size_files, size_size = self.cleanup_by_size(max_size_mb, dry_run=dry_run)
        total_deleted_files += len(size_files)
        total_freed_mb += size_size / 1024 / 1024
        
        # 3. 清理空目錄
        self.logger.info("\n3️⃣ 清理空目錄...")
        empty_dirs = self.cleanup_empty_directories(dry_run)
        
        # 4. 清理日誌檔案
        self.logger.info("\n4️⃣ 清理日誌檔案...")
        log_files, log_size = self.cleanup_log_files(max_log_age_days, dry_run=dry_run)
        total_freed_mb += log_size / 1024 / 1024
        
        # 清理後狀態
        after_info = self.get_directory_info(self.base_dir)
        
        self.logger.info("\n" + "=" * 60)
        self.logger.info("清理摘要")
        self.logger.info("=" * 60)
        
        if not dry_run:
            self.logger.info(f"✅ 刪除檔案: {total_deleted_files} 個")
            self.logger.info(f"✅ 釋放空間: {total_freed_mb:.1f} MB")
            self.logger.info(f"✅ 刪除空目錄: {len(empty_dirs)} 個")
            
            if before_info and after_info:
                size_reduction = before_info['total_size_mb'] - after_info['total_size_mb']
                self.logger.info(f"📊 空間變化: {before_info['total_size_mb']:.1f} MB → {after_info['total_size_mb']:.1f} MB")
                self.logger.info(f"📊 實際釋放: {size_reduction:.1f} MB")
        else:
            self.logger.info(f"🔍 模擬結果: 將刪除 {total_deleted_files} 個檔案")
            self.logger.info(f"🔍 模擬結果: 將釋放 {total_freed_mb:.1f} MB")
        
        return {
            'deleted_files': total_deleted_files,
            'freed_mb': total_freed_mb,
            'deleted_dirs': len(empty_dirs)
        }

def main():
    """主程式"""
    parser = argparse.ArgumentParser(description="NCCU 監控系統儲存空間清理工具")
    
    parser.add_argument("--age", type=int, default=7, help="清理 N 天前的檔案 (預設: 7)")
    parser.add_argument("--size", type=int, default=500, help="保持總大小在 N MB 以下 (預設: 500)")
    parser.add_argument("--log-age", type=int, default=14, help="清理 N 天前的日誌 (預設: 14)")
    parser.add_argument("--dry-run", action="store_true", help="模擬模式，不實際刪除檔案")
    parser.add_argument("--info", action="store_true", help="只顯示目錄資訊")
    parser.add_argument("--age-only", action="store_true", help="只按年齡清理")
    parser.add_argument("--size-only", action="store_true", help="只按大小清理")
    parser.add_argument("--logs-only", action="store_true", help="只清理日誌")
    
    args = parser.parse_args()
    
    cleanup = StorageCleanup()
    
    if args.info:
        print("📊 目錄資訊")
        print("=" * 40)
        
        # Captures 目錄
        captures_info = cleanup.get_directory_info("captures")
        if captures_info:
            print(f"Captures 目錄:")
            print(f"  檔案數: {captures_info['file_count']}")
            print(f"  總大小: {captures_info['total_size_mb']:.1f} MB")
            if captures_info['oldest_time']:
                print(f"  最舊檔案: {captures_info['oldest_time'].strftime('%Y-%m-%d %H:%M:%S')}")
            if captures_info['newest_time']:
                print(f"  最新檔案: {captures_info['newest_time'].strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 日誌目錄
        logs_info = cleanup.get_directory_info("logs")
        if logs_info:
            print(f"\n日誌目錄:")
            print(f"  檔案數: {logs_info['file_count']}")
            print(f"  總大小: {logs_info['total_size_mb']:.1f} MB")
        
    elif args.age_only:
        cleanup.cleanup_by_age(args.age, args.dry_run)
    elif args.size_only:
        cleanup.cleanup_by_size(args.size, dry_run=args.dry_run)
    elif args.logs_only:
        cleanup.cleanup_log_files(args.log_age, dry_run=args.dry_run)
    else:
        cleanup.run_comprehensive_cleanup(
            max_age_days=args.age,
            max_size_mb=args.size,
            max_log_age_days=args.log_age,
            dry_run=args.dry_run
        )

if __name__ == "__main__":
    main()