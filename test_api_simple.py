#!/usr/bin/env python3
"""
Simplified test of the PortableAI API flow
"""

import json
import urllib.request
import time

BASE_URL = "http://127.0.0.1:8080"

def test_message(content):
    """Send a message and get response"""
    request_body = {
        "messages": [{"role": "user", "content": content}],
        "stream": False,  # Simpler - non-streaming
        "temperature": 0.1,
        "max_tokens": 100,
    }
    
    data = json.dumps(request_body).encode()
    req = urllib.request.Request(
        f"{BASE_URL}/v1/chat/completions",
        data=data,
        headers={"Content-Type": "application/json"}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            response_data = json.loads(resp.read().decode())
            return response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
    except Exception as e:
        return f"ERROR: {e}"

# Test sequence
messages = [
    "Hello, introduce yourself in one short sentence.",
    "Write a Python function that adds two numbers and explain it briefly.",
    "What model are you using?"
]

print("PortableAI - Simplified API Test")
print("=" * 60)

for i, msg in enumerate(messages, 1):
    print(f"\nTest {i}: {msg[:60]}")
    print("-" * 60)
    response = test_message(msg)
    print(f"Response ({len(response)} chars): {response[:200]}...")
    if "ERROR" in response:
        print("✗ FAILED")
    else:
        print("✓ PASSED")
    time.sleep(2)

print("\n" + "=" * 60)
print("Test sequence complete")
