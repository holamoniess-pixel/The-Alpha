#!/usr/bin/env python3
"""
ALPHA OMEGA - STARTUP SCRIPT
System initialization and launch with comprehensive checks
Version: 1.1.0 Production Ready
"""

import asyncio
import sys
import os
import time
import logging
import json
import subprocess
import platform
from pathlib import Path
from typing import Dict, Any, List, Optional
import psutil

# Setup logging for startup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/startup.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AlphaOmegaStartup:
    """
    Comprehensive startup system for Alpha Omega
    """
    
    def __init__(self):
        self.base_path = Path.cwd()
        self.config_file = self.base_path / "config.yaml"
        self.required_files = [
            "config.yaml",
            "alpha_omega_main.py",
            "voice_system.py",
            "intelligence_engine.py",
            "learning_engine.py",
            "memory_system.py",
            "automation_engine.py",
            "automation.py"
        ]
        self.required_directories = [
            "data",
            "models", 
            "logs",
            "sounds",
            "web"
        ]
        self.system_info = self._get_system_info()
        self.startup_issues = []
        
        logger.info("Alpha Omega Startup initialized")
    
    def _get_system_info(self) -> Dict[str, Any]:
        """Get comprehensive system information"""
        try:
            return {
                "platform": platform.system(),
                "architecture": platform.architecture()[0],
                "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                "cpu_count": psutil.cpu_count(),
                "memory_total": psutil.virtual_memory().total,
                "disk_free": psutil.disk_usage(self.base_path).free,
                "boot_time": psutil.boot_time()
            }
        except Exception as e:
            logger.warning(f"Could not get complete system info: {e}")
            return {"platform": platform.system()}
    
    def check_installation(self) -> bool:
        """Check if system is properly installed"""
        logger.info("Checking installation integrity...")
        
        all_good = True
        
        # Check required files
        for file_path in self.required_files:
            full_path = self.base_path / file_path
            if not full_path.exists():
                logger.error(f"Missing required file: {file_path}")
                self.startup_issues.append(f"Missing file: {file_path}")
                all_good = False
            else:
                logger.info(f"✅ Found: {file_path}")
        
        # Check required directories
        for dir_path in self.required_directories:
            full_path = self.base_path / dir_path
            if not full_path.exists():
                logger.error(f"Missing required directory: {dir_path}")
                self.startup_issues.append(f"Missing directory: {dir_path}")
                all_good = False
            else:
                logger.info(f"✅ Found: {dir_path}")
        
        # Check Python version
        if sys.version_info < (3, 8):
            logger.error(f"Python 3.8+ required, found {sys.version_info.major}.{sys.version_info.minor}")
            self.startup_issues.append("Python version too old")
            all_good = False
        else:
            logger.info(f"✅ Python version: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
        
        # Check disk space
        try:
            free_gb = psutil.disk_usage(self.base_path).free / (1024**3)
            if free_gb < 1:
                logger.error(f"Insufficient disk space: {free_gb:.1f}GB available")
                self.startup_issues.append("Insufficient disk space")
                all_good = False
            else:
                logger.info(f"✅ Disk space: {free_gb:.1f}GB available")
        except Exception as e:
            logger.warning(f"Could not check disk space: {e}")
        
        # Check memory
        try:
            total_memory = psutil.virtual_memory().total / (1024**3)
            if total_memory < 2:
                logger.warning(f"Low memory: {total_memory:.1f}GB total")
                self.startup_issues.append("Low system memory")
            else:
                logger.info(f"✅ Memory: {total_memory:.1f}GB total")
        except Exception as e:
            logger.warning(f"Could not check memory: {e}")
        
        return all_good
    
    def check_dependencies(self) -> bool:
        """Check if all required dependencies are available"""
        logger.info("Checking dependencies...")
        
        critical_modules = [
            "numpy", "cv2", "pyautogui", "pyperclip", "keyboard", 
            "mouse", "psutil", "yaml", "requests", "PIL", "screeninfo"
        ]
        
        optional_modules = [
            "pyaudio", "pyttsx3", "whisper", "torch", "transformers",
            "llama_cpp", "chromadb", "sklearn", "win32gui", "wmi"
        ]
        
        all_good = True
        
        # Check critical modules
        for module in critical_modules:
            try:
                __import__(module)
                logger.info(f"✅ Critical module: {module}")
            except ImportError as e:
                logger.error(f"❌ Missing critical module: {module} - {e}")
                self.startup_issues.append(f"Missing critical module: {module}")
                all_good = False
        
        # Check optional modules
        for module in optional_modules:
            try:
                __import__(module)
                logger.info(f"✅ Optional module: {module}")
            except ImportError as e:
                logger.warning(f"⚠️  Missing optional module: {module} - {e}")
                self.startup_issues.append(f"Missing optional module: {module}")
        
        return all_good
    
    def check_configuration(self) -> bool:
        """Check configuration file"""
        logger.info("Checking configuration...")
        
        try:
            import yaml
            
            if not self.config_file.exists():
                logger.error("Configuration file not found")
                self.startup_issues.append("Missing configuration file")
                return False
            
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # Check required sections
            required_sections = ['system', 'voice', 'intelligence', 'automation', 'memory', 'security']
            for section in required_sections:
                if section not in config:
                    logger.error(f"Missing configuration section: {section}")
                    self.startup_issues.append(f"Missing config section: {section}")
                    return False
                else:
                    logger.info(f"✅ Configuration section: {section}")
            
            # Check wake word
            wake_word = config.get('voice', {}).get('wake_word', '')
            if not wake_word:
                logger.warning("No wake word configured")
            else:
                logger.info(f"✅ Wake word: '{wake_word}'")
            
            return True
            
        except Exception as e:
            logger.error(f"Configuration check failed: {e}")
            self.startup_issues.append(f"Configuration error: {e}")
            return False
    
    def check_ports(self) -> bool:
        """Check if required ports are available"""
        logger.info("Checking ports...")
        
        import socket
        
        # Check web server port (8080)
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('localhost', 8080))
            sock.close()
            
            if result == 0:
                logger.warning("Port 8080 is in use - web server may conflict")
                self.startup_issues.append("Port 8080 in use")
                return False
            else:
                logger.info("✅ Port 8080 available for web server")
                return True
                
        except Exception as e:
            logger.warning(f"Could not check port 8080: {e}")
            return True
    
    def check_system_health(self) -> bool:
        """Check overall system health"""
        logger.info("Checking system health...")
        
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            if cpu_percent > 90:
                logger.warning(f"High CPU usage: {cpu_percent}%")
                self.startup_issues.append(f"High CPU usage: {cpu_percent}%")
            else:
                logger.info(f"✅ CPU usage: {cpu_percent}%")
            
            # Memory usage
            memory = psutil.virtual_memory()
            if memory.percent > 90:
                logger.warning(f"High memory usage: {memory.percent}%")
                self.startup_issues.append(f"High memory usage: {memory.percent}%")
            else:
                logger.info(f"✅ Memory usage: {memory.percent}%")
            
            # Disk usage
            disk = psutil.disk_usage(self.base_path)
            if disk.percent > 90:
                logger.warning(f"High disk usage: {disk.percent}%")
                self.startup_issues.append(f"High disk usage: {disk.percent}%")
            else:
                logger.info(f"✅ Disk usage: {disk.percent}%")
            
            return True
            
        except Exception as e:
            logger.warning(f"System health check failed: {e}")
            return True
    
    def generate_startup_report(self) -> Dict[str, Any]:
        """Generate comprehensive startup report"""
        logger.info("Generating startup report...")
        
        report = {
            "timestamp": time.time(),
            "system_info": self.system_info,
            "startup_issues": self.startup_issues,
            "status": "SUCCESS" if len(self.startup_issues) == 0 else "WARNINGS" if len([i for i in self.startup_issues if "Missing" not in i]) == 0 else "ERRORS",
            "recommendations": []
        }
        
        # Generate recommendations
        if any("Missing critical" in issue for issue in self.startup_issues):
            report["recommendations"].append("Run 'pip install -r requirements.txt' to install missing dependencies")
        
        if any("Missing file" in issue for issue in self.startup_issues):
            report["recommendations"].append("Run installation script to create missing files")
        
        if any("High" in issue for issue in self.startup_issues):
            report["recommendations"].append("Close unnecessary applications to free up system resources")
        
        if any("Port" in issue for issue in self.startup_issues):
            report["recommendations"].append("Free up port 8080 or change web server port in configuration")
        
        return report
    
    def print_startup_banner(self):
        """Print startup banner"""
        banner = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║    ██████╗ ██╗      █████╗  ██████╗██╗  ██╗     ██╗  ██╗ ██████╗ ███╗   ██╗ ║
