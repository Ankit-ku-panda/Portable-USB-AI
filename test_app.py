#!/usr/bin/env python3
"""
Test script for PortableAI send and delete functionality
Run with: python3 test_send_delete.py
"""

import urllib.request
import json
import time
import sys

BASE_URL = "http://127.0.0.1:9000"

def test_health():
    print("=" * 60)
    print("TEST 1: Health Check")
    print("=" * 60)
    try:
        response = urllib.request.urlopen(f"{BASE_URL}/health")
        print(f"✓ Health check passed (HTTP {response.status})")
        return True
    except Exception as e:
        print(f"✗ Health check failed: {e}")
        return False

def test_send_message(msg_text="Hello, test message"):
    print("\n" + "=" * 60)
    print(f"TEST 2: Send Message - '{msg_text}'")
    print("=" * 60)
    try:
        request_body = {
            "messages": [
                {"role": "user", "content": msg_text}
            ],
            "temperature": 0.1,
            "max_tokens": 256,
            "stream": True
        }
        
        req = urllib.request.Request(
            f"{BASE_URL}/v1/chat/completions",
            data=json.dumps(request_body).encode(),
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Sending: {json.dumps(request_body, indent=2)}")
        
        response = urllib.request.urlopen(req, timeout=300)
        print(f"✓ Send message succeeded (HTTP {response.status})")
        
        # Read response stream
        print("\nResponse stream:")
        tokens_received = 0
        for line in response:
            line_text = line.decode('utf-8').strip()
            if line_text.startswith("data: "):
                try:
                    data = json.loads(line_text[6:])
                    if "choices" in data and data["choices"]:
                        content = data["choices"][0].get("delta", {}).get("content", "")
                        if content:
                            print(content, end="", flush=True)
                            tokens_received += 1
                except:
                    pass
        print(f"\n✓ Received {tokens_received} tokens")
        return True
        
    except Exception as e:
        print(f"✗ Send message failed: {e}")
        return False

def test_get_chats():
    print("\n" + "=" * 60)
    print("TEST 3: Get Chat List")
    print("=" * 60)
    try:
        response = urllib.request.urlopen(f"{BASE_URL}/api/chats")
        chats = json.loads(response.read().decode())
        print(f"✓ Got {len(chats)} chats")
        for chat in chats[:3]:
            print(f"  - {chat.get('title', 'Untitled')}")
        return chats
    except Exception as e:
        print(f"✗ Get chats failed: {e}")
        return []

def test_delete_chat(chat_id):
    print("\n" + "=" * 60)
    print(f"TEST 4: Delete Chat - {chat_id}")
    print("=" * 60)
    try:
        req = urllib.request.Request(
            f"{BASE_URL}/api/chat/{chat_id}",
            method="DELETE"
        )
        response = urllib.request.urlopen(req)
        print(f"✓ Delete succeeded (HTTP {response.status})")
        return True
    except urllib.error.HTTPError as e:
        print(f"✗ Delete failed (HTTP {e.code}): {e.read().decode()}")
        return False
    except Exception as e:
        print(f"✗ Delete failed: {e}")
        return False

def main():
    print("\n")
    print("[" + "=" * 58 + "]")
    print(" " * 10 + "PORTABLEAI - SEND & DELETE TEST")
    print("[" + "=" * 58 + "]")
    print()
    
    # Run tests
    if not test_health():
        print("\n✗ Cannot connect to server. Is it running?")
        sys.exit(1)
    
    test_send_message("What is 2+2?")
    
    chats = test_get_chats()
    
    # Try to delete first chat if it exists
    if chats:
        first_chat_id = chats[0].get('id')
        if first_chat_id:
            test_delete_chat(first_chat_id)
    
    print("\n" + "=" * 60)
    print("✓ ALL TESTS COMPLETED")
    print("=" * 60)

if __name__ == "__main__":
    main()
