import json
import os
import subprocess
import time

import requests


def check_server_performance():
    """Check various aspects of server performance"""

    print("🔍 LLAMA-SERVER PERFORMANCE DIAGNOSTICS")
    print("=" * 50)

    # 1. Check if server is running
    print("\n1️⃣ Server Status Check")
    try:
        response = requests.get("http://127.0.0.1:8081/health", timeout=5)
        print(f"✅ Server responding: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"❌ Server not responding: {e}")
        return

    # 2. Check model info
    print("\n2️⃣ Model Information")
    try:
        response = requests.get("http://127.0.0.1:8081/v1/models", timeout=10)
        if response.status_code == 200:
            models = response.json()
            print(f"📋 Models: {json.dumps(models, indent=2)}")
        else:
            print(f"⚠️ Model info not available: {response.status_code}")
    except Exception as e:
        print(f"⚠️ Could not get model info: {e}")

    # 3. System resources
    print("\n3️⃣ System Resources")
    print(f"💾 CPU count: {os.cpu_count()}")

    # Check memory from /proc/meminfo
    try:
        with open("/proc/meminfo", "r") as f:
            meminfo = f.read()
        for line in meminfo.split("\n"):
            if line.startswith("MemTotal:"):
                total_kb = int(line.split()[1])
                print(f"💾 Memory: {total_kb / (1024**2):.1f} GB total")
            elif line.startswith("MemAvailable:"):
                available_kb = int(line.split()[1])
                print(f"💾 Memory available: {available_kb / (1024**2):.1f} GB")
    except Exception:
        print("💾 Memory info not available")

    # 4. Check for GPU
    print("\n4️⃣ GPU Check")
    try:
        result = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total,memory.used", "--format=csv,nounits,noheader"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            gpu_info = result.stdout.strip().split("\n")
            for i, gpu in enumerate(gpu_info):
                name, total, used = gpu.split(", ")
                print(f"🎮 GPU {i}: {name}")
                print(f"   VRAM: {used}MB / {total}MB used")
        else:
            print("🤷 No NVIDIA GPUs detected")
    except Exception:
        print("🤷 Could not check GPU status")

    # 5. Check llama-server process
    print("\n5️⃣ Process Information")
    try:
        result = subprocess.run(["pgrep", "-f", "llama-server"], capture_output=True, text=True)
        if result.returncode == 0:
            pids = result.stdout.strip().split("\n")
            for pid in pids:
                if pid:
                    print(f"🔄 llama-server process found (PID: {pid})")
        else:
            print("⚠️ No llama-server process found")
    except Exception:
        print("⚠️ Could not check processes")

    # 6. Simple text completion benchmark
    print("\n6️⃣ Performance Benchmark")
    try:
        print("Testing simple text completion...")
        start_time = time.time()

        response = requests.post("http://127.0.0.1:8081/v1/chat/completions", json={"model": "ultravox", "messages": [{"role": "user", "content": "Hello, please respond with exactly: 'Test successful'"}], "max_tokens": 10, "temperature": 0}, timeout=30)

        end_time = time.time()
        processing_time = end_time - start_time

        if response.status_code == 200:
            result = response.json()
            print(f"✅ Text completion: {processing_time:.2f}s")
            print(f"Response: {result.get('choices', [{}])[0].get('message', {}).get('content', 'No content')}")

            # Check if response includes timing info
            if "usage" in result:
                usage = result["usage"]
                print(f"📊 Tokens: {usage.get('total_tokens', 'N/A')}")

        else:
            print(f"❌ Text completion failed: {response.status_code}")
            print(f"Response: {response.text[:200]}")

    except Exception as e:
        print(f"❌ Benchmark failed: {e}")


if __name__ == "__main__":
    check_server_performance()
