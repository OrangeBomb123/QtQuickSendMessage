import sys
import time
import random
import threading
import unicodedata
import pyautogui
import pynput.keyboard as keyboard
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QSpinBox, QDoubleSpinBox,
    QCheckBox, QPushButton, QGridLayout, QVBoxLayout, QGroupBox, QMessageBox,
    QStatusBar, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread

class MessageSenderThread(QThread):
    # 定义信号
    status_updated = pyqtSignal(str)
    finished = pyqtSignal()
    error = pyqtSignal(str)
    
    def __init__(self, message, count, interval, random_interval, multi_message):
        super().__init__()
        self.keyboard = keyboard.Controller()
        self.message = message
        self.count = count
        self.interval = interval
        self.random_interval = random_interval
        self.multi_message = multi_message
        self.running = False
    
    def run(self):
        self.running = True
        messages = self.message.split(";") if self.multi_message else [self.message]
        base_interval = self.interval
        
        try:
            time.sleep(3)
            for i in range(self.count):
                if not self.running:
                    break
                
                for msg in messages:
                    # 确保Unicode字符正确发送
                    normalized_msg = unicodedata.normalize('NFC', msg.strip())
                    try:
                        for char in normalized_msg:
                            self.keyboard.type(char)
                        self.keyboard.press(keyboard.Key.enter)
                        self.keyboard.release(keyboard.Key.enter)
                    except Exception as e:
                        if 'character' in str(e):
                            pyautogui.write(normalized_msg.encode('utf-8').decode('unicode_escape'))
                        else:
                            raise
                
                interval = base_interval * random.uniform(0.8, 1.2) if self.random_interval else base_interval
                time.sleep(interval)
                
                self.status_updated.emit(f"已发送 {i+1}/{self.count} 条：{msg.strip()[:10]}...")
            
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))
            self.finished.emit()
    
    def stop(self):
        self.running = False

class UnicodeSpamGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.sender_thread = None
    
    def init_ui(self):
        self.setWindowTitle("Unicode消息助手 v1.0")
        self.setGeometry(100, 100, 500, 300)
        
        # 主布局
        main_layout = QVBoxLayout()
        
        # 参数设置组
        param_group = QGroupBox("设置参数")
        param_layout = QGridLayout()
        
        # 消息内容
        param_layout.addWidget(QLabel("消息内容："), 0, 0, 1, 1, Qt.AlignmentFlag.AlignLeft)
        self.message_entry = QLineEdit()
        self.message_entry.setPlaceholderText("请输入要发送的消息")
        self.message_entry.setFixedWidth(300)
        param_layout.addWidget(self.message_entry, 0, 1, 1, 2)
        
        # 发送次数
        param_layout.addWidget(QLabel("发送次数："), 1, 0, 1, 1, Qt.AlignmentFlag.AlignLeft)
        self.count_spin = QSpinBox()
        self.count_spin.setMinimum(1)
        self.count_spin.setMaximum(1000)
        self.count_spin.setValue(10)
        self.count_spin.setFixedWidth(100)
        param_layout.addWidget(self.count_spin, 1, 1, 1, 1, Qt.AlignmentFlag.AlignLeft)
        
        # 间隔时间
        param_layout.addWidget(QLabel("间隔时间（秒）："), 2, 0, 1, 1, Qt.AlignmentFlag.AlignLeft)
        self.interval_spin = QDoubleSpinBox()
        self.interval_spin.setMinimum(0.1)
        self.interval_spin.setMaximum(10.0)
        self.interval_spin.setSingleStep(0.1)
        self.interval_spin.setValue(1.0)
        self.interval_spin.setFixedWidth(100)
        param_layout.addWidget(self.interval_spin, 2, 1, 1, 1, Qt.AlignmentFlag.AlignLeft)
        
        # 选项
        self.random_interval = QCheckBox("随机间隔 (±20%)")
        param_layout.addWidget(self.random_interval, 3, 1, 1, 1, Qt.AlignmentFlag.AlignLeft)
        
        self.multi_message = QCheckBox("多重消息（分号分隔）")
        param_layout.addWidget(self.multi_message, 3, 2, 1, 1, Qt.AlignmentFlag.AlignLeft)
        
        param_group.setLayout(param_layout)
        main_layout.addWidget(param_group)
        
        # 按钮布局
        button_layout = QGridLayout()
        self.start_btn = QPushButton("开始发送")
        self.start_btn.clicked.connect(self.start_sending)
        button_layout.addWidget(self.start_btn, 0, 0, 1, 1, Qt.AlignmentFlag.AlignCenter)
        
        self.stop_btn = QPushButton("停止")
        self.stop_btn.clicked.connect(self.stop_sending)
        self.stop_btn.setEnabled(False)
        button_layout.addWidget(self.stop_btn, 0, 1, 1, 1, Qt.AlignmentFlag.AlignCenter)
        
        button_frame = QFrame()
        button_frame.setLayout(button_layout)
        main_layout.addWidget(button_frame)
        
        # 状态栏
        self.status_bar = QStatusBar()
        self.status_bar.showMessage("准备就绪")
        main_layout.addWidget(self.status_bar)
        
        self.setLayout(main_layout)
    
    def validate_input(self):
        message = self.message_entry.text().strip()
        if not message:
            QMessageBox.critical(self, "输入错误", "消息内容不能为空")
            return False
        
        # 检查Unicode字符是否可打印
        for char in message:
            if unicodedata.category(char) in ('Cc', 'Cf', 'Co', 'Cn'):
                QMessageBox.critical(self, "输入错误", f"包含不可打印字符: {char}")
                return False
        
        return True
    
    def start_sending(self):
        if not self.validate_input():
            return
        
        message = self.message_entry.text().strip()
        count = self.count_spin.value()
        interval = self.interval_spin.value()
        random_interval = self.random_interval.isChecked()
        multi_message = self.multi_message.isChecked()
        
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_bar.showMessage("运行中...")
        
        # 创建并启动发送线程
        self.sender_thread = MessageSenderThread(
            message, count, interval, random_interval, multi_message
        )
        self.sender_thread.status_updated.connect(self.update_status)
        self.sender_thread.finished.connect(self.on_finish)
        self.sender_thread.error.connect(self.show_error)
        self.sender_thread.start()
    
    def stop_sending(self):
        if self.sender_thread and self.sender_thread.isRunning():
            self.sender_thread.stop()
            self.status_bar.showMessage("正在停止...")
    
    def update_status(self, status):
        self.status_bar.showMessage(status)
    
    def on_finish(self):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        message = self.message_entry.text().strip()
        self.status_bar.showMessage(f"完成：{message[:20]}...")
        self.sender_thread = None
    
    def show_error(self, error_msg):
        QMessageBox.critical(self, "错误", error_msg)
    
    def closeEvent(self, event):
        if self.sender_thread and self.sender_thread.is_alive():
            reply = QMessageBox.question(
                self, "确认退出", "发送任务正在进行中，确定要退出吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.sender_thread.stop()
                self.sender_thread.join(1)  # 等待1秒让线程结束
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

def main():
    app = QApplication(sys.argv)
    
    # 显示安全提示
    QMessageBox.information(
        None, "使用提示", "请确保：\n1. 已切换到目标输入窗口\n2. 间隔时间设置合理\n3. 遵守相关平台使用规定"
    )
    
    window = UnicodeSpamGUI()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()