import subprocess
import json
import sys
import threading
import time
import os

# GitHub Personal Access Token을 환경 변수에서 읽기
token = os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN", "")
if not token:
    print("ERROR: GITHUB_PERSONAL_ACCESS_TOKEN 환경 변수가 설정되지 않았습니다.")
    sys.exit(1)

# MCP 서버 프로세스 시작
proc = subprocess.Popen(
    ["docker", "run", "-i", "--rm",
     "-e", f"GITHUB_PERSONAL_ACCESS_TOKEN={token}",
     "ghcr.io/github/github-mcp-server", "stdio"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

def read_output(stream, label):
    for line in stream:
        print(f"[{label}] {line.strip()}")

# stderr 리더 스레드
threading.Thread(target=read_output, args=(proc.stderr, "STDERR"), daemon=True).start()

# initialize 요청 전송
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

print("Sending initialize request...")
proc.stdin.write(json.dumps(init_request) + "\n")
proc.stdin.flush()

# 응답 읽기 (타임아웃 10초)
import select
import os

end_time = time.time() + 10
response_lines = []
while time.time() < end_time:
    line = proc.stdout.readline()
    if not line:
        break
    response_lines.append(line.strip())
    print(f"[STDOUT] {line.strip()}")
    # initialize 응답을 받으면 계속 진행
    if any('result' in l for l in response_lines):
        break

if response_lines:
    print("\n=== SUCCESS: MCP Server 응답 수신 ===")
    print(response_lines[0])
else:
    print("\n=== FAILED: 응답 없음 ===")
    # 프로세스 종료
    proc.stdin.close()
    proc.wait(timeout=5)
    sys.exit(1)

# tools/list 요청 전송
tools_request = {
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/list",
    "params": {}
}

print("\nSending tools/list request...")
proc.stdin.write(json.dumps(tools_request) + "\n")
proc.stdin.flush()

end_time = time.time() + 10
tool_lines = []
while time.time() < end_time:
    line = proc.stdout.readline()
    if not line:
        break
    tool_lines.append(line.strip())
    if 'result' in line:
        break

if tool_lines:
    print("=== TOOLS LIST RESPONSE ===")
    # 응답 크기를 제한해서 출력
    response = tool_lines[-1]
    try:
        data = json.loads(response)
        tools = data.get("result", {}).get("tools", [])
        print(f"Total tools available: {len(tools)}")
        # 처음 5개 도구 이름 출력
        for t in tools[:5]:
            print(f"  - {t['name']}: {t.get('description', '')[:60]}")
    except json.JSONDecodeError:
        print(response[:2000])
else:
    print("=== FAILED: tools/list 응답 없음 ===")

# 프로세스 종료
proc.stdin.close()
try:
    proc.wait(timeout=5)
except:
    proc.kill()

print("\n=== TEST COMPLETE ===")