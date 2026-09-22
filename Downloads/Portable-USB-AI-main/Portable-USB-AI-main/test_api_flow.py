#!/usr/bin/env python3
"""
Test the complete PortableAI API flow with 3 sequential messages
"""

import json
import urllib.request
import urllib.error
import time
import sys

BASE_URL = "http://127.0.0.1:8080"
COMPLETION_URL = f"{BASE_URL}/v1/chat/completions"
HEALTH_URL = f"{BASE_URL}/health"

def check_health():
    """Check if server is healthy"""
    try:
        with urllib.request.urlopen(HEALTH_URL, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            print(f"✓ Health check passed: {data}")
            return True
    except Exception as e:
        print(f"✗ Health check failed: {e}")
        return False

def send_message(content, message_num):
    """Send a single message and capture full response"""
    print(f"\n{'='*60}")
    print(f"TEST {message_num}: {content}")
    print('='*60)
    
    request_body = {
        "messages": [
            {"role": "user", "content": content}
        ],
        "stream": True,
        "temperature": 0.1,
        "max_tokens": 256,
    }
    
    data = json.dumps(request_body).encode()
    req = urllib.request.Request(
        COMPLETION_URL,
        data=data,
        headers={"Content-Type": "application/json"}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            print(f"Status: {resp.status}")
            
            full_response = ""
            line_count = 0
            
            for line in resp:
                line = line.decode()
                line_count += 1
                
                if line.startswith("data: "):
                    try:
                        chunk = json.loads(line[6:])
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        
                        # Extract content from either 'content' or 'reasoning_content'
                        content = delta.get("content")
                        if content is None:
                            content = delta.get("reasoning_content", "")
                        
                        if content:
                            full_response += content
                            print(content, end="", flush=True)
                        
                        # Check for finish reason
                        finish_reason = chunk.get("choices", [{}])[0].get("finish_reason")
                        if finish_reason:
                            print(f"\n\n[Finished: {finish_reason}]")
                            
                    except json.JSONDecodeError:
                        pass
            
            print(f"\nTotal lines: {line_count}")
            print(f"Total response length: {len(full_response)} chars")
            
            if full_response:
                print("✓ Message successful")
                return True
            else:
                print("✗ No response received")
                return False
                
    except urllib.error.HTTPError as e:
        print(f"✗ HTTP Error {e.code}: {e.reason}")
        print(f"Body: {e.read().decode()}")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run complete test sequence"""
    print("PortableAI - API Flow Test")
    print("="*60)
    
    # Check health first
    if not check_health():
        print("\n✗ Server is not healthy. Exiting.")
        sys.exit(1)
    
    time.sleep(1)
    
    # Test messages
    messages = [
        "Hello, introduce yourself in one short sentence.",
        "Write a Python function that adds two numbers and explain it briefly.",
        "What model are you using?"
    ]
    
    results = []
    
    for i, msg in enumerate(messages, 1):
        time.sleep(2)  # Small delay between messages
        success = send_message(msg, i)
        results.append((msg, success))
    
    # Summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print('='*60)
    
    for msg, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status}: {msg[:50]}")
    
    all_passed = all(success for _, success in results)
    print(f"\nOverall: {'✓ ALL TESTS PASSED' if all_passed else '✗ SOME TESTS FAILED'}")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
