#!/usr/bin/env python3
"""
调试版发布脚本 - 详细日志 + 多次重试
"""

import json
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

import requests
import websockets.sync.client as ws_client

CDP_HOST = "127.0.0.1"
CDP_PORT = 9222
XHS_CREATOR_URL = "https://creator.xiaohongshu.com/publish/publish"

class Publisher:
    def __init__(self):
        self.ws = None
        self._msg_id = 0

    def connect(self):
        url = f"http://{CDP_HOST}:{CDP_PORT}/json"
        targets = requests.get(url, timeout=5).json()
        pages = [t for t in targets if t.get("type") == "page"]
        
        ws_url = None
        for t in pages:
            if XHS_CREATOR_URL in t.get("url", ""):
                ws_url = t["webSocketDebuggerUrl"]
                break
        
        if not ws_url and pages:
            ws_url = pages[0]["webSocketDebuggerUrl"]
        
        if not ws_url:
            resp = requests.put(f"http://{CDP_HOST}:{CDP_PORT}/json/new?{XHS_CREATOR_URL}", timeout=5)
            if resp.ok:
                ws_url = resp.json().get("webSocketDebuggerUrl")
        
        print(f"[debug] Connecting to {ws_url}")
        self.ws = ws_client.connect(ws_url)
        print("[debug] Connected")

    def _send(self, method, params=None):
        self._msg_id += 1
        msg = {"id": self._msg_id, "method": method}
        if params:
            msg["params"] = params
        self.ws.send(json.dumps(msg))
        
        while True:
            raw = self.ws.recv()
            data = json.loads(raw)
            if data.get("id") == self._msg_id:
                if "error" in data:
                    raise Exception(f"CDP error: {data['error']}")
                return data.get("result", {})

    def _evaluate(self, expr):
        result = self._send("Runtime.evaluate", {
            "expression": expr,
            "returnByValue": True,
            "awaitPromise": True,
        })
        remote_obj = result.get("result", {})
        if remote_obj.get("subtype") == "error":
            raise Exception(f"JS error: {remote_obj.get('description', remote_obj)}")
        return remote_obj.get("value")

    def _sleep(self, secs):
        time.sleep(secs)

    def publish(self, title, content, image_path):
        # Navigate
        print("[debug] Navigating to publish page...")
        self._send("Page.enable")
        self._send("Page.navigate", {"url": XHS_CREATOR_URL})
        self._sleep(3)
        
        # Click tab
        print("[debug] Clicking '上传图文' tab...")
        self._evaluate("""
            (function() {
                var tabs = document.querySelectorAll('div.creator-tab');
                for (var t of tabs) {
                    if (t.textContent.trim() === '上传图文') {
                        t.click();
                        return true;
                    }
                }
                return false;
            })()
        """)
        self._sleep(2)
        
        # Upload image
        print(f"[debug] Uploading image: {image_path}")
        self._send("DOM.enable")
        doc = self._send("DOM.getDocument")
        root_id = doc["root"]["nodeId"]
        
        node_id = 0
        for selector in ('input.upload-input', 'input[type="file"]'):
            result = self._send("DOM.querySelector", {"nodeId": root_id, "selector": selector})
            node_id = result.get("nodeId", 0)
            if node_id:
                break
        
        if node_id:
            self._send("DOM.setFileInputFiles", {
                "nodeId": node_id,
                "files": [image_path.replace("\\", "/")],
            })
            print("[debug] Image uploaded, waiting 15s...")
            self._sleep(15)
        else:
            raise Exception("Could not find upload input")
        
        # Fill title
        print(f"[debug] Setting title: {title}")
        escaped_title = json.dumps(title)
        self._evaluate(f"""
            (function() {{
                var el = document.querySelector('input[placeholder*="填写标题"]');
                if (!el) return false;
                var nativeSetter = Object.getOwnPropertyDescriptor(
                    window.HTMLInputElement.prototype, 'value'
                ).set;
                el.focus();
                nativeSetter.call(el, {escaped_title});
                el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                return true;
            }})()
        """)
        self._sleep(2)
        
        # Fill content
        print(f"[debug] Setting content ({len(content)} chars)...")
        escaped_content = json.dumps(content)
        self._evaluate(f"""
            (function() {{
                var el = document.querySelector('div.tiptap.ProseMirror');
                if (!el) return false;
                el.focus();
                var text = {escaped_content};
                var paragraphs = text.split('\\\\n').filter(p => p.trim());
                var html = paragraphs.map(p => '<p>' + p + '</p>').join('<p><br></p>');
                el.innerHTML = html;
                el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                return true;
            }})()
        """)
        self._sleep(3)
        
        # Click publish button - FIRST CLICK
        print("[debug] Clicking publish button (1st click)...")
        self._evaluate("""
            (function() {
                var buttons = document.querySelectorAll('button');
                for (var b of buttons) {
                    if (b.textContent.trim() === '发布') {
                        b.click();
                        console.log('[debug] Publish button clicked');
                        return true;
                    }
                }
                return false;
            })()
        """)
        
        # Wait and check for confirmation dialog
        print("[debug] Waiting 5s for dialog...")
        self._sleep(5)
        
        # Check URL after first click
        url = self._evaluate("window.location.href")
        print(f"[debug] URL after 1st click: {url}")
        
        if 'published=true' in url or '/explore/' in url:
            print("[debug] ✅ Published after 1st click!")
            return True
        
        # Look for confirmation dialog and click
        print("[debug] Looking for confirmation dialog...")
        confirm_clicked = self._evaluate("""
            (function() {
                var buttons = document.querySelectorAll('button, .ant-btn, [role="button"]');
                for (var b of buttons) {
                    var text = b.textContent.trim();
                    console.log('[debug] Button found: ' + text);
                    if (text === '发布' || text === '确认发布' || text === '确认') {
                        b.click();
                        console.log('[debug] Confirm button clicked: ' + text);
                        return true;
                    }
                }
                return false;
            })()
        """)
        
        if confirm_clicked:
            print("[debug] Confirmation button clicked")
        else:
            print("[debug] No confirmation button found, clicking publish again...")
            # Second attempt
            self._evaluate("""
                (function() {
                    var buttons = document.querySelectorAll('button');
                    for (var b of buttons) {
                        if (b.textContent.trim() === '发布') {
                            b.click();
                            return true;
                        }
                    }
                    return false;
                })()
            """)
        
        # Wait longer for publish to complete
        print("[debug] Waiting 15s for publish...")
        for i in range(15):
            self._sleep(1)
            try:
                url = self._evaluate("window.location.href")
                if 'published=true' in url or '/explore/' in url or '/user/profile' in url:
                    print(f"[debug] ✅ Published! URL: {url}")
                    return True
                if i % 5 == 4:
                    print(f"[debug] Still waiting... ({i+1}/15)")
            except:
                print("[debug] Connection closed (redirect?)")
                return True
        
        # Final URL check
        url = self._evaluate("window.location.href")
        print(f"[debug] Final URL: {url}")
        
        if 'published=true' in url:
            print("[debug] ✅ Published (URL contains published=true)")
            return True
        
        print("[debug] ❌ Publish may have failed - URL unchanged")
        return False

    def disconnect(self):
        if self.ws:
            self.ws.close()


def main():
    # Read content from draft file
    draft_path = Path.home() / ".openclaw" / "workspace" / "xhs" / "draft-2026-03-08.md"
    with open(draft_path) as f:
        content = f.read()
    
    # Extract title and body
    title = "OpenClaw 使用技巧：7 个让你效率翻倍的功能"
    
    # Find body after "## 正文"
    body_start = content.find("## 正文")
    if body_start > 0:
        body = content[body_start:].split("\n", 1)[1].strip()
    else:
        body = content
    
    # Remove hashtags for content
    body = body.split("#OpenClaw")[0].strip()
    
    image_path = str(Path.home() / ".openclaw" / "output" / "xhs-publisher" / "render_20260308_171216" / "card_1.png")
    
    pub = Publisher()
    try:
        pub.connect()
        success = pub.publish(title, body, image_path)
        if success:
            print("\n✅ SUCCESS")
        else:
            print("\n❌ FAILED - Please check browser manually")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        pub.disconnect()


if __name__ == "__main__":
    main()
