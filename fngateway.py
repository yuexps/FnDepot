#!/usr/bin/env python3
"""
飞牛网关反向代理中间件：https://github.com/yuexps/FnDepot/blob/main/fngateway.py
监听 Unix Domain Socket 并代理至目标 TCP 端口，实现子路径路由剥除、请求/响应头重写及前端运行时环境适配。
"""

import os
import re
import sys
import gzip
import socket
import select
import atexit
import signal
import logging
import argparse
import http.client
import socketserver
from http.server import BaseHTTPRequestHandler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger("fngateway")

HTML_ATTR_RE = re.compile(r'(?i)\b(src|href|action|poster)\s*=\s*(["\'])(/[^"\']*)')
JS_ROUTE_RE = re.compile(
    rb'function\s+([a-zA-Z0-9_$]+)\s*\(\s*([a-zA-Z0-9_$]+)\s*\)\s*\{\s*return\s*/\^\\/([a-zA-Z0-9_-]+)\(\?:\\/\|\$\)/\.test\(\s*\2\s*\)\s*\?\s*([a-zA-Z0-9_$]+)\s*:\s*(?:void 0|undefined)\s*\}'
)
CHUNK_SIZE = 64 * 1024


def generate_bridge_script(prefix: str) -> str:
    """前端运行时拦截与路由适配脚本"""
    return f"""<script>
(function (prefix) {{
  if (typeof window === "undefined" || !window.location || !prefix) return;
  if (window.location.pathname.indexOf(prefix) !== 0 && window.location.pathname !== prefix) return;

  var isAlreadyPrefixed = function (pathname) {{
    return pathname === prefix || pathname.indexOf(prefix + "/") === 0;
  }};

  var toGatewayUrl = function (value) {{
    if (!value) return value;
    var str = String(value).trim();
    if (/^(blob:|data:|javascript:|about:|#)/i.test(str)) return value;
    var url;
    try {{ url = new URL(str, window.location.href); }} catch (_) {{ return value; }}
    if (url.origin !== window.location.origin) return value;
    if (isAlreadyPrefixed(url.pathname)) return value;
    var rawPath = url.pathname.indexOf('/') === 0 ? url.pathname : '/' + url.pathname;
    var newPath = prefix + rawPath;
    if (str.indexOf('/') === 0 && str.indexOf('//') !== 0) {{
      return newPath + (url.search || '') + (url.hash || '');
    }}
    url.pathname = newPath;
    return url.toString();
  }};

  var toGatewaySrcset = function (srcsetStr) {{
    if (!srcsetStr || typeof srcsetStr !== "string") return srcsetStr;
    return srcsetStr.split(",").map(function (part) {{
      var item = part.trim();
      if (!item) return item;
      var segs = item.split(/\\s+/);
      var mapped = toGatewayUrl(segs[0]);
      if (mapped) segs[0] = mapped;
      return segs.join(" ");
    }}).join(", ");
  }};

  var rewriteHtmlString = function (html) {{
    if (typeof html !== "string" || html.indexOf("/") === -1) return html;
    var htmlAttrRe = new RegExp("\\\\b(src|href|action|poster)=([\\"'])(/[^\\"']*)\\\\2", "gi");
    return html.replace(htmlAttrRe, function (match, attr, quote, path) {{
      if (isAlreadyPrefixed(path) || path.indexOf("//") === 0) return match;
      return attr + "=" + quote + prefix + path + quote;
    }});
  }};

  var installBridge = function (targetWindow) {{
    if (!targetWindow || targetWindow.__fnGatewayBridgeReady) return;
    targetWindow.__fnGatewayBridgeReady = true;

    // 拦截 Location 原型（pathname、assign、replace）
    if (targetWindow.Location && targetWindow.Location.prototype) {{
      var locProto = targetWindow.Location.prototype;
      var locPathDesc = Object.getOwnPropertyDescriptor(locProto, "pathname");
      if (locPathDesc && locPathDesc.get && locPathDesc.configurable) {{
        var nativeLocPathGet = locPathDesc.get;
        var nativeLocPathSet = locPathDesc.set;
        try {{
          Object.defineProperty(locProto, "pathname", {{
            get: function () {{
              var p = nativeLocPathGet.call(this);
              if (isAlreadyPrefixed(p)) {{
                var stripped = p.slice(prefix.length);
                return stripped.indexOf("/") === 0 ? stripped : "/" + stripped;
              }}
              return p;
            }},
            set: function (val) {{
              if (nativeLocPathSet) {{
                if (typeof val === "string" && val.indexOf("/") === 0 && !isAlreadyPrefixed(val)) {{
                  val = prefix + val;
                }}
                return nativeLocPathSet.call(this, val);
              }}
            }},
            configurable: true,
            enumerable: true
          }});
        }} catch (_) {{}}
      }}

      if (locProto.assign) {{
        var nativeAssign = locProto.assign;
        locProto.assign = function (url) {{
          return nativeAssign.call(this, toGatewayUrl(url) || url);
        }};
      }}
      if (locProto.replace) {{
        var nativeReplace = locProto.replace;
        locProto.replace = function (url) {{
          return nativeReplace.call(this, toGatewayUrl(url) || url);
        }};
      }}
    }}

    // 拦截 History API
    if (targetWindow.history) {{
      var wrapHistory = function (orig) {{
        if (!orig) return orig;
        return function (state, unused, url) {{
          if (url) url = toGatewayUrl(url);
          return orig.call(this, state, unused, url);
        }};
      }};
      targetWindow.history.pushState = wrapHistory(targetWindow.history.pushState);
      targetWindow.history.replaceState = wrapHistory(targetWindow.history.replaceState);
    }}

    // 拦截 Fetch
    if (targetWindow.fetch) {{
      var nativeFetch = targetWindow.fetch.bind(targetWindow);
      targetWindow.fetch = function (input, init) {{
        if (typeof Request !== "undefined" && input instanceof Request) {{
          var mapped = toGatewayUrl(input.url);
          if (mapped !== input.url) {{
            try {{ input = new Request(mapped, input); }} catch (_) {{}}
          }}
        }} else {{
          input = toGatewayUrl(input);
        }}
        return nativeFetch(input, init);
      }};
    }}

    // 拦截 XMLHttpRequest
    if (targetWindow.XMLHttpRequest) {{
      var nativeXHROpen = targetWindow.XMLHttpRequest.prototype.open;
      targetWindow.XMLHttpRequest.prototype.open = function (method, url) {{
        arguments[1] = toGatewayUrl(url);
        return nativeXHROpen.apply(this, arguments);
      }};
    }}

    // 拦截 DOM 元素属性
    var hookProperty = function (proto, prop, isSrcset) {{
      if (!proto) return;
      var desc = Object.getOwnPropertyDescriptor(proto, prop);
      if (!desc || !desc.set || !desc.configurable) return;
      var nativeSet = desc.set;
      Object.defineProperty(proto, prop, {{
        set: function (val) {{
          return nativeSet.call(this, isSrcset ? toGatewaySrcset(val) : toGatewayUrl(val));
        }},
        get: desc.get,
        configurable: true,
        enumerable: true
      }});
    }};

    if (targetWindow.HTMLImageElement) {{
      hookProperty(targetWindow.HTMLImageElement.prototype, "src", false);
      hookProperty(targetWindow.HTMLImageElement.prototype, "srcset", true);
    }}
    if (targetWindow.HTMLLinkElement) hookProperty(targetWindow.HTMLLinkElement.prototype, "href", false);
    if (targetWindow.HTMLAnchorElement) hookProperty(targetWindow.HTMLAnchorElement.prototype, "href", false);
    if (targetWindow.HTMLIFrameElement) hookProperty(targetWindow.HTMLIFrameElement.prototype, "src", false);
    if (targetWindow.HTMLScriptElement) hookProperty(targetWindow.HTMLScriptElement.prototype, "src", false);
    if (targetWindow.HTMLMediaElement) hookProperty(targetWindow.HTMLMediaElement.prototype, "src", false);
    if (targetWindow.HTMLSourceElement) {{
      hookProperty(targetWindow.HTMLSourceElement.prototype, "src", false);
      hookProperty(targetWindow.HTMLSourceElement.prototype, "srcset", true);
    }}

    // 拦截 setAttribute 与 innerHTML
    if (targetWindow.Element) {{
      var nativeSetAttr = targetWindow.Element.prototype.setAttribute;
      targetWindow.Element.prototype.setAttribute = function (name, value) {{
        var n = String(name).toLowerCase();
        if (n === "src" || n === "href" || n === "action") {{
          value = toGatewayUrl(value);
        }} else if (n === "srcset") {{
          value = toGatewaySrcset(value);
        }}
        return nativeSetAttr.call(this, name, value);
      }};

      var innerDesc = Object.getOwnPropertyDescriptor(targetWindow.Element.prototype, "innerHTML");
      if (innerDesc && innerDesc.set && innerDesc.configurable) {{
        var nativeInnerSet = innerDesc.set;
        Object.defineProperty(targetWindow.Element.prototype, "innerHTML", {{
          set: function (val) {{
            return nativeInnerSet.call(this, rewriteHtmlString(val));
          }},
          get: innerDesc.get,
          configurable: true,
          enumerable: true
        }});
      }}
    }}

    // 拦截超链接点击
    targetWindow.addEventListener("click", function (e) {{
      var target = e.target;
      while (target && target.tagName !== "A") target = target.parentElement;
      if (target && target.tagName === "A") {{
        var href = target.getAttribute("href") || target.href;
        var mapped = toGatewayUrl(href);
        if (mapped) {{
          target.setAttribute("href", mapped);
          if (target.href) target.href = mapped;
        }}
      }}
    }}, true);

    // 拦截 window.open 与 sendBeacon
    if (typeof targetWindow.open === "function") {{
      var nativeOpen = targetWindow.open.bind(targetWindow);
      targetWindow.open = function (url, target, features) {{
        return nativeOpen(toGatewayUrl(url), target, features);
      }};
    }}
    if (targetWindow.navigator && typeof targetWindow.navigator.sendBeacon === "function") {{
      var nativeBeacon = targetWindow.navigator.sendBeacon.bind(targetWindow.navigator);
      targetWindow.navigator.sendBeacon = function (url, data) {{
        return nativeBeacon(toGatewayUrl(url), data);
      }};
    }}

    // 拦截 Worker
    if (targetWindow.Worker) {{
      var nativeWorker = targetWindow.Worker;
      targetWindow.Worker = new Proxy(nativeWorker, {{
        construct: function (target, args, newTarget) {{
          args = [toGatewayUrl(args[0])].concat(args.slice(1));
          return Reflect.construct(target, args, newTarget);
        }}
      }});
    }}
    if (targetWindow.SharedWorker) {{
      var nativeSharedWorker = targetWindow.SharedWorker;
      targetWindow.SharedWorker = new Proxy(nativeSharedWorker, {{
        construct: function (target, args, newTarget) {{
          args = [toGatewayUrl(args[0])].concat(args.slice(1));
          return Reflect.construct(target, args, newTarget);
        }}
      }});
    }}

    // 拦截 WebSocket
    if (targetWindow.WebSocket) {{
      var nativeWebSocket = targetWindow.WebSocket;
      targetWindow.WebSocket = new Proxy(nativeWebSocket, {{
        construct: function (target, args, newTarget) {{
          try {{
            var url = new URL(String(args[0]), targetWindow.location.href);
            if ((url.protocol === "ws:" || url.protocol === "wss:") && !isAlreadyPrefixed(url.pathname)) {{
              var rawPath = url.pathname.indexOf('/') === 0 ? url.pathname : '/' + url.pathname;
              url.pathname = prefix + rawPath;
              args = [url.toString()].concat(args.slice(1));
            }}
          }} catch (_) {{}}
          return Reflect.construct(target, args, newTarget);
        }}
      }});
    }}

    // 拦截 EventSource
    if (targetWindow.EventSource) {{
      var nativeEventSource = targetWindow.EventSource;
      targetWindow.EventSource = new Proxy(nativeEventSource, {{
        construct: function (target, args, newTarget) {{
          args = [toGatewayUrl(args[0])].concat(args.slice(1));
          return Reflect.construct(target, args, newTarget);
        }}
      }});
    }}

    // 注入同源 iframe
    var injectIframe = function (el) {{
      try {{
        if (!el || el.__fnHooked) return;
        el.__fnHooked = true;
        var hookWin = function () {{
          try {{
            var win = el.contentWindow;
            if (win && win !== targetWindow) installBridge(win);
          }} catch (_) {{}}
        }};
        el.addEventListener("load", hookWin);
        hookWin();
      }} catch (_) {{}}
    }};

    if (targetWindow.MutationObserver) {{
      var observer = new MutationObserver(function (mutations) {{
        for (var i = 0; i < mutations.length; i++) {{
          var nodes = mutations[i].addedNodes;
          for (var j = 0; j < nodes.length; j++) {{
            if (nodes[j].tagName === "IFRAME") injectIframe(nodes[j]);
          }}
        }}
      }});
      if (targetWindow.document && targetWindow.document.documentElement) {{
        observer.observe(targetWindow.document.documentElement, {{ childList: true, subtree: true }});
      }}
    }}
  }};

  installBridge(window);
}})("{prefix}");
</script>"""


