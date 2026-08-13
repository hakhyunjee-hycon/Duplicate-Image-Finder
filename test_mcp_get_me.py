import subprocess
import json
import threading
import time
import os

# GitHub Personal Access Token을 환경 변수에서 읽기
token = os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN", "")
if not token:
    print("ERROR: GITHUB_PERSONAL_ACCESS_TOKEN 환경 변수가 설정되지 않았습니다.")
    exit(1)

# 환경 변수 설정
env = dict(os.environ)
env["GITHUB_PERSONAL_ACCESS_TOKEN"] = token

# Docker run -e GITHUB_PERSONAL_ACCESS_TOKEN: 호스트 환경 변수를 Docker에 전달
proc = subprocess.Popen(
    ["docker", "run", "-i", "--rm",
     "-e", "GITHUB_PERSONAL_ACCESS_TOKEN",
     "ghcr.io/github/github-mcp-server", "stdio"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    env=env
)

def read_stderr():
    for line in proc.stderr:
        print(f"[STDERR] {line.strip()}")

threading.Thread(target=read_stderr, daemon=True).start()

# 1. initialize 요청
init_request = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "test-client", "version": "1.0.0"}
    }
}

print("1. Sending initialize request...")
proc.stdin.write(json.dumps(init_request) + "\n")
proc.stdin.flush()

# 응답 읽기
end_time = time.time() + 15
init_response = None
while time.time() < end_time:
    line = proc.stdout.readline()
    if not line:
        break
    print(f"[STDOUT] {line.strip()[:100]}...")
    try:
        data = json.loads(line)
        if data.get("id") == 1:
            init_response = data
            print("  -> Initialize SUCCESS")
            break
    except json.JSONDecodeError:
        continue

if not init_response:
    print("  -> Initialize FAILED")
    proc.kill()
    exit(1)

# 2. initialized 알림
notif = {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}
proc.stdin.write(json.dumps(notif) + "\n")
proc.stdin.flush()

# 3. tools/call get_me 요청
call_request = {
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
        "name": "get_me",
        "arguments": {}
    }
}

print("\n2. Calling get_me tool...")
proc.stdin.write(json.dumps(call_request) + "\n")
proc.stdin.flush()

# 응답 읽기
end_time = time.time() + 15
call_response = None
while time.time() < end_time:
    line = proc.stdout.readline()
    if not line:
        break
    try:
        data = json.loads(line)
        if data.get("id") == 2:
            call_response = data
            break
    except json.JSONDecodeError:
        continue

if call_response:
    if "result" in call_response:
        result = call_response["result"]
        content = result.get("content", [])
        for item in content:
            if item.get("type") == "text":
                print("\n=== get_me RESULT ===")
                text = item["text"]
                try:
                    user_data = json.loads(text)
                    print(f"  Login: {user_data.get('login')}")
                    print(f"  Name: {user_data.get('name')}")
                    print(f"  ID: {user_data.get('id')}")
                    print(f"  Followers: {user_data.get('followers')}")
                except json.JSONDecodeError:
                    print(text[:500])
                break
        print("\n=== SUCCESS: PAT 인증 확인됨 ===")
    elif "error" in call_response:
        error = call_response["error"]
        print(f"\n=== ERROR: {error.get('message', error)} ===")
else:
    print("\n=== FAILED: get_me 응답 없음 ===")

# 프로세스 종료
proc.stdin.close()
try:
    proc.wait(timeout=5)
except:
    proc.kill()

print("\n=== TEST COMPLETE ===")