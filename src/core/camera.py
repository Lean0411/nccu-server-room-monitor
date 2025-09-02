"""
相機管理模組 - 處理影像擷取和緩衝區管理

管理 Pi Camera 的影像擷取、儲存和循環緩衝區。
"""

import io
import logging
import threading
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from PIL import Image
from picamera import PiCamera


class CameraStatus:
    """相機狀態追蹤"""
    
    def __init__(self):
        self.is_active = False
        self.total_frames = 0
        self.failed_captures = 0
        self.last_capture_time: Optional[float] = None
        self.fps = 0.0
        self.buffer_size = 0
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert status to dictionary."""
        return {
            "is_active": self.is_active,
            "total_frames": self.total_frames,
            "failed_captures": self.failed_captures,
            "last_capture_time": self.last_capture_time,
            "fps": round(self.fps, 2),
            "buffer_size": self.buffer_size
        }


class FrameBuffer:
    """影像循環緩衝區"""
    
    def __init__(self, max_size: int = 20):
        """初始化緩衝區
        
        Args:
            max_size: 最大儲存影格數
        """
        self.max_size = max_size
        self.frames: deque = deque(maxlen=max_size)
        self.lock = threading.Lock()
        self.logger = logging.getLogger(f"{__name__}.FrameBuffer")
        
    def add_frame(self, frame_data: bytes, timestamp: float):
        """新增影格到緩衝區
        
        Args:
            frame_data: 原始影格資料
            timestamp: 擷取時間戳
        """
        with self.lock:
            frame = {
                "data": frame_data,
                "timestamp": timestamp,
                "datetime": datetime.fromtimestamp(timestamp)
            }
            self.frames.append(frame)
            
    def get_frames(self, count: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get frames from buffer.
        
        Args:
            count: Number of frames to retrieve (None for all)
            
        Returns:
            List of frame dictionaries
        """
        with self.lock:
            if count is None:
                return list(self.frames)
            return list(self.frames)[-count:]
            
    def clear(self):
        """Clear all frames from buffer."""
        with self.lock:
            self.frames.clear()
            self.logger.debug("Frame buffer cleared")
            
    def get_size(self) -> int:
        """Get current buffer size."""
        return len(self.frames)
        
    def get_memory_usage(self) -> int:
        """Calculate buffer memory usage in bytes."""
        with self.lock:
            return sum(len(frame["data"]) for frame in self.frames)


class ROI:
    """Region of Interest for camera capture."""
    
    def __init__(self, x: int, y: int, width: int, height: int):
        """Initialize ROI.
        
        Args:
            x: X coordinate of top-left corner
            y: Y coordinate of top-left corner
            width: ROI width
            height: ROI height
        """
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        
    def to_tuple(self) -> Tuple[int, int, int, int]:
        """Convert to tuple format (x, y, width, height)."""
        return (self.x, self.y, self.width, self.height)
        
    def to_normalized(self, image_width: int, image_height: int) -> Tuple[float, float, float, float]:
        """Convert to normalized coordinates (0.0-1.0).
        
        Args:
            image_width: Total image width
            image_height: Total image height
            
        Returns:
            Normalized ROI coordinates
        """
        return (
            self.x / image_width,
            self.y / image_height,
            self.width / image_width,
            self.height / image_height
        )