def strip_prefix(path: str, prefix: str) -> str:
    """剥除网关前缀"""
    if prefix and (path == prefix or path.startswith(prefix + "/")):
        path = path[len(prefix):]
        if not path.startswith("/"):
            path = "/" + path
    return path or "/"


class FnGatewayHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    STATIC_EXTS = (".js", ".css", ".png", ".jpg", ".jpeg", ".svg", ".ico", ".woff", ".woff2", ".ttf", ".webp", ".map")

    def log_message(self, format, *args):
        """输出访问日志"""
        code = str(args[0]) if args else ""
        if code.startswith(("2", "3")) and self.path.endswith(self.STATIC_EXTS):
            return
        logger.info(f"{self.command} {self.path} - {format % args}")

    def do_HEAD(self): self.handle_proxy()
    def do_GET(self): self.handle_proxy()
    def do_POST(self): self.handle_proxy()
    def do_PUT(self): self.handle_proxy()
    def do_DELETE(self): self.handle_proxy()
    def do_PATCH(self): self.handle_proxy()
    def do_OPTIONS(self): self.handle_proxy()

    def handle_proxy(self):
        """HTTP 反向代理处理"""
        prefix = self.server.prefix
        target_host = self.server.target_host
        target_port = self.server.target_port

        if self.headers.get("Upgrade", "").lower() == "websocket":
            self.handle_websocket_tunnel()
            return

        req_path = strip_prefix(self.path, prefix)

        # 读取请求体
        content_len = int(self.headers.get("Content-Length", 0))
        is_chunked_req = self.headers.get("Transfer-Encoding", "").lower() == "chunked"
        body = self.rfile.read(content_len) if content_len > 0 else (self.rfile if is_chunked_req else None)

        # 构建转发请求头
        headers = {}
        for k, v in self.headers.items():
            if k.lower() not in ("host", "origin", "sec-fetch-site", "connection"):
                headers[k] = v

        headers["Host"] = f"{target_host}:{target_port}"
        headers["Origin"] = f"http://{target_host}:{target_port}"
        headers["Sec-Fetch-Site"] = "same-origin"
        headers["Connection"] = "close"

        try:
            conn = http.client.HTTPConnection(target_host, target_port, timeout=30)
            conn.connect()
            if conn.sock:
                conn.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            conn.request(self.command, req_path, body=body, headers=headers)
            resp = conn.getresponse()

            content_type = ""
            content_encoding = ""
            content_length = -1
            out_headers = []

            for k, v in resp.getheaders():
                k_lower = k.lower()
                if k_lower == "content-type":
                    content_type = v.lower()
                elif k_lower == "content-encoding":
                    content_encoding = v.lower()
                elif k_lower == "content-length":
                    try:
                        content_length = int(v)
                    except ValueError:
                        pass
                elif k_lower == "location":
                    if v.startswith("/") and not v.startswith("//") and not (prefix and (v == prefix or v.startswith(prefix + "/"))):
                        v = prefix + v
                elif k_lower == "set-cookie":
                    if "path=/;" in v.lower() or v.lower().endswith("path=/"):
                        v = re.sub(r'(?i)path=/;', f'Path={prefix}/;', v)
                        if v.lower().endswith("path=/"):
                            v = v[:-7] + f"Path={prefix}/"

                if k_lower not in ("content-length", "transfer-encoding", "connection"):
                    out_headers.append((k, v))

            # HTML 注入改写
            if "text/html" in content_type:
                resp_body = resp.read()
                if "gzip" in content_encoding:
                    try:
                        resp_body = gzip.decompress(resp_body)
                    except Exception:
                        pass

                html_text = resp_body.decode("utf-8", errors="ignore")

                def replace_attr(m):
                    attr, quote, p = m.group(1), m.group(2), m.group(3)
                    return m.group(0) if (p.startswith("//") or (prefix and p.startswith(prefix))) else f"{attr}={quote}{prefix}{p}"

                modified_html = HTML_ATTR_RE.sub(replace_attr, html_text)
                base_tag = f'<base href="{prefix}/">' if prefix else ""
                bridge_code = base_tag + self.server.bridge_code

                head_match = re.search(r"(?i)<head[^>]*>", modified_html)
                if head_match:
                    idx = head_match.end()
                    modified_html = modified_html[:idx] + bridge_code + modified_html[idx:]
                else:
                    modified_html = bridge_code + modified_html

                final_bytes = modified_html.encode("utf-8")
                filtered_headers = [(k, v) for k, v in out_headers if k.lower() not in ("content-encoding", "content-security-policy", "content-security-policy-report-only")]

                resp_lines = [f"HTTP/1.1 {resp.status} {resp.reason}"]
                for k, v in filtered_headers:
                    resp_lines.append(f"{k}: {v}")
                resp_lines.append(f"Content-Length: {len(final_bytes)}")
                resp_lines.append("Connection: close\r\n\r\n")

                self.connection.sendall("\r\n".join(resp_lines).encode("latin1") + final_bytes)
                self.close_connection = True
                conn.close()
                return

            # JS 动态路由适配改写与响应转发
            if prefix and req_path.endswith(".js"):
                resp_body = resp.read()
                is_gzip = "gzip" in content_encoding
                if is_gzip:
                    try:
                        resp_body = gzip.decompress(resp_body)
                        content_encoding = ""
                    except Exception:
                        pass

                def patch_route(m):
                    fn = m.group(1).decode("utf-8")
                    arg = m.group(2).decode("utf-8")
                    route = m.group(3).decode("utf-8")
                    val = m.group(4).decode("utf-8")
                    return (
                        f'function {fn}({arg}){{const p="{prefix}";const s={arg}.startsWith(p)?'
                        f'{arg}.slice(p.length)||"/":{arg};return/^\\/{route}(?:\\/|$)/.test(s)?'
                        f'({arg}.startsWith(p)?p+{val}:{val}):({arg}.startsWith(p)?p:void 0)}}'
                    ).encode("utf-8")

                if not content_encoding and JS_ROUTE_RE.search(resp_body):
                    resp_body = JS_ROUTE_RE.sub(patch_route, resp_body)

                filtered_headers = []
                for k, v in out_headers:
                    if not content_encoding and k.lower() == "content-encoding":
                        continue
                    filtered_headers.append((k, v))

                resp_lines = [f"HTTP/1.1 {resp.status} {resp.reason}"]
                for k, v in filtered_headers:
                    resp_lines.append(f"{k}: {v}")
                resp_lines.append(f"Content-Length: {len(resp_body)}")
                resp_lines.append("Connection: close\r\n\r\n")

                self.connection.sendall("\r\n".join(resp_lines).encode("latin1") + resp_body)
                self.close_connection = True
                conn.close()
                return

            # 通用流式直通（API / 静态资源 / SSE / 音视频流）
            resp_lines = [f"HTTP/1.1 {resp.status} {resp.reason}"]
            for k, v in out_headers:
                resp_lines.append(f"{k}: {v}")
            if content_length >= 0:
                resp_lines.append(f"Content-Length: {content_length}")
            resp_lines.append("Connection: close\r\n\r\n")

            self.connection.sendall("\r\n".join(resp_lines).encode("latin1"))
            while True:
                chunk = resp.read(CHUNK_SIZE)
                if not chunk:
                    break
                self.connection.sendall(chunk)

            self.close_connection = True
            conn.close()

        except (BrokenPipeError, ConnectionResetError):
            self.close_connection = True
        except Exception as e:
            logger.error(f"代理请求失败 [{self.command} {self.path}]: {e}")
            try:
                self.send_error(http.client.BAD_GATEWAY, f"Bad Gateway: {str(e)}")
            except Exception:
                pass
            self.close_connection = True

    def handle_websocket_tunnel(self):
        """WebSocket 全双工隧道"""
        prefix = self.server.prefix
        target_host = self.server.target_host
        target_port = self.server.target_port

        req_path = strip_prefix(self.path, prefix)

        target_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        target_sock.connect((target_host, target_port))

        handshake = [f"{self.command} {req_path} HTTP/1.1"]
        for k, v in self.headers.items():
            k_lower = k.lower()
            if k_lower == "host":
                handshake.append(f"Host: {target_host}:{target_port}")
            elif k_lower == "origin":
                handshake.append(f"Origin: http://{target_host}:{target_port}")
            else:
                handshake.append(f"{k}: {v}")
        handshake.append("\r\n")
        target_sock.sendall("\r\n".join(handshake).encode("utf-8"))

        client_sock = self.connection
        sockets = [client_sock, target_sock]
        logger.info(f"WebSocket 隧道建立: {req_path}")
        try:
            while True:
                r_list, _, x_list = select.select(sockets, [], sockets, 60)
                if x_list:
                    break
                for s in r_list:
                    data = s.recv(CHUNK_SIZE)
                    if not data:
                        return
                    if s is client_sock:
                        target_sock.sendall(data)
                    else:
                        client_sock.sendall(data)
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            self.close_connection = True
            target_sock.close()
            logger.info(f"WebSocket 隧道关闭: {req_path}")