║    ██╔══██╗██║     ██╔══██╗██╔════╝██║ ██╔╝     ██║  ██║██╔═████╗████╗  ██║ ║
║    ██████╔╝██║     ███████║██║     █████╔╝█████╗███████║██║██╔██║██╔██╗ ██║ ║
║    ██╔══██╗██║     ██╔══██║██║     ██╔═██╗╚════╝██╔══██║████╔╝██║██║╚██╗██║ ║
║    ██████╔╝███████╗██║  ██║╚██████╗██║  ██╗     ██║  ██║╚██████╔╝██║ ╚████║ ║
║    ╚═════╝ ╚══════╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝     ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝ ║
║                                                                              ║
║                    Voice-Activated PC Control System                         ║
║                         Version 1.1.0 Production Ready                       ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
        """
        print(banner)
    
    async def run_startup_checks(self) -> bool:
        """Run all startup checks"""
        self.print_startup_banner()
        
        logger.info("Starting Alpha Omega system checks...")
        logger.info(f"Platform: {self.system_info['platform']}")
        logger.info(f"Python: {self.system_info['python_version']}")
        logger.info(f"CPU Cores: {self.system_info['cpu_count']}")
        
        # Run all checks
        checks = [
            ("Installation", self.check_installation),
            ("Dependencies", self.check_dependencies),
            ("Configuration", self.check_configuration),
            ("Ports", self.check_ports),
            ("System Health", self.check_system_health)
        ]
        
        results = {}
        for check_name, check_func in checks:
            try:
                results[check_name] = check_func()
                logger.info(f"✅ {check_name} check completed")
            except Exception as e:
                logger.error(f"❌ {check_name} check failed: {e}")
                results[check_name] = False
                self.startup_issues.append(f"{check_name} check failed: {e}")
        
        # Generate report
        report = self.generate_startup_report()
        
        # Print summary
        print(f"\n{'='*60}")
        print("STARTUP CHECKS SUMMARY")
        print(f"{'='*60}")
        
        for check_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{check_name:.<50} {status}")
        
        print(f"\nOverall Status: {report['status']}")
        print(f"Issues Found: {len(report['startup_issues'])}")
        
        if report['startup_issues']:
            print("\nIssues:")
            for issue in report['startup_issues']:
                print(f"  • {issue}")
        
        if report['recommendations']:
            print("\nRecommendations:")
            for rec in report['recommendations']:
                print(f"  • {rec}")
        
        # Save report
        try:
            report_file = self.base_path / "logs" / f"startup_report_{int(time.time())}.json"
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, default=str)
            logger.info(f"Startup report saved: {report_file}")
        except Exception as e:
            logger.warning(f"Could not save startup report: {e}")
        
        return len([i for i in self.startup_issues if "Missing critical" in i or "Missing file" in i]) == 0
    
    async def start_system(self) -> bool:
        """Start the Alpha Omega system"""
        try:
            logger.info("Starting Alpha Omega system...")
            
            # Import and initialize system
            from alpha_omega_main import AlphaOmegaSystem
            
            system = AlphaOmegaSystem()
            
            logger.info("Initializing system components...")
            success = await system.initialize()
            
            if success:
                logger.info("✅ System initialization successful")
                
                print(f"\n{'='*60}")
                print("🎉 ALPHA OMEGA SYSTEM READY")
                print(f"{'='*60}")
                print(f"Version: {system.version}")
                print(f"Wake Word: '{system.config.get('voice', {}).get('wake_word', 'hey alpha')}'")
                print(f"Web Interface: http://localhost:8080")
                print(f"Logs: logs/")
                print(f"{'='*60}")
                print("\nSay the wake word to activate voice control!")
                print("Press Ctrl+C to stop the system gracefully.")
                print(f"{'='*60}\n")
                
                # Start the system
                await system.start()
                return True
            else:
                logger.error("❌ System initialization failed")
                return False
                
        except KeyboardInterrupt:
            logger.info("Startup interrupted by user")
            return False
        except Exception as e:
            logger.error(f"Failed to start system: {e}")
            self.startup_issues.append(f"System start failed: {e}")
            return False
    
    async def run_startup(self) -> bool:
        """Run complete startup process"""
        try:
            # Run startup checks
            checks_passed = await self.run_startup_checks()
            
            if not checks_passed:
                print("\n❌ Critical issues detected. System cannot start.")
                print("Please fix the issues above and try again.")
                return False
            
            # Ask user if they want to continue with warnings
            if self.startup_issues:
                print(f"\n⚠️  {len(self.startup_issues)} non-critical issues detected.")
                response = input("Do you want to continue? (y/N): ").strip().lower()
                if response not in ['y', 'yes']:
                    print("Startup cancelled by user.")
                    return False
            
            # Start the system
            return await self.start_system()
            
        except KeyboardInterrupt:
            print("\n\n👋 Startup cancelled by user.")
            return False
        except Exception as e:
            logger.error(f"Startup process failed: {e}")
            return False


async def main():
    """Main startup function"""
    startup = AlphaOmegaStartup()
    
    try:
        success = await startup.run_startup()
        
        if success:
            print("\n✅ Alpha Omega startup completed successfully!")
        else:
            print("\n❌ Alpha Omega startup failed.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"\n💥 Fatal startup error: {e}")
        logger.error(f"Fatal startup error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    # Run the startup
    asyncio.run(main())