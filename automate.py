#!/usr/bin/env python3
import subprocess
import socket
import re
import os
import sys
import requests
from pathlib import Path
import glob
import time
import psutil

def get_ipv4_address():
    """Get the IPv4 address of the current device"""
    try:
        # Connect to a remote address to determine local IP
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
        print(f"IPv4 Address: {ip}")
        return ip
    except Exception as e:
        print(f"Error getting IPv4 address: {e}")
        return None

def kill_processes_on_ports(ports):
    """Kill all processes using the specified ports"""
    killed_processes = []
    
    for port in ports:
        try:
            print(f"🔍 Checking for processes on port {port}...")
            
            # Use netstat to find processes using the port
            result = subprocess.run(['netstat', '-ano'], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                lines = result.stdout.split('\\n')
                for line in lines:
                    # Look for TCP connections on the specific port that are LISTENING
                    if f':{port}' in line and 'LISTENING' in line and 'TCP' in line:
                        parts = line.strip().split()
                        if len(parts) >= 5:
                            pid = parts[-1]
                            try:
                                pid_int = int(pid)
                                if pid_int not in killed_processes:
                                    print(f"🔪 Killing process {pid} on port {port}")
                                    # Use taskkill with /F for force and /T for tree
                                    subprocess.run(['taskkill', '/F', '/T', '/PID', str(pid)], 
                                                 capture_output=True, timeout=10)
                                    killed_processes.append(pid_int)
                                    print(f"✅ Killed process {pid}")
                            except (ValueError, subprocess.TimeoutExpired) as e:
                                print(f"⚠️ Error killing process {pid}: {e}")
                                
        except Exception as e:
            print(f"⚠️ Error checking port {port}: {e}")
    
    # Wait a moment for processes to fully terminate
    if killed_processes:
        print("⏳ Waiting for processes to terminate...")
        time.sleep(2)
    
    return killed_processes

def force_kill_python_servers():
    """Force kill any Python processes that might be running servers"""
    try:
        print("🔍 Looking for Python server processes...")
        
        # Get all running processes
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                # Check if it's a Python process running server.py
                if (proc.info['name'] and 'python' in proc.info['name'].lower() and 
                    proc.info['cmdline'] and any('server.py' in arg for arg in proc.info['cmdline'])):
                    
                    print(f"🔪 Killing Python server process {proc.info['pid']}")
                    proc.kill()
                    print(f"✅ Killed Python server process {proc.info['pid']}")
                    
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                # Process might have already terminated
                continue
            except Exception as e:
                print(f"⚠️ Error checking process: {e}")
                continue
                
    except Exception as e:
        print(f"⚠️ Error in force_kill_python_servers: {e}")

def run_key_script():
    """Run key.py and capture the output"""
    try:
        result = subprocess.run([sys.executable, "key.py"], 
                              capture_output=True, text=True, check=True)
        output = result.stdout.strip()
        
        # Parse API Key and Secret from output
        api_key_match = re.search(r'API Key: (.+)', output)
        api_secret_match = re.search(r'API Secret: (.+)', output)
        
        if api_key_match and api_secret_match:
            return api_key_match.group(1), api_secret_match.group(1)
        else:
            raise ValueError("Could not parse API key and secret from key.py output")
            
    except subprocess.CalledProcessError as e:
        print(f"Error running key.py: {e}")
        return None, None
    except Exception as e:
        print(f"Error parsing key.py output: {e}")
        return None, None

def update_yaml_files(api_key, api_secret, ip_address):
    """Update all YAML files with hardcoded API credentials"""
    yaml_files = glob.glob("*.yaml") + glob.glob("*.yml")
    
    if not yaml_files:
        print("⚠️ No YAML files found in the current directory")
        return False
    
    success = True
    for yaml_file in yaml_files:
        try:
            print(f"📝 Updating {yaml_file}...")
            with open(yaml_file, 'r') as f:
                content = f.read()
            
            # Special case for config.yaml
            if yaml_file == "config.yaml":
                # Update keys section
                content = re.sub(
                    r'keys:\n(?:\s+[a-zA-Z0-9]+:.*\n?)+',
                    f'keys:\n  {api_key}: {api_secret}\n',
                    content,
                    flags=re.MULTILINE
                )
                # Update webhook section with new API key only (remove api_secret if present)
                if 'webhook:' in content:
                    # Remove api_secret if present
                    content = re.sub(
                        r'\n\s*api_secret:.*',
                        '',
                        content
                    )
                    # Update API key if it exists, otherwise add it
                    webhook_api_key_match = re.search(r'api_key:\s*[\'"]?[^\'"]+[\'"]?', content)
                    if webhook_api_key_match:
                        content = re.sub(
                            r'api_key:\s*[\'"]?[^\'"]+[\'"]?',
                            f"api_key: {api_key}",
                            content
                        )
                    else:
                        # If api_key doesn't exist, add it under webhook section
                        content = re.sub(
                            r'(webhook:\n)',
                            r'\g<1>  api_key: {}\n'.format(api_key),
                            content
                        )
                    # Ensure webhook URLs exist with the correct IP address
                    if 'urls:' not in content:
                        # Add urls section if it doesn't exist
                        content = re.sub(
                            r'(webhook:\n(?:\s*api_key:[^\n]+\n)?)',
                            r'\g<1>  urls:\n    - http://{}:5005/webhook\n'.format(ip_address),
                            content
                        )
                    else:
                        # Update existing URLs with new IP address
                        content = re.sub(
                            r'(\s*- "http://)[^"]+(:5005/webhook")',
                            r'\g<1>' + ip_address + r'\g<2>',
                            content
                        )
                else:
                    # If webhook section doesn't exist, create it with only api_key
                    content += f'''\nwebhook:\n  api_key: {api_key}\n  urls:\n    - http://{ip_address}:5005/webhook\n'''
            
            # Special case for sip-config.yaml
            elif yaml_file == "sip-config.yaml":
                # Always update api_key, api_secret, ws_url as single-quoted (even if commented)
                content = re.sub(
                    r'(#?\s*api_key:)\s*[\'\"]?[^\'\"]*[\'\"]?',
                    f"api_key: '{api_key}'",
                    content
                )
                content = re.sub(
                    r'(#?\s*api_secret:)\s*[\'\"]?[^\'\"]*[\'\"]?',
                    f"api_secret: '{api_secret}'",
                    content
                )
                content = re.sub(
                    r'(#?\s*ws_url:)\s*[\'\"]?[^\'\"]*[\'\"]?',
                    f"ws_url: 'ws://{ip_address}:7880'",
                    content
                )
            else:
                # Update API Key (handling different formats)
                content = re.sub(
                    r'api_key:\\s*\\${LIVEKIT_API_KEY}',
                    f'api_key: {api_key}',
                    content
                )
                content = re.sub(
                    r'apiKey:\\s*\\${LIVEKIT_API_KEY}',
                    f'apiKey: {api_key}',
                    content
                )
                content = re.sub(
                    r'LIVEKIT_API_KEY=\\${LIVEKIT_API_KEY}',
                    f'LIVEKIT_API_KEY={api_key}',
                    content
                )
                
                # Update API Secret (handling different formats)
                content = re.sub(
                    r'api_secret:\\s*\\${LIVEKIT_API_SECRET}',
                    f'api_secret: {api_secret}',
                    content
                )
                content = re.sub(
                    r'apiSecret:\\s*\\${LIVEKIT_API_SECRET}',
                    f'apiSecret: {api_secret}',
                    content
                )
                content = re.sub(
                    r'LIVEKIT_API_SECRET=\\${LIVEKIT_API_SECRET}',
                    f'LIVEKIT_API_SECRET={api_secret}',
                    content
                )
            
            # Update ws_url or url with IP address for config.yaml and sip-config.yaml
            if yaml_file in ["config.yaml", "sip-config.yaml"]:
                # Replace ws_url: ... with single quotes
                content = re.sub(
                    r'ws_url:\s*.*',
                    f"ws_url: 'ws://{ip_address}:7880'",
                    content
                )
                # Replace url: ...
                content = re.sub(
                    r'url:\s*.*',
                    f"url: ws://{ip_address}:7880",
                    content
                )
            
            # Special case for docker-compose.yaml
            if yaml_file == "docker-compose.yaml":
                # Ensure api_key, api_secret, ws_url are present and single-quoted at the top of SIP_CONFIG_BODY
                sip_config_match = re.search(r'(SIP_CONFIG_BODY:\s*\|\n)([\s\S]+?)(?=^\S|\Z)', content, re.MULTILINE)
                if sip_config_match:
                    header = sip_config_match.group(1)
                    body = sip_config_match.group(2)
                    # Remove any existing api_key/api_secret/ws_url lines (only at the top, before the first non-matching field)
                    lines = body.splitlines(keepends=True)
                    i = 0
                    while i < len(lines):
                        line = lines[i]
                        if re.match(r"^\s*api_key:", line) or re.match(r"^\s*api_secret:", line) or re.match(r"^\s*ws_url:", line):
                            i += 1
                            continue
                        break
                    # Now, insert the three fields at the top in order, with correct indentation (4 spaces)
                    top = [
                        f"        api_key: '{api_key}'\n",
                        f"        api_secret: '{api_secret}'\n",
                        f"        ws_url: 'ws://{ip_address}:7880'\n"
                    ]
                    # Add the rest of the lines (starting from i)
                    new_body = ''.join(top + lines[i:])
                    content = content[:sip_config_match.start(1)] + header + new_body + content[sip_config_match.end(2):]
                else:
                    # fallback: just add at the top of the file (shouldn't happen)
                    content = f"SIP_CONFIG_BODY: |\n          \t\tapi_key: '{api_key}'\n          \t\tapi_secret: '{api_secret}'\n            \t\tws_url: 'ws://{ip_address}:7880'\n" + content
            
            with open(yaml_file, 'w') as f:
                f.write(content)
            
            print(f"✅ Updated {yaml_file}")
            
        except Exception as e:
            print(f"❌ Error updating {yaml_file}: {e}")
            success = False
    
    return success

def update_env_file(api_key, api_secret, ip_address):
    """Update the .env file with new values, always set SERVER_PORT=5000"""
    env_file = Path(".env")
    
    if not env_file.exists():
        print("Error: .env file not found")
        return False
    
    try:
        # Read current .env file
        with open(env_file, 'r') as f:
            content = f.read()
        
        # Update API Key
        if 'LIVEKIT_API_KEY=' in content:
            content = re.sub(r'LIVEKIT_API_KEY=.*', f'LIVEKIT_API_KEY={api_key}', content)
        else:
            content += f'\nLIVEKIT_API_KEY={api_key}'
        
        # Update API Secret
        if 'LIVEKIT_API_SECRET=' in content:
            content = re.sub(r'LIVEKIT_API_SECRET=.*', f'LIVEKIT_API_SECRET={api_secret}', content)
        else:
            content += f'\nLIVEKIT_API_SECRET={api_secret}'
        
        # Update LIVEKIT_URL with new IP address
        if 'LIVEKIT_URL=' in content:
            # Extract current URL and update IP
            url_match = re.search(r'LIVEKIT_URL=(.+)', content)
            if url_match:
                current_url = url_match.group(1)
                # Replace IP address in URL
                new_url = re.sub(r'ws://\d+\.\d+\.\d+\.\d+', f'ws://{ip_address}', current_url)
                content = re.sub(r'LIVEKIT_URL=.*', f'LIVEKIT_URL={new_url}', content)
        else:
            content += f'\nLIVEKIT_URL=ws://{ip_address}:7880'
        
        # Always set SERVER_PORT=5000
        if 'SERVER_PORT=' in content:
            content = re.sub(r'SERVER_PORT=.*', 'SERVER_PORT=5000', content)
        else:
            content += '\nSERVER_PORT=5000'
        
        # Write updated content back to .env file
        with open(env_file, 'w') as f:
            f.write(content)
        
        print(f"✅ Updated .env file with new API credentials and IP address: {ip_address} and SERVER_PORT=5000")
        return True
        
    except Exception as e:
        print(f"Error updating .env file: {e}")
        return False

def get_livekit_token(api_key, api_secret, ip_address):
    """Run server.py, get token from its API, and update LIVEKIT_TOKEN in .env"""
    print("🔄 Starting server.py to get LiveKit token...")
    server_process = None
    try:
        # Start server.py in background
        server_process = subprocess.Popen([sys.executable, "server.py"], 
                                        stdout=subprocess.DEVNULL, 
                                        stderr=subprocess.DEVNULL)
        # Wait for server to start
        print("⏳ Waiting for server to start...")
        time.sleep(8)
        # Always use port 5000
        server_port = 5000
        print(f"✅ Server should be running on port {server_port}")
        # Try to get token with multiple attempts
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                print(f"🔄 Attempt {attempt + 1}/{max_attempts} to get token...")
                response = requests.get(f"http://localhost:{server_port}/getToken", 
                                      timeout=15)
                response.raise_for_status()
                token = response.text.strip()
                print(f"✅ Got LiveKit token: {token[:20]}...")
                # Update .env file with the token
                env_file = Path(".env")
                if env_file.exists():
                    with open(env_file, 'r') as f:
                        content = f.read()
                    # Update LIVEKIT_TOKEN
                    if 'LIVEKIT_TOKEN=' in content:
                        content = re.sub(r'LIVEKIT_TOKEN=.*', f'LIVEKIT_TOKEN={token}', content)
                    else:
                        content += f'\nLIVEKIT_TOKEN={token}'
                    with open(env_file, 'w') as f:
                        f.write(content)
                    print("✅ Updated .env file with LiveKit token")
                return True
            except requests.exceptions.RequestException as e:
                print(f"⚠️ Attempt {attempt + 1} failed: {e}")
                if attempt < max_attempts - 1:
                    print("⏳ Waiting before retry...")
                    time.sleep(5)
                else:
                    print("❌ All attempts failed to get token from server")
                    return False
    except Exception as e:
        print(f"❌ Error in get_livekit_token: {e}")
        return False
    finally:
        print("🛑 Stopping server.py...")
        if server_process:
            try:
                server_process.terminate()
                try:
                    server_process.wait(timeout=5)
                    print("✅ Server.py stopped gracefully")
                except subprocess.TimeoutExpired:
                    print("⚠️ Server.py didn't stop gracefully, forcing termination...")
                    server_process.kill()
                    try:
                        server_process.wait(timeout=3)
                        print("✅ Server.py forcefully stopped")
                    except subprocess.TimeoutExpired:
                        print("⚠️ Server.py still running after kill")
            except Exception as e:
                print(f"⚠️ Error stopping server.py: {e}")
        # After token is generated, kill all processes on port 5000
        print("🔪 Final cleanup of port 5000 processes...")
        kill_processes_on_ports([5000])
        force_kill_python_servers()
        print("✅ Server cleanup completed")

def run_docker_compose(command):
    """Run docker compose command"""
    try:
        print(f"🔄 Running: docker compose {command}")
        result = subprocess.run(['docker', 'compose'] + command.split(), 
                              check=True, capture_output=True, text=True)
        print(f"✅ Docker compose {command} completed successfully")
        if result.stdout.strip():
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running docker compose {command}: {e}")
        if e.stderr:
            print(f"Error output: {e.stderr}")
        return False

def main():
    print("🚀 Starting automation script...")
    
    # Step 1: Get IPv4 address
    print("📡 Getting IPv4 address...")
    ip_address = get_ipv4_address()
    if not ip_address:
        print("❌ Failed to get IPv4 address")
        return
    
    print(f"📍 Current IPv4 address: {ip_address}")
    
    # Step 2: Run key.py to get API credentials
    print("🔑 Running key.py to get API credentials...")
    api_key, api_secret = run_key_script()
    if not api_key or not api_secret:
        print("❌ Failed to get API credentials")
        return
    
    print(f"✅ Got API Key: {api_key[:8]}...")
    print(f"✅ Got API Secret: {api_secret[:8]}...")
    
    # Step 3: Update YAML files with hardcoded credentials
    print("📝 Updating YAML files with hardcoded credentials...")
    if not update_yaml_files(api_key, api_secret, ip_address):
        print("❌ Failed to update YAML files")
        return
    
    # Step 4: Update .env file
    print("📝 Updating .env file...")
    if not update_env_file(api_key, api_secret, ip_address):
        print("❌ Failed to update .env file")
        return
    
    # Step 5: Get LiveKit token from server.py (before killing server)
    print("🔑 Getting LiveKit token from server.py...")
    if not get_livekit_token(api_key, api_secret, ip_address):
        print("❌ Failed to get LiveKit token")
        return
    
    # Step 6: Docker compose down
    print("⬇️  Stopping Docker containers...")
    if not run_docker_compose("down"):
        print("❌ Failed to stop Docker containers")
        return
    
    # Step 7: Docker compose up -d
    print("⬆️  Starting Docker containers...")
    if not run_docker_compose("up -d"):
        print("❌ Failed to start Docker containers")
        return

    # # Step 8: Ensure webhook_listener.py is running
    # print("🔍 Checking for existing webhook_listener.py processes on port 5005...")
    # # Kill any process using port 5005 (webhook_listener)
    # kill_processes_on_ports([5005])
    # time.sleep(1)
    # print("🚦 Starting webhook_listener.py...")
    # subprocess.Popen([sys.executable, "webhook_listener.py"],
    #                  stdout=subprocess.DEVNULL,
    #                  stderr=subprocess.DEVNULL)
    # print("✅ webhook_listener.py started on port 5005!")

    print("🎉 Automation completed successfully!")
    print(f"🌐 LiveKit URL: ws://{ip_address}:7880")

if __name__ == "__main__":
    main()