if hasattr(socketserver, "UnixStreamServer"):
    BaseUnixServer = socketserver.UnixStreamServer
else:
    class BaseUnixServer(socketserver.TCPServer):
        address_family = getattr(socket, "AF_UNIX", socket.AF_INET)

        def server_bind(self):
            self.socket.bind(self.server_address)
            self.server_address = self.socket.getsockname()


class ThreadingUnixHTTPServer(socketserver.ThreadingMixIn, BaseUnixServer):
    """Unix Domain Socket HTTP 服务"""
    def __init__(self, socket_path: str, target_host: str, target_port: int, prefix: str):
        self.socket_path = socket_path
        self.target_host = target_host
        self.target_port = target_port
        self.prefix = prefix.rstrip("/")
        self.bridge_code = generate_bridge_script(self.prefix)

        if os.path.exists(socket_path):
            try:
                os.unlink(socket_path)
            except Exception:
                pass

        super().__init__(socket_path, FnGatewayHandler)

        try:
            os.chmod(socket_path, 0o666)
        except Exception:
            pass


def parse_listen_address(addr: str) -> tuple[str, int]:
    """解析监听地址为 host 与 port"""
    clean_addr = addr.replace("http://", "").replace("https://", "").strip().rstrip("/")
    if ":" in clean_addr:
        parts = clean_addr.split(":")
        host = parts[0] if parts[0] else "127.0.0.1"
        port = int(parts[1])
        return host, port
    return "127.0.0.1", int(clean_addr)


def main():
    parser = argparse.ArgumentParser(description="飞牛网关反向代理中间件")
    parser.add_argument("--listen", type=str, required=True, help="目标后端地址 (格式: 127.0.0.1:2298 或 2298)")
    parser.add_argument("--socket", type=str, required=True, help="Unix Domain Socket 监听路径")
    parser.add_argument("--prefix", type=str, required=True, help="飞牛网关反向代理路由前缀")
    args = parser.parse_args()

    target_host, target_port = parse_listen_address(args.listen)

    def cleanup():
        if os.path.exists(args.socket):
            try:
                os.unlink(args.socket)
            except Exception:
                pass

    def sig_handler(*_):
        sys.exit(0)

    atexit.register(cleanup)
    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    server = ThreadingUnixHTTPServer(args.socket, target_host, target_port, args.prefix)
    logger.info(f"服务已启动: Unix套接字 [{args.socket}] -> 目标后端 [{target_host}:{target_port}] (路由前缀: {args.prefix})")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        cleanup()
        logger.info("服务已停止并清理套接字")


if __name__ == "__main__":
    main()
