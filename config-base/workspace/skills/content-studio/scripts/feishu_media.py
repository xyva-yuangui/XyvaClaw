#!/usr/bin/env python3
"""
飞书媒体发送模块 — 支持上传图片/视频/文件并发送到飞书对话 (群聊/私聊)

飞书 Open API:
  - 上传图片: POST /im/v1/images  → image_key
  - 上传文件: POST /im/v1/files   → file_key
  - 发送消息: POST /im/v1/messages → msg_id
  - 支持 receive_id_type: open_id (私聊) / chat_id (群聊)
"""

import json
import mimetypes
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path


def _get_openclaw_feishu_config():
    """从 openclaw.json 读取飞书配置"""
    oc_cfg_path = Path.home() / ".openclaw" / "openclaw.json"
    if not oc_cfg_path.exists():
        return {}
    with open(oc_cfg_path) as f:
        return json.load(f).get("channels", {}).get("feishu", {})


def get_tenant_token(app_id=None, app_secret=None):
    """获取飞书 tenant_access_token"""
    if not app_id or not app_secret:
        feishu_cfg = _get_openclaw_feishu_config()
        app_id = app_id or feishu_cfg.get("appId", "")
        app_secret = app_secret or feishu_cfg.get("appSecret", "")

    if not app_id or not app_secret:
        return None

    payload = json.dumps({"app_id": app_id, "app_secret": app_secret}).encode()
    req = urllib.request.Request(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        data=payload, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            if data.get("code") == 0:
                return data["tenant_access_token"]
    except Exception as e:
        print(f"  ⚠️  获取飞书token失败: {e}", file=sys.stderr)
    return None


def upload_image(file_path, token=None):
    """上传图片到飞书, 返回 image_key

    POST https://open.feishu.cn/open-apis/im/v1/images
    Content-Type: multipart/form-data
    Fields: image_type=message, image=<file>
    """
    token = token or get_tenant_token()
    if not token:
        return {"ok": False, "error": "无飞书token"}

    file_path = Path(file_path)
    if not file_path.exists():
        return {"ok": False, "error": f"文件不存在: {file_path}"}

    boundary = "----FeishuUploadBoundary9527"
    mime_type = mimetypes.guess_type(str(file_path))[0] or "image/png"
    file_data = file_path.read_bytes()
    filename = file_path.name

    body = bytearray()
    # image_type field
    body += f"--{boundary}\r\n".encode()
    body += b'Content-Disposition: form-data; name="image_type"\r\n\r\n'
    body += b"message\r\n"
    # image file field
    body += f"--{boundary}\r\n".encode()
    body += f'Content-Disposition: form-data; name="image"; filename="{filename}"\r\n'.encode()
    body += f"Content-Type: {mime_type}\r\n\r\n".encode()
    body += file_data
    body += b"\r\n"
    body += f"--{boundary}--\r\n".encode()

    req = urllib.request.Request(
        "https://open.feishu.cn/open-apis/im/v1/images",
        data=bytes(body),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read())
            if result.get("code") == 0:
                image_key = result.get("data", {}).get("image_key", "")
                return {"ok": True, "image_key": image_key}
            return {"ok": False, "error": f"飞书API: code={result.get('code')} msg={result.get('msg', '?')}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def upload_file(file_path, file_type="stream", token=None):
    """上传文件到飞书, 返回 file_key

    POST https://open.feishu.cn/open-apis/im/v1/files
    Content-Type: multipart/form-data
    Fields: file_type=stream|mp4|pdf|doc|xls|ppt, file_name=xxx, file=<file>

    视频用 file_type="mp4"
    """
    token = token or get_tenant_token()
    if not token:
        return {"ok": False, "error": "无飞书token"}

    file_path = Path(file_path)
    if not file_path.exists():
        return {"ok": False, "error": f"文件不存在: {file_path}"}

    # 自动推断file_type (注意: mp4用stream上传, 否则飞书要求msg_type=media)
    ext = file_path.suffix.lower()
    if file_type == "stream":
        type_map = {
            ".pdf": "pdf", ".doc": "doc", ".docx": "doc",
            ".xls": "xls", ".xlsx": "xls", ".ppt": "ppt", ".pptx": "ppt",
        }
        file_type = type_map.get(ext, "stream")

    boundary = "----FeishuUploadBoundary7788"
    mime_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
    file_data = file_path.read_bytes()
    filename = file_path.name

    body = bytearray()
    # file_type field
    body += f"--{boundary}\r\n".encode()
    body += b'Content-Disposition: form-data; name="file_type"\r\n\r\n'
    body += f"{file_type}\r\n".encode()
    # file_name field
    body += f"--{boundary}\r\n".encode()
    body += b'Content-Disposition: form-data; name="file_name"\r\n\r\n'
    body += f"{filename}\r\n".encode()
    # file field
    body += f"--{boundary}\r\n".encode()
    body += f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode()
    body += f"Content-Type: {mime_type}\r\n\r\n".encode()
    body += file_data
    body += b"\r\n"
    body += f"--{boundary}--\r\n".encode()

    req = urllib.request.Request(
        "https://open.feishu.cn/open-apis/im/v1/files",
        data=bytes(body),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read())
            if result.get("code") == 0:
                file_key = result.get("data", {}).get("file_key", "")
                return {"ok": True, "file_key": file_key}
            return {"ok": False, "error": f"飞书API: code={result.get('code')} msg={result.get('msg', '?')}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def send_text(text, receive_id=None, receive_id_type=None, token=None):
    """发送文本消息到飞书"""
    token = token or get_tenant_token()
    receive_id, receive_id_type = _resolve_target(receive_id, receive_id_type)

    if not token or not receive_id:
        return {"ok": False, "error": "无token或目标"}

    return _send_message(
        msg_type="text",
        content=json.dumps({"text": text}),
        receive_id=receive_id,
        receive_id_type=receive_id_type,
        token=token,
    )


def send_image(image_key=None, file_path=None, receive_id=None,
               receive_id_type=None, token=None):
    """发送图片消息到飞书 (直接image_key或上传后发送)"""
    token = token or get_tenant_token()
    receive_id, receive_id_type = _resolve_target(receive_id, receive_id_type)

    if not token or not receive_id:
        return {"ok": False, "error": "无token或目标"}

    # 需要先上传
    if not image_key and file_path:
        upload_result = upload_image(file_path, token)
        if not upload_result["ok"]:
            return upload_result
        image_key = upload_result["image_key"]

    if not image_key:
        return {"ok": False, "error": "无image_key"}

    return _send_message(
        msg_type="image",
        content=json.dumps({"image_key": image_key}),
        receive_id=receive_id,
        receive_id_type=receive_id_type,
        token=token,
    )


def send_file(file_key=None, file_path=None, receive_id=None,
              receive_id_type=None, token=None):
    """发送文件消息到飞书 (直接file_key或上传后发送)"""
    token = token or get_tenant_token()
    receive_id, receive_id_type = _resolve_target(receive_id, receive_id_type)

    if not token or not receive_id:
        return {"ok": False, "error": "无token或目标"}

    # 需要先上传
    if not file_key and file_path:
        upload_result = upload_file(file_path, file_type="stream", token=token)
        if not upload_result["ok"]:
            return upload_result
        file_key = upload_result["file_key"]

    if not file_key:
        return {"ok": False, "error": "无file_key"}

    return _send_message(
        msg_type="file",
        content=json.dumps({"file_key": file_key}),
        receive_id=receive_id,
        receive_id_type=receive_id_type,
        token=token,
    )


def send_video(file_path, cover_path=None, receive_id=None,
               receive_id_type=None, token=None):
    """发送视频消息到飞书 (内联播放, 需上传视频+封面图)

    如果无封面图, 退化为文件消息发送。
    """
    token = token or get_tenant_token()
    receive_id, receive_id_type = _resolve_target(receive_id, receive_id_type)

    if not token or not receive_id:
        return {"ok": False, "error": "无token或目标"}

    fp = Path(file_path)
    if not fp.exists():
        return {"ok": False, "error": f"文件不存在: {file_path}"}

    # 如有封面图: 走 media 消息 (视频内联播放)
    if cover_path and Path(cover_path).exists():
        # 上传视频 (file_type=mp4)
        vid_result = upload_file(str(fp), file_type="mp4", token=token)
        if not vid_result["ok"]:
            return vid_result
        # 上传封面图
        img_result = upload_image(cover_path, token=token)
        if not img_result["ok"]:
            return img_result

        return _send_message(
            msg_type="media",
            content=json.dumps({
                "file_key": vid_result["file_key"],
                "image_key": img_result["image_key"],
            }),
            receive_id=receive_id,
            receive_id_type=receive_id_type,
            token=token,
        )

    # 无封面图: 退化为文件消息
    return send_file(file_path=str(fp), receive_id=receive_id,
                    receive_id_type=receive_id_type, token=token)


def send_media_with_text(text, file_path=None, receive_id=None,
                         receive_id_type=None, token=None):
    """发送文本+媒体文件 (根据文件类型自动选择上传方式)

    图片文件: 先发图片消息, 再发文本说明
    视频/其他文件: 先发文件消息, 再发文本说明
    """
    token = token or get_tenant_token()
    receive_id, receive_id_type = _resolve_target(receive_id, receive_id_type)

    if not token or not receive_id:
        return {"ok": False, "error": "无token或目标"}

    results = []

    # 发送文件/图片
    if file_path:
        fp = Path(file_path)
        ext = fp.suffix.lower()
        is_image = ext in (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp")

        if is_image:
            print(f"  📤 上传图片到飞书: {fp.name}")
            r = send_image(file_path=str(fp), receive_id=receive_id,
                          receive_id_type=receive_id_type, token=token)
            results.append(("image", r))
        else:
            print(f"  📤 上传文件到飞书: {fp.name}")
            r = send_file(file_path=str(fp), receive_id=receive_id,
                         receive_id_type=receive_id_type, token=token)
            results.append(("file", r))

    # 发送文本说明
    if text:
        r = send_text(text, receive_id=receive_id,
                     receive_id_type=receive_id_type, token=token)
        results.append(("text", r))

    ok = all(r[1].get("ok") for r in results)
    errors = [f"{r[0]}: {r[1].get('error')}" for r in results if not r[1].get("ok")]
    return {"ok": ok, "results": results, "errors": errors if errors else None}


# ── 内部辅助 ──

def _resolve_target(receive_id=None, receive_id_type=None):
    """解析接收目标 (支持 open_id / chat_id)"""
    if receive_id:
        if not receive_id_type:
            # 自动推断: oc_ 开头为群聊 chat_id, ou_ 开头为 open_id
            if receive_id.startswith("oc_"):
                receive_id_type = "chat_id"
            else:
                receive_id_type = "open_id"
        return receive_id, receive_id_type

    # 从 openclaw.json 读取默认目标
    feishu_cfg = _get_openclaw_feishu_config()
    target = feishu_cfg.get("proactivePushTarget", "")
    target_type = feishu_cfg.get("proactivePushTargetType", "open_id")
    return target, target_type


def _send_message(msg_type, content, receive_id, receive_id_type, token):
    """飞书发送消息通用方法"""
    payload = json.dumps({
        "receive_id": receive_id,
        "msg_type": msg_type,
        "content": content,
    }).encode("utf-8")

    req = urllib.request.Request(
        f"https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type={receive_id_type}",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read())
            if result.get("code") == 0:
                msg_id = result.get("data", {}).get("message_id", "")
                target_desc = f"{'群聊' if receive_id_type == 'chat_id' else '私聊'} {receive_id[:20]}..."
                print(f"  ✅ 飞书{msg_type}消息已发送 → {target_desc}")
                return {"ok": True, "message_id": msg_id}
            return {"ok": False, "error": f"code={result.get('code')} msg={result.get('msg', '?')}"}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:300]
        return {"ok": False, "error": f"HTTP {e.code}: {body}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ── CLI ──

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="飞书媒体发送工具")
    parser.add_argument("--text", "-t", help="文本消息")
    parser.add_argument("--image", "-i", help="图片文件路径")
    parser.add_argument("--file", "-f", help="文件路径 (视频/文档等)")
    parser.add_argument("--target", help="接收者ID (open_id/chat_id)")
    parser.add_argument("--target-type", choices=["open_id", "chat_id"])
    parser.add_argument("--test", action="store_true", help="发送测试消息")

    args = parser.parse_args()

    if args.test:
        r = send_text("🧪 Content Studio 飞书发送测试 — 媒体直发模块就绪",
                      receive_id=args.target, receive_id_type=args.target_type)
        print(json.dumps(r, ensure_ascii=False, indent=2))
    elif args.image:
        r = send_image(file_path=args.image, receive_id=args.target,
                      receive_id_type=args.target_type)
        print(json.dumps(r, ensure_ascii=False, indent=2))
    elif args.file:
        r = send_file(file_path=args.file, receive_id=args.target,
                     receive_id_type=args.target_type)
        print(json.dumps(r, ensure_ascii=False, indent=2))
    elif args.text:
        r = send_text(args.text, receive_id=args.target,
                     receive_id_type=args.target_type)
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        parser.print_help()
