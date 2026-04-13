import logging
import time
import threading
from typing import Dict, List, Callable
from alpha_omega import autonomous_objective_loop, simulate_protection
from openclav_vision import vision_engine

class OpenClawCore:
    """
    Core OpenClaw system integration for Raver.
    Provides autonomous operation, protection monitoring, and advanced vision.
    """
    
    def __init__(self):
        self.logger = logging.getLogger("OpenClawCore")
        self.is_active = False
        self.autonomous_thread = None
        self.protection_thread = None
        self.vision_thread = None
        self.current_objective = "Monitor and protect system environment"
        self.protection_status = "Standby"
        self.last_analysis = None
        
        # Callbacks for UI updates
        self.status_callbacks: List[Callable] = []
        
    def start_autonomous_mode(self, objective: str = None):
        """Start autonomous operation mode."""
        if self.is_active:
            self.logger.warning("OpenClaw already active")
            return
            
        self.is_active = True
        self.current_objective = objective or self.current_objective
        
        # Start autonomous thread
        self.autonomous_thread = threading.Thread(target=self._autonomous_loop, daemon=True)
        self.autonomous_thread.start()
        
        # Start protection thread
        self.protection_thread = threading.Thread(target=self._protection_loop, daemon=True)
        self.protection_thread.start()
        
        # Start vision analysis thread
        self.vision_thread = threading.Thread(target=self._vision_loop, daemon=True)
        self.vision_thread.start()
        
        self.logger.info("OpenClaw autonomous mode activated")
        self._notify_status("OpenClaw: Autonomous mode active")
    
    def stop_autonomous_mode(self):
        """Stop autonomous operation."""
        self.is_active = False
        
        if self.autonomous_thread:
            self.autonomous_thread.join(timeout=2)
        if self.protection_thread:
            self.protection_thread.join(timeout=2)
        if self.vision_thread:
            self.vision_thread.join(timeout=2)
            
        self.logger.info("OpenClaw autonomous mode deactivated")
        self._notify_status("OpenClaw: Standby mode")
    
    def _autonomous_loop(self):
        """Main autonomous operation loop."""
        while self.is_active:
            try:
                # Execute autonomous objective
                autonomous_objective_loop(self.current_objective)
                
                # Custom autonomous logic
                self._perform_autonomous_tasks()
                
                time.sleep(5)  # 5-second cycle
                
            except Exception as e:
                self.logger.error(f"Autonomous loop error: {e}")
                time.sleep(10)  # Wait longer on error
    
    def _protection_loop(self):
        """System protection monitoring loop."""
        while self.is_active:
            try:
                # Run protection simulation
                simulate_protection(hours=1)  # 1-hour simulation in accelerated mode
                
                # Update protection status
                self.protection_status = "Active - Monitoring"
                self._notify_status(f"Protection: {self.protection_status}")
                
                time.sleep(30)  # 30-second protection cycle
                
            except Exception as e:
                self.logger.error(f"Protection loop error: {e}")
                self.protection_status = "Error"
                time.sleep(60)
    
    def _vision_loop(self):
        """Advanced screen vision analysis loop."""
        while self.is_active:
            try:
                # Perform screen analysis
                analysis = vision_engine.analyze_screen_realtime()
                self.last_analysis = analysis
                
                # Detect automation opportunities
                if analysis.get('automation_opportunities'):
                    opportunities = analysis['automation_opportunities']
                    if len(opportunities) > 0:
                        self.logger.info(f"Found {len(opportunities)} automation opportunities")
                
                # Check for anomalies
                if analysis.get('anomalies'):
                    anomalies = analysis['anomalies']
                    for anomaly in anomalies:
                        if anomaly['severity'] > 0.7:  # High severity
                            self.logger.warning(f"High severity anomaly detected: {anomaly['description']}")
                            self._notify_status(f"Anomaly: {anomaly['description']}")
                
                time.sleep(3)  # 3-second vision cycle
                
            except Exception as e:
                self.logger.error(f"Vision loop error: {e}")
                time.sleep(10)
    
    def _perform_autonomous_tasks(self):
        """Perform autonomous system tasks."""
        # System optimization
        self._optimize_system_performance()
        
        # Memory management
        self._manage_memory_usage()
        
        # Process monitoring
        self._monitor_processes()
    
    def _optimize_system_performance(self):
        """Optimize system performance autonomously."""
        try:
            # CPU optimization suggestions
            import psutil
            cpu_percent = psutil.cpu_percent(interval=1)
            
            if cpu_percent > 80:
                self.logger.warning(f"High CPU usage: {cpu_percent}%")
                # Could implement automatic process management here
            
            # Memory optimization
            memory = psutil.virtual_memory()
            if memory.percent > 85:
                self.logger.warning(f"High memory usage: {memory.percent}%")
                
        except ImportError:
            self.logger.debug("psutil not available for performance monitoring")
        except Exception as e:
            self.logger.error(f"Performance optimization error: {e}")
    
    def _manage_memory_usage(self):
        """Manage memory usage autonomously."""
        try:
            # Clear vision cache if too large
            if hasattr(vision_engine, 'vision_history') and len(vision_engine.vision_history) > 50:
                vision_engine.vision_history = vision_engine.vision_history[-25:]
                
        except Exception as e:
            self.logger.error(f"Memory management error: {e}")
    
    def _monitor_processes(self):
        """Monitor system processes."""
        try:
            import psutil
            
            # Monitor for suspicious processes
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
                try:
                    if proc.info['cpu_percent'] > 50:  # High CPU usage
                        self.logger.info(f"High CPU process: {proc.info['name']} ({proc.info['cpu_percent']}%)")
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
                    
        except ImportError:
            pass
        except Exception as e:
            self.logger.error(f"Process monitoring error: {e}")
    
    def get_status(self) -> Dict:
        """Get current OpenClaw status."""
        return {
            "active": self.is_active,
            "objective": self.current_objective,
            "protection_status": self.protection_status,
            "last_analysis": self.last_analysis,
            "threads_active": {
                "autonomous": self.autonomous_thread.is_alive() if self.autonomous_thread else False,
                "protection": self.protection_thread.is_alive() if self.protection_thread else False,
                "vision": self.vision_thread.is_alive() if self.vision_thread else False
            }
        }
    
    def add_status_callback(self, callback: Callable):
        """Add a callback for status updates."""
        self.status_callbacks.append(callback)
    
    def _notify_status(self, message: str):
        """Notify all status callbacks."""
        for callback in self.status_callbacks:
            try:
                callback(message)
            except Exception as e:
                self.logger.error(f"Status callback error: {e}")
    
    def execute_command(self, command: str, args: List[str] = None) -> str:
        """Execute OpenClaw-specific commands."""
        args = args or []
        
        if command == "status":
            status = self.get_status()
            return f"OpenClaw Status: Active={status['active']}, Objective={status['objective']}, Protection={status['protection_status']}"
        
        elif command == "start":
            objective = " ".join(args) if args else None
            self.start_autonomous_mode(objective)
            return "OpenClaw autonomous mode started"
        
        elif command == "stop":
            self.stop_autonomous_mode()
            return "OpenClaw autonomous mode stopped"
        
        elif command == "objective":
            if args:
                self.current_objective = " ".join(args)
                return f"Objective updated: {self.current_objective}"
            else:
                return f"Current objective: {self.current_objective}"
        
        elif command == "vision":
            if self.last_analysis:
                return vision_engine.get_screen_summary()
            else:
                return "No vision analysis available"
        
        else:
            return f"Unknown OpenClaw command: {command}"

# Global instance
openclaw_core = OpenClawCore()

def execute_openclaw_command(command: str, args: List[str] = None) -> str:
    """Execute OpenClaw command (wrapper for automation.py integration)."""
    return openclaw_core.execute_command(command, args)