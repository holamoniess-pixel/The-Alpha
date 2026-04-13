"""
Alpha and Omega Installation Script
Sets up the complete voice-activated PC control system
"""

import os
import sys
import subprocess
from pathlib import Path

def check_python_version():
    """Check Python version compatibility"""
    if sys.version_info < (3, 8):
        print("❌ Error: Python 3.8 or higher required")
        print(f"   Current version: {sys.version}")
        return False
    print("✅ Python version OK")
    return True

def install_dependencies():
    """Install required Python packages"""
    print("\n📦 Installing dependencies...")
    
    dependencies = [
        ('numpy', 'Numerical operations'),
        ('pyaudio', 'Audio input/output'),
        ('pyttsx3', 'Text-to-speech'),
        ('pyyaml', 'Configuration files'),
        ('psutil', 'Process management'),
        ('pyautogui', 'GUI automation'),
        ('pynput', 'Keyboard/mouse control'),
        ('pywin32', 'Windows API'),
        ('winsound', 'Windows sounds'),
        ('sqlite3', 'Database (built-in)'),
        ('pickle', 'Serialization (built-in)'),
        ('asyncio', 'Async operations (built-in)'),
        ('json', 'JSON handling (built-in)'),
        ('hashlib', 'Hash functions (built-in)'),
        ('datetime', 'Date/time (built-in)'),
        ('pathlib', 'Path handling (built-in)'),
        ('typing', 'Type hints (built-in)'),
        ('re', 'Regular expressions (built-in)'),
        ('time', 'Time functions (built-in)'),
        ('struct', 'Binary data (built-in)')
    ]
    
    failed_installs = []
    
    for package, description in dependencies:
        print(f"   Installing {package} ({description})...")
        try:
            # Skip built-in modules
            if package in ['sqlite3', 'pickle', 'asyncio', 'json', 'hashlib', 
                          'datetime', 'pathlib', 'typing', 're', 'time', 'struct']:
                print(f"   ✅ {package} (built-in)")
                continue
            
            subprocess.check_call([
                sys.executable, '-m', 'pip', 'install', package
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"   ✅ {package} installed")
        except subprocess.CalledProcessError:
            print(f"   ❌ {package} failed to install")
            failed_installs.append(package)
        except Exception as e:
            print(f"   ❌ {package} error: {e}")
            failed_installs.append(package)
    
    return len(failed_installs) == 0

def create_directories():
    """Create necessary directories"""
    print("\n📁 Creating directories...")
    
    directories = [
        ('data', 'User data and databases'),
        ('models', 'AI model files'),
        ('logs', 'System logs'),
        ('sounds', 'Audio files'),
        ('workflows', 'User workflows')
    ]
    
    for dir_name, description in directories:
        try:
            Path(dir_name).mkdir(exist_ok=True)
            print(f"   ✅ Created {dir_name}/ ({description})")
        except Exception as e:
            print(f"   ❌ Failed to create {dir_name}: {e}")
            return False
    
    return True

def create_config_file():
    """Create default configuration file"""
    print("\n⚙️ Creating configuration file...")
    
    config_content = """# Alpha and Omega Configuration
wake_word: hey alpha
language: en
voice_model: whisper-base
llm_model: llama-7b-q4
memory_limit_mb: 1000
learning_enabled: true
auto_start: true
"""
    
    try:
        with open('config.yaml', 'w') as f:
            f.write(config_content)
        print("   ✅ Created config.yaml")
        return True
    except Exception as e:
        print(f"   ❌ Failed to create config: {e}")
        return False

def create_startup_script():
    """Create Windows startup script"""
    print("\n🚀 Creating startup script...")
    
    startup_script = '''@echo off
echo Starting Alpha and Omega...
python main.py
pause
'''
    
    try:
        with open('start_alpha_omega.bat', 'w') as f:
            f.write(startup_script)
        print("   ✅ Created start_alpha_omega.bat")
        return True
    except Exception as e:
        print(f"   ❌ Failed to create startup script: {e}")
        return False

def check_microphone_access():
    """Check microphone accessibility"""
    print("\n🎤 Checking microphone access...")
    
    try:
        import pyaudio
        audio = pyaudio.PyAudio()
        
        # Try to get default input device info
        try:
            default_input = audio.get_default_input_device_info()
            print(f"   ✅ Microphone found: {default_input['name']}")
            return True
        except:
            print("   ⚠️ No default microphone found")
            return False
    except ImportError:
        print("   ❌ PyAudio not available")
        return False
    except Exception as e:
        print(f"   ❌ Microphone check failed: {e}")
        return False

def show_model_requirements():
    """Display model download requirements"""
    print("\n🤖 Model Requirements:")
    print("   The following models need to be downloaded manually:")
    print("   1. Whisper speech recognition model (base or tiny)")
    print("      - Download from: https://huggingface.co/openai/whisper")
    print("      - Place in: models/whisper-base.pt")
    print("   2. LLaMA language model (quantized)")
    print("      - Download from: https://huggingface.co/TheBloke/llama-7b")
    print("      - Place in: models/llama-7b-q4.gguf")
    print("   3. (Optional) Wake word detection model")
    print("      - For better wake word detection")

def create_readme():
    """Create README with instructions"""
    readme_content = '''# Alpha and Omega - Voice-Activated PC Control

## Quick Start

1. **Install System**
   ```bash
   python install.py
   ```

2. **Download Models**
   - Whisper model: Place in `models/whisper-base.pt`
   - LLaMA model: Place in `models/llama-7b-q4.gguf`

3. **Start System**
   ```bash
   python main.py
   ```
   Or use: `start_alpha_omega.bat`

4. **Voice Commands**
   - Say "Hey Alpha" to activate
   - Try: "Hey Alpha, open Chrome"
   - Try: "Hey Alpha, what time is it?"

## Features

- ✅ Voice control with wake word detection
- ✅ Natural language understanding
- ✅ Application automation
- ✅ Learning from user behavior
- ✅ Memory system
- ✅ Workflow creation
- ✅ 100% offline operation

## Configuration

Edit `config.yaml` to customize:
- Wake word
- Language settings
- Model paths
- Learning preferences

## Troubleshooting

1. **Wake word not detected**
   - Check microphone permissions
   - Adjust voice_sensitivity in config.yaml
   - Try speaking louder/clearer

2. **Models not loading**
   - Verify model files in models/ directory
   - Check file paths in config.yaml

3. **Automation not working**
   - Run as administrator
   - Check Windows security settings
   - Verify pyautogui permissions

## Safety

This system is designed for personal automation and does not:
- Collect personal data
- Connect to external servers
- Share information without consent
- Modify system files without permission
'''
    
    try:
        with open('README.md', 'w', encoding='utf-8') as f:
            f.write(readme_content)
        print("   ✅ Created README.md")
        return True
    except Exception as e:
        print(f"   ❌ Failed to create README: {e}")
        return False

def main():
    """Main installation function"""
    print("=" * 60)
    print("🚀 ALPHA AND OMEGA - INSTALLATION")
    print("=" * 60)
    
    # Check Python version
    if not check_python_version():
        return False
    
    # Install dependencies
    if not install_dependencies():
        print("\n❌ Installation failed due to missing dependencies")
        return False
    
    # Create directories
    if not create_directories():
        print("\n❌ Installation failed due to directory creation")
        return False
    
    # Create config
    if not create_config_file():
        print("\n❌ Installation failed due to config creation")
        return False
    
    # Create startup script
    create_startup_script()
    
    # Check microphone
    check_microphone_access()
    
    # Show model requirements
    show_model_requirements()
    
    # Create README
    create_readme()
    
    print("\n" + "=" * 60)
    print("✅ INSTALLATION COMPLETE!")
    print("=" * 60)
    print("\n📋 Next Steps:")
    print("   1. Download required models (see above)")
    print("   2. Place models in models/ directory")
    print("   3. Run: python main.py")
    print("   4. Say 'Hey Alpha' to start")
    print("\n📖 For help, read README.md")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
