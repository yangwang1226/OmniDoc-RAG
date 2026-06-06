#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
调试辅助工具

用于清理和管理调试会话
"""

import sys
import os
import psutil
import signal
from typing import List, Dict


class DebugHelper:
    """调试辅助类"""
    
    @staticmethod
    def find_python_processes() -> List[Dict]:
        """
        查找所有Python进程
        
        Returns:
            List[Dict]: Python进程列表
        """
        processes = []
        current_pid = os.getpid()
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
            try:
                # 检查是否是Python进程
                if proc.info['name'] and 'python' in proc.info['name'].lower():
                    # 跳过当前进程
                    if proc.info['pid'] == current_pid:
                        continue
                    
                    processes.append({
                        'pid': proc.info['pid'],
                        'name': proc.info['name'],
                        'cmdline': ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else '',
                        'create_time': proc.info['create_time']
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        return processes
    
    @staticmethod
    def kill_process(pid: int, force: bool = False) -> bool:
        """
        终止指定进程
        
        Args:
            pid: 进程ID
            force: 是否强制终止
            
        Returns:
            bool: 是否成功
        """
        try:
            proc = psutil.Process(pid)
            
            if force:
                proc.kill()  # SIGKILL
            else:
                proc.terminate()  # SIGTERM
            
            # 等待进程结束
            try:
                proc.wait(timeout=3)
                return True
            except psutil.TimeoutExpired:
                if not force:
                    # 如果温和终止失败，强制终止
                    proc.kill()
                    proc.wait(timeout=3)
                return True
                
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            print(f"[ERROR] 无法终止进程 {pid}: {e}")
            return False
    
    @staticmethod
    def clean_debug_processes(interactive: bool = True) -> int:
        """
        清理调试相关的Python进程
        
        Args:
            interactive: 是否交互式确认
            
        Returns:
            int: 清理的进程数量
        """
        processes = DebugHelper.find_python_processes()
        
        if not processes:
            print("[INFO] 未找到需要清理的Python进程")
            return 0
        
        print("\n" + "=" * 80)
        print("找到以下Python进程:")
        print("=" * 80)
        
        for i, proc in enumerate(processes, 1):
            print(f"\n{i}. PID: {proc['pid']}")
            print(f"   名称: {proc['name']}")
            print(f"   命令: {proc['cmdline'][:100]}...")
        
        print("\n" + "=" * 80)
        
        if interactive:
            response = input("\n是否清理这些进程? (Y/N): ").strip().upper()
            if response != 'Y':
                print("[INFO] 已取消操作")
                return 0
        
        print("\n正在清理进程...")
        cleaned = 0
        
        for proc in processes:
            try:
                if DebugHelper.kill_process(proc['pid'], force=True):
                    print(f"✓ 已停止进程 PID: {proc['pid']}")
                    cleaned += 1
                else:
                    print(f"✗ 无法停止进程 PID: {proc['pid']}")
            except Exception as e:
                print(f"✗ 停止进程 {proc['pid']} 时出错: {e}")
        
        print(f"\n清理完成! 共清理 {cleaned} 个进程")
        return cleaned
    
    @staticmethod
    def check_port_usage(port: int = 5678) -> bool:
        """
        检查端口是否被占用
        
        Args:
            port: 端口号（默认debugpy端口5678）
            
        Returns:
            bool: 端口是否被占用
        """
        import socket
        
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', port))
                return False  # 端口可用
        except OSError:
            return True  # 端口被占用
    
    @staticmethod
    def release_debug_port(port: int = 5678) -> bool:
        """
        释放调试端口
        
        Args:
            port: 端口号
            
        Returns:
            bool: 是否成功释放
        """
        if not DebugHelper.check_port_usage(port):
            print(f"[INFO] 端口 {port} 未被占用")
            return True
        
        print(f"[WARN] 端口 {port} 被占用，尝试释放...")
        
        # 查找占用端口的进程
        for conn in psutil.net_connections():
            if conn.laddr.port == port:
                try:
                    proc = psutil.Process(conn.pid)
                    print(f"[INFO] 找到占用进程: PID={conn.pid}, Name={proc.name()}")
                    
                    if DebugHelper.kill_process(conn.pid, force=True):
                        print(f"[OK] 已释放端口 {port}")
                        return True
                except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                    print(f"[ERROR] 无法释放端口: {e}")
                    return False
        
        print(f"[WARN] 未找到占用端口 {port} 的进程")
        return False


def main():
    """主函数"""
    print("\n" + "=" * 80)
    print("Python调试端口清理工具")
    print("=" * 80)
    
    # 检查是否需要安装psutil
    try:
        import psutil
    except ImportError:
        print("\n[ERROR] 缺少依赖: psutil")
        print("[INFO] 请运行: pip install psutil")
        sys.exit(1)
    
    # 检查调试端口
    debug_port = 5678
    if DebugHelper.check_port_usage(debug_port):
        print(f"\n[WARN] 调试端口 {debug_port} 被占用")
        DebugHelper.release_debug_port(debug_port)
    else:
        print(f"\n[OK] 调试端口 {debug_port} 可用")
    
    # 清理Python进程
    print("\n" + "-" * 80)
    DebugHelper.clean_debug_processes(interactive=True)
    
    print("\n" + "=" * 80)
    print("完成!")
    print("=" * 80 + "\n")


if __name__ == '__main__':
    main()