class CameraManager:
    """相機管理器 - 協調所有相機操作"""
    
    def __init__(self, config: Any):
        """初始化相機管理器
        
        Args:
            config: 系統配置物件
        """
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.CameraManager")
        self.status = CameraStatus()
        
        # Camera settings
        self.resolution = config.camera.resolution
        self.framerate = config.camera.framerate
        self.rotation = config.camera.rotation
        self.roi = ROI(
            config.camera.roi_x,
            config.camera.roi_y,
            config.camera.roi_width,
            config.camera.roi_height
        ) if config.camera.use_roi else None
        
        # Buffer management
        self.buffer = FrameBuffer(max_size=config.camera.buffer_size)
        
        # Threading
        self.camera: Optional[PiCamera] = None
        self.capture_thread: Optional[threading.Thread] = None
        self.running = False
        self.lock = threading.Lock()
        
        # Performance tracking
        self.last_fps_calc = time.time()
        self.fps_frame_count = 0
        
    def start(self):
        """Start camera capture."""
        if self.running:
            self.logger.warning("Camera already running")
            return
            
        try:
            self._initialize_camera()
            self.running = True
            self.status.is_active = True
            
            # Start capture thread
            self.capture_thread = threading.Thread(
                target=self._capture_loop,
                daemon=True
            )
            self.capture_thread.start()
            
            self.logger.info("Camera manager started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start camera: {e}")
            self.status.is_active = False
            raise
            
    def stop(self):
        """Stop camera capture."""
        if not self.running:
            return
            
        self.logger.info("Stopping camera manager...")
        self.running = False
        
        # Wait for capture thread
        if self.capture_thread:
            self.capture_thread.join(timeout=5)
            
        # Close camera
        if self.camera:
            try:
                self.camera.close()
            except Exception as e:
                self.logger.error(f"Error closing camera: {e}")
            finally:
                self.camera = None
                
        self.status.is_active = False
        self.logger.info("Camera manager stopped")
        
    def _initialize_camera(self):
        """Initialize Pi Camera with configured settings."""
        self.logger.info("Initializing camera...")
        
        try:
            self.camera = PiCamera()
            
            # Apply settings
            self.camera.resolution = self.resolution
            self.camera.framerate = self.framerate
            self.camera.rotation = self.rotation
            
            # Set ROI if configured
            if self.roi:
                normalized_roi = self.roi.to_normalized(
                    self.resolution[0],
                    self.resolution[1]
                )
                self.camera.zoom = normalized_roi
                self.logger.info(f"ROI set to: {self.roi.to_tuple()}")
                
            # Camera warm-up
            time.sleep(2)
            
            self.logger.info(
                f"Camera initialized - Resolution: {self.resolution}, "
                f"Framerate: {self.framerate}, Rotation: {self.rotation}"
            )
            
        except Exception as e:
            self.logger.error(f"Camera initialization failed: {e}")
            raise
            
    def _capture_loop(self):
        """Main capture loop running in separate thread."""
        while self.running:
            try:
                # Capture frame
                frame_data = self.capture_frame_raw()
                if frame_data:
                    timestamp = time.time()
                    self.buffer.add_frame(frame_data, timestamp)
                    
                    self.status.total_frames += 1
                    self.status.last_capture_time = timestamp
                    
                    # Update FPS
                    self._update_fps()
                    
                    # Log periodically
                    if self.status.total_frames % 100 == 0:
                        self.logger.debug(
                            f"Captured {self.status.total_frames} frames, "
                            f"FPS: {self.status.fps:.2f}"
                        )
                        
                # Sleep based on configured interval
                time.sleep(self.config.camera.capture_interval)
                
            except Exception as e:
                self.logger.error(f"Error in capture loop: {e}")
                self.status.failed_captures += 1
                time.sleep(1)  # 錯誤後短暫暫停
                
    def capture_frame_raw(self) -> Optional[bytes]:
        """Capture a raw frame from camera.
        
        Returns:
            Raw frame data as bytes, or None if capture fails
        """
        if not self.camera:
            return None
            
        try:
            stream = io.BytesIO()
            self.camera.capture(stream, format='jpeg', use_video_port=True)
            stream.seek(0)
            return stream.read()
            
        except Exception as e:
            self.logger.error(f"Failed to capture frame: {e}")
            self.status.failed_captures += 1
            return None
            
    def capture_frame(self) -> Optional[Image.Image]:
        """Capture a frame and return as PIL Image.
        
        Returns:
            PIL Image object, or None if capture fails
        """
        frame_data = self.capture_frame_raw()
        if frame_data:
            try:
                return Image.open(io.BytesIO(frame_data))
            except Exception as e:
                self.logger.error(f"Failed to decode frame: {e}")
                return None
        return None
        
    def capture_to_file(self, filepath: Path) -> bool:
        """Capture frame directly to file.
        
        Args:
            filepath: Path to save the image
            
        Returns:
            True if successful, False otherwise
        """
        try:
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            if self.camera:
                self.camera.capture(str(filepath))
                self.logger.info(f"Frame saved to {filepath}")
                return True
            else:
                self.logger.error("Camera not initialized")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to save frame: {e}")
            return False
            
    def get_buffer_images(self) -> List[bytes]:
        """Get all images from buffer as raw bytes.
        
        Returns:
            List of image data as bytes
        """
        frames = self.buffer.get_frames()
        return [frame["data"] for frame in frames]
        
    def save_buffer_to_zip(self, zip_path: Path) -> bool:
        """Save buffer contents to ZIP file.
        
        Args:
            zip_path: Path for the ZIP file
            
        Returns:
            True if successful, False otherwise
        """
        import zipfile
        
        try:
            frames = self.buffer.get_frames()
            if not frames:
                self.logger.warning("No frames in buffer to save")
                return False
                
            zip_path.parent.mkdir(parents=True, exist_ok=True)
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for i, frame in enumerate(frames):
                    timestamp = frame["datetime"].strftime("%Y%m%d_%H%M%S")
                    filename = f"frame_{i:03d}_{timestamp}.jpg"
                    zf.writestr(filename, frame["data"])
                    
            self.logger.info(f"Saved {len(frames)} frames to {zip_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save buffer to ZIP: {e}")
            return False
            
    def apply_motion_detection(self, threshold: int = 25) -> bool:
        """Apply basic motion detection between frames.
        
        Args:
            threshold: Pixel difference threshold for motion
            
        Returns:
            True if motion detected, False otherwise
        """
        frames = self.buffer.get_frames(count=2)
        if len(frames) < 2:
            return False
            
        try:
            # Convert frames to numpy arrays
            img1 = Image.open(io.BytesIO(frames[0]["data"])).convert('L')
            img2 = Image.open(io.BytesIO(frames[1]["data"])).convert('L')
            
            arr1 = np.array(img1)
            arr2 = np.array(img2)
            
            # Calculate difference
            diff = np.abs(arr1.astype(int) - arr2.astype(int))
            motion_pixels = np.sum(diff > threshold)
            
            # Calculate percentage of changed pixels
            total_pixels = arr1.size
            motion_percent = (motion_pixels / total_pixels) * 100
            
            # 超過 1% 像素變化視為偵測到動作
            return motion_percent > 1.0
            
        except Exception as e:
            self.logger.error(f"Motion detection failed: {e}")
            return False
            
    def _update_fps(self):
        """Update FPS calculation."""
        current_time = time.time()
        self.fps_frame_count += 1
        
        # Calculate FPS every second
        if current_time - self.last_fps_calc >= 1.0:
            self.status.fps = self.fps_frame_count / (current_time - self.last_fps_calc)
            self.fps_frame_count = 0
            self.last_fps_calc = current_time
            
    def get_status(self) -> Dict[str, Any]:
        """Get camera status.
        
        Returns:
            Dictionary containing camera status
        """
        status = self.status.to_dict()
        status.update({
            "resolution": self.resolution,
            "framerate": self.framerate,
            "roi": self.roi.to_tuple() if self.roi else None,
            "buffer_memory_mb": self.buffer.get_memory_usage() / 1024 / 1024
        })
        return status
        
    def clear_buffer(self):
        """Clear frame buffer."""
        self.buffer.clear()
        self.logger.info("Frame buffer cleared")
        
    def adjust_settings(self, **kwargs):
        """Adjust camera settings dynamically.
        
        Args:
            **kwargs: Camera settings to adjust
        """
        if not self.camera:
            self.logger.error("Camera not initialized")
            return
            
        with self.lock:
            for key, value in kwargs.items():
                if hasattr(self.camera, key):
                    setattr(self.camera, key, value)
                    self.logger.info(f"Camera {key} set to {value}")
                else:
                    self.logger.warning(f"Unknown camera setting: {key}")