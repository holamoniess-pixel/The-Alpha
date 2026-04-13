import http.server
import socketserver
import json
import os
import urllib.request
import urllib.parse
import sys
import base64
import io
import subprocess
import re
import pyautogui
import cv2
import numpy as np
import time
from PIL import Image
import automation
from voice_auth import VoiceAuthenticator
from openclav_vision import vision_engine, analyze_screen
from openclaw_core import openclaw_core, execute_openclaw_command

try:
    from gtts import gTTS
except ImportError:
    gTTS = None

# Global execution control
PAUSE_STATE = {
    "paused": False,
    "reason": "",
    "since": 0.0,
}

# Commands that are always denied from the chat channel
DENYLIST_SHELL_PREFIXES = [
    "powershell",
    "pwsh",
    "cmd",
    "reg ",
    "schtasks",
    "netsh",
    "sc ",
    "wmic",
]

def _is_paused() -> bool:
    return bool(PAUSE_STATE.get("paused"))

def _set_paused(paused: bool, reason: str = ""):
    PAUSE_STATE["paused"] = bool(paused)
    PAUSE_STATE["reason"] = reason if paused else ""
    PAUSE_STATE["since"] = time.time() if paused else 0.0

def _summarize_action(command: str) -> str:
    return f"I heard a request to execute: {command}"

def _is_shell_command(command: str) -> bool:
    cmd = command.strip().lower()
    if not cmd:
        return False
    first = cmd.split()[0]
    known = {
        "click",
        "type",
        "press",
        "open",
        "screenshot",
        "vol_up",
        "vol_down",
        "mute",
        "minimize_window",
        "maximize_window",
        "shutdown",
        "restart",
        "lock_pc",
        "unlock_pc",
        "hibernate",
        "log_off",
        "system_reset",
        "system_status",
        "status",
    }
    return first not in known

def _normalize_direct_command(user_msg: str) -> str:
    msg = (user_msg or "").strip()
    if not msg:
        return ""
    # Allow direct use of automation command names from UI quick actions.
    direct = {
        "screenshot": "screenshot",
        "take_screenshot": "screenshot",
        "mute": "mute",
        "vol_up": "vol_up",
        "vol_down": "vol_down",
        "task_manager": "task_manager",
        "lock_pc": "lock_pc",
        "shutdown": "shutdown",
        "restart": "restart",
        "hibernate": "hibernate",
        "log_off": "log_off",
        "status": "status",
        "system_status": "status",
        "pause": "pause",
        "resume": "resume",
    }
    key = msg.lower().strip()
    return direct.get(key, "")

def _denylisted_shell(command: str) -> bool:
    c = command.strip().lower()
    for pref in DENYLIST_SHELL_PREFIXES:
        if c.startswith(pref):
            return True
    return False

def _requires_review(command: str) -> bool:
    parts = command.split()
    if not parts:
        return False
    cmd = parts[0].lower()
    if cmd in PEACE_ACTIONS:
        return True
    if _is_shell_command(command):
        return True
    return False

# Initialize Voice Auth
voice_auth = VoiceAuthenticator()
VERIFIED_SESSION = {"expiry": 0}
PEACE_ACTIONS = ["shutdown", "restart", "lock_pc", "unlock_pc", "hibernate", "log_off", "system_reset"]

# Provided API Key
API_KEY = os.environ.get("OPENROUTER_API_KEY")
API_URL = "https://openrouter.ai/api/v1/chat/completions"

PORT = 8000
WEB_DIR = os.path.join(os.getcwd(), "web")

class RaverHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.path = '/web/index.html'
            
        # --- SYSTEM STATUS ENDPOINT ---
        if self.path == '/status':
            try:
                # Gather system stats using automation agent
                status_text = automation.agent.system_status()
                # Parse text to JSON structure for frontend
                # Example text: "OS: Windows ...\nCPU Usage: 5%..."
                lines = status_text.split('\n')
                stats = {}
                for line in lines:
                    if ':' in line:
                        key, val = line.split(':', 1)
                        stats[key.strip()] = val.strip()
                
                # Add verified session info
                stats['Authenticated'] = time.time() < VERIFIED_SESSION['expiry']
                if stats['Authenticated']:
                     stats['Session Expiry'] = int(VERIFIED_SESSION['expiry'] - time.time())
                
                # Add OpenClaw status
                try:
                    openclaw_status = openclaw_core.get_status()
                    stats['OpenClaw Active'] = openclaw_status['active']
                    stats['OpenClaw Objective'] = openclaw_status['objective']
                    stats['OpenClaw Protection'] = openclaw_status['protection_status']
                except Exception as e:
                    stats['OpenClaw Status'] = "Offline"
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(stats).encode('utf-8'))
            except Exception as e:
                self.send_error(500, str(e))
            return

        # --- OPENCLAW VISION ENDPOINT ---
        if self.path == '/vision':
            try:
                # Serve the OpenClaw Vision HTML page
                vision_path = os.path.join(os.getcwd(), "openclaw_vision.html")
                if os.path.exists(vision_path):
                    with open(vision_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    self.wfile.write(content.encode('utf-8'))
                else:
                    self.send_error(404, "OpenClaw Vision page not found")
            except Exception as e:
                self.send_error(500, str(e))
            return

        return http.server.SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self):
        def _read_body_bytes():
            try:
                content_length = int(self.headers.get('Content-Length', '0'))
            except Exception:
                content_length = 0
            return self.rfile.read(content_length) if content_length else b""

        def _read_json_body(allow_plain_text: bool = False):
            post_data = _read_body_bytes()
            try:
                return json.loads(post_data.decode('utf-8')) if post_data else {}
            except Exception as e:
                if allow_plain_text:
                    try:
                        txt = post_data.decode('utf-8', errors='replace')
                    except Exception:
                        txt = ""
                    return {"message": txt}

                try:
                    preview = post_data[:200].decode('utf-8', errors='replace')
                except Exception:
                    preview = ""
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'invalid_json', 'detail': str(e), 'body_preview': preview}).encode('utf-8'))
                return None

        # --- ENROLLMENT ENDPOINT ---
        if self.path == '/enroll':
            try:
                data = _read_json_body()
                if data is None:
                    return
                user_id = data.get('user_id', 'admin')
                audio_b64 = data.get('audio', '')
                
                # Decode audio
                audio_bytes = base64.b64decode(audio_b64)
                
                # Save temp file
                temp_wav = f"temp_enroll_{user_id}.wav"
                with open(temp_wav, "wb") as f:
                    f.write(audio_bytes)
                
                # Enroll
                success = voice_auth.enroll_user(user_id, temp_wav)
                os.remove(temp_wav)
                
                response = {'status': 'success' if success else 'failed', 'message': 'Enrollment complete' if success else 'Enrollment failed'}
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(response).encode('utf-8'))
            except Exception as e:
                self.send_error(500, str(e))
            return

        # --- VERIFICATION ENDPOINT ---
        if self.path == '/verify':
            try:
                data = _read_json_body()
                if data is None:
                    return
                user_id = data.get('user_id', 'admin')
                audio_b64 = data.get('audio', '')
                
                audio_bytes = base64.b64decode(audio_b64)
                
                # Verification logic requires raw PCM usually, but let's see what voice_auth expects
                # voice_auth.verify_user expects raw bytes.
                # If audio_bytes is WAV, we might need to skip header or read it via wave module.
                # Let's save to temp file and read via wave to be safe/consistent with enroll
                
                temp_wav = f"temp_verify_{user_id}.wav"
                with open(temp_wav, "wb") as f:
                    f.write(audio_bytes)
                
                # Read back raw frames
                import wave
                with wave.open(temp_wav, "rb") as wf:
                    raw_data = wf.readframes(wf.getnframes())
                
                verified, score = voice_auth.verify_user(raw_data, user_id)
                os.remove(temp_wav)
                
                if verified:
                    VERIFIED_SESSION['expiry'] = time.time() + 300 # 5 minutes
                    print(f"User {user_id} verified. Session valid until {VERIFIED_SESSION['expiry']}")

                response = {'verified': verified, 'score': score}
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(response).encode('utf-8'))
            except Exception as e:
                self.send_error(500, str(e))
            return

        # --- CHAT / COMMAND ENDPOINT ---
        if self.path == '/chat':
            data = _read_json_body(allow_plain_text=True)
            if data is None:
                return
            user_msg = data.get('message', '')
            action_confirm = bool(data.get('confirm_action', False))
            action_to_confirm = (data.get('action', '') or '').strip()
            
            print(f"User said: {user_msg}")

            # Deterministic direct-command path (used by quick actions and manual typing)
            direct_cmd = _normalize_direct_command(user_msg)
            if direct_cmd and direct_cmd not in {"pause", "resume"}:
                # Always require review for these direct commands; they are system actions.
                if not action_confirm:
                    summary = _summarize_action(direct_cmd)
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        'reply': f"Review required before I run this. {summary}. If correct, confirm.",
                        'review_required': True,
                        'action': direct_cmd,
                        'audio': None
                    }).encode('utf-8'))
                    return

                if action_to_confirm and action_to_confirm != direct_cmd:
                    self.send_response(400)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        'error': 'action_mismatch',
                        'detail': 'Confirmed action did not match requested action.'
                    }).encode('utf-8'))
                    return

                # Execute deterministic command through existing automation executor.
                output = None
                try:
                    output = execute_automation(direct_cmd)
                except Exception as e:
                    output = f"Error executing {direct_cmd}: {e}"

                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'reply': str(output), 'audio': None}).encode('utf-8'))
                return

            # Pause/resume system control commands (text-based for now)
            lowered = (user_msg or "").strip().lower()
            if lowered in {"pause", "pause raver", "stop", "hold"}:
                _set_paused(True, reason="User requested pause")
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'reply': "Paused. Do you want me to explain what I was doing, or do you want to change the task before continuing?",
                    'paused': True,
                    'pause_reason': PAUSE_STATE['reason'],
                    'audio': None
                }).encode('utf-8'))
                return

            if lowered in {"resume", "continue", "unpause"}:
                _set_paused(False)
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'reply': "Resumed.",
                    'paused': False,
                    'audio': None
                }).encode('utf-8'))
                return

            if _is_paused():
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'reply': f"Currently paused ({PAUSE_STATE['reason']}). Say 'resume' to continue or tell me what to change.",
                    'paused': True,
                    'audio': None
                }).encode('utf-8'))
                return
            
            # System Info for Context
            sys_info = f"OS: {os.name} (Windows). CWD: {os.getcwd()}."
            screen_size = pyautogui.size()
            sys_info += f" Screen Size: {screen_size[0]}x{screen_size[1]}."

            # Automation Tools
            def execute_automation(command_str):
                try:
                    # Check for Automation Agent commands
                    parts = command_str.split()
                    cmd = parts[0].lower()
                    args = parts[1:]
                    
                    # --- SECURITY CHECK ---
                    if cmd in PEACE_ACTIONS:
                        if time.time() > VERIFIED_SESSION['expiry']:
                            return "ACCESS DENIED. PEACE ACTION PROTOCOL REQUIRES VOICE VERIFICATION. Please say 'Verify' to authenticate."
                    if _is_shell_command(command_str) and _denylisted_shell(command_str):
                        return "ACCESS DENIED. This type of shell command is blocked from chat execution."
                    
                    # Try automation.py first
                    auto_result = automation.execute_command(cmd, args)
                    if "not found" not in str(auto_result):
                        return str(auto_result)

                    # Fallback to local implementations
                    if cmd == 'click':
                        x, y = int(args[0]), int(args[1])
                        pyautogui.click(x, y)
                        return f"Clicked at {x}, {y}"
                    elif cmd == 'type':
                        text = " ".join(args)
                        pyautogui.write(text, interval=0.05)
                        return f"Typed: {text}"
                    elif cmd == 'press':
                        key = args[0]
                        pyautogui.press(key)
                        return f"Pressed: {key}"
                    elif cmd == 'open':
                        app = " ".join(args)
                        pyautogui.press('win')
                        pyautogui.write(app)
                        pyautogui.press('enter')
                        return f"Opened: {app}"
                    elif cmd == 'screenshot':
                        # Capture screen with OpenClaw Vision Analysis
                        screenshot = pyautogui.screenshot()
                        
                        # Convert to base64 for web display
                        buffered = io.BytesIO()
                        screenshot.save(buffered, format="JPEG", quality=85)  # Optimized quality
                        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
                        
                        # Screen Vision Analysis (OpenClaw Feature)
                        try:
                            # Convert PIL image to OpenCV format for analysis
                            img_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
                            
                            # Basic screen analysis
                            height, width = img_cv.shape[:2]
                            
                            # Detect active windows/contours
                            gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
                            edges = cv2.Canny(gray, 50, 150)
                            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                            
                            # Analyze screen content
                            analysis = f"Screen Analysis: {width}x{height} pixels. "
                            analysis += f"Detected {len(contours)} active regions. "
                            
                            # Check for common UI elements
                            if len(contours) > 10:
                                analysis += "Multiple windows detected. "
                            else:
                                analysis += "Clean desktop environment. "
                                
                            # Color analysis
                            avg_color = np.mean(img_cv, axis=(0,1))
                            if avg_color[0] > 100:
                                analysis += "Blue-dominant interface detected."
                            elif avg_color[1] > 100:
                                analysis += "Green-dominant interface detected."
                            else:
                                analysis += "Neutral color scheme."
                                
                        except Exception as e:
                            analysis = f"Screen Vision Error: {str(e)}"
                        
                        return f"SCREENSHOT_ captured. Vision: {analysis} (Base64 length: {len(img_str)})"
                    # OpenClaw Vision Commands
                     elif cmd == 'screen_vision':
                         return analyze_screen()
                     elif cmd == 'vision_analyze':
                         analysis = vision_engine.analyze_screen_realtime()
                         return f"OpenClaw Vision: {vision_engine.get_screen_summary()}"
                     elif cmd == 'vision_export':
                         format_type = args[0] if args else "json"
                         return vision_engine.export_vision_data(format_type)
                     elif cmd == 'find_automation_targets':
                         screen = vision_engine.capture_screen()
                         targets = vision_engine._find_automation_targets(screen)
                         return f"Found {len(targets)} automation targets: {[t['type'] for t in targets]}"
                     # OpenClaw Core Commands
                     elif cmd.startswith('openclaw_'):
                         openclaw_cmd = cmd.replace('openclaw_', '')
                         return execute_openclaw_command(openclaw_cmd, args)
                     else:
                         # Fallback to shell
                         result = subprocess.run(command_str, shell=True, capture_output=True, text=True, timeout=10)
                         output = result.stdout + "\n" + result.stderr
                         return output.strip() or "Done (No Output)."
                except Exception as e:
                    return f"Error executing {command_str}: {e}"

            # Conversation History
            messages = [
                {"role": "system", "content": f"""You are Raver, a highly intelligent, loyal, and capable AI assistant (Alpha & Omega interface). 
You speak concisely and with a sophisticated, helpful tone. Address the user as 'Sir' or 'Boss'.
SYSTEM POWER: You have full access to the Windows command line and GUI Automation.
OPENCLAW VISION: You can analyze screens, detect UI elements, and identify automation targets.
To execute a command, output it inside <cmd>...</cmd> tags.
Available Commands:
- <cmd>click X Y</cmd> : Click at coordinates.
- <cmd>type TEXT</cmd> : Type text.
- <cmd>press KEY</cmd> : Press a key (e.g. enter, esc, win).
- <cmd>open APP_NAME</cmd> : Open an application.
- <cmd>screenshot</cmd> : Capture screen to view it.
- <cmd>screen_vision</cmd> : Analyze screen with OpenClaw vision.
- <cmd>vision_analyze</cmd> : Detailed screen analysis.
- <cmd>find_automation_targets</cmd> : Find clickable elements.
- <cmd>vol_up</cmd> / <cmd>vol_down</cmd> / <cmd>mute</cmd> : Volume control.
- <cmd>minimize_window</cmd> / <cmd>maximize_window</cmd> : Window control.
- <cmd>shutdown</cmd> / <cmd>restart</cmd> / <cmd>lock_pc</cmd> : Power control.
- <cmd>SHELL_COMMAND</cmd> : Run any shell command (e.g. dir, python ...).

If you run a command, I will execute it and give you the output. Do NOT explain the command before running it. Just run it.
Current System Context: {sys_info}"""},
                {"role": "user", "content": user_msg}
            ]
            
            final_reply = "I'm sorry, I couldn't process that."
            
            # Loop for Tool Use (Max 3 turns)
            for _ in range(3):
                # Call OpenRouter API
                headers = {
                    "Authorization": f"Bearer {API_KEY}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "http://localhost:8000",
                    "X-Title": "Raver Alpha"
                }
                
                payload = {
                    "model": "google/gemini-2.0-flash-001",
                    "messages": messages
                }
                
                try:
                    req = urllib.request.Request(API_URL, data=json.dumps(payload).encode('utf-8'), headers=headers)
                    with urllib.request.urlopen(req) as response:
                        res_body = response.read()
                        res_json = json.loads(res_body)
                        
                        current_reply = ""
                        if 'choices' in res_json and len(res_json['choices']) > 0:
                            current_reply = res_json['choices'][0]['message']['content']
                        
                        # Check for commands
                        cmd_match = re.search(r'<cmd>(.*?)</cmd>', current_reply, re.DOTALL)
                        
                        if cmd_match:
                            command = cmd_match.group(1).strip()
                            print(f"Executing: {command}")

                            # Pre-execution review requirement
                            if _requires_review(command) and not action_confirm:
                                summary = _summarize_action(command)
                                self.send_response(200)
                                self.send_header('Content-type', 'application/json')
                                self.end_headers()
                                self.wfile.write(json.dumps({
                                    'reply': f"Review required before I run this. {summary}. If correct, resend with confirm_action=true.",
                                    'review_required': True,
                                    'action': command,
                                    'audio': None
                                }).encode('utf-8'))
                                return
                            
                            # Run Command / Automation
                            output = execute_automation(command)
                            
                            print(f"Output: {output[:100]}...")
                            
                            # Append to history
                            messages.append({"role": "assistant", "content": current_reply})
                            
                            # If screenshot, we might want to pass image to vision model in next turn (Complex with this simple setup)
                            # For now, just confirm capture. 
                            # Ideally, we would send the image content, but OpenRouter Gemini API supports image input.
                            # TODO: Implement Multi-modal input if screenshot is taken.
                            
                            messages.append({"role": "user", "content": f"System Output:\n{output}\n\nPlease analyze this output and provide the final answer to the user."})
                            continue # Loop again to get final answer
                        else:
                            final_reply = current_reply
                            break # No command, we are done
                            
                except Exception as e:
                    print(f"API Loop Error: {e}")
                    final_reply = "Neural link unstable."
                    break

            print(f"Raver replied: {final_reply[:50]}...")
            
            # Generate TTS Audio (gTTS) - OPTIMIZED for speed
            try:
                # Strip cmd tags from speech if any remain (unlikely in final step but safe)
                clean_text = re.sub(r'<cmd>.*?</cmd>', '', final_reply, flags=re.DOTALL).strip()
                if not clean_text: clean_text = "Task completed."

                if not gTTS:
                    audio_base64 = None
                else:
                    # Speed-optimized TTS with faster settings
                    tts = gTTS(text=clean_text, lang='en', slow=False)
                    mp3_fp = io.BytesIO()
                    tts.write_to_fp(mp3_fp)
                    mp3_fp.seek(0)
                    audio_base64 = base64.b64encode(mp3_fp.read()).decode('utf-8')
            except Exception as tts_err:
                print(f"TTS Error: {tts_err}")
                audio_base64 = None
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'reply': final_reply, 'audio': audio_base64}).encode('utf-8'))
        else:
            self.send_error(404)

if __name__ == "__main__":
    # Change to root dir so we can serve /web
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Allow address reuse to prevent "Address already in use" errors on restart
    socketserver.TCPServer.allow_reuse_address = True
    
    # Use ThreadingTCPServer for multi-tasking backend
    class ThreadingServer(socketserver.ThreadingTCPServer):
        allow_reuse_address = True

    with ThreadingServer(("", PORT), RaverHandler) as httpd:
        print(f"Raver Interface Online at http://localhost:{PORT}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
        httpd.server_close()