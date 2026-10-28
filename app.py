# -*- coding: utf-8 -*-
"""
南京 · 五一三日游 旅行攻略 Web 服务
------------------------------------
- 仅使用 Python 标准库，无需安装任何第三方依赖
- 提供 /api/trip 行程数据接口，静态托管 index.html
- 启动后自动打开浏览器

运行:  python app.py
"""
import json
import os
import socket
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import quote

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PORT = 8080
GAODE_WEB = "https://uri.amap.com"

# ---------------------------------------------------------------------------
# 高德地图 MCP 生成结果
# ---------------------------------------------------------------------------
# 由 高德地图 MCP 工具 maps_schema_personal_map 生成的「三日游路线」个人地图
# （唤起高德 APP 查看完整路线）
PERSONAL_MAP_URI = (
    "amapuri://workInAmap/createWithToken"
    "?polymericId=mcp_63b9f944a7d345e3a4464cd6829df76b&from=MCP"
)


def nav_web(src, dst):
    """高德网页版驾车路线（浏览器内展示，非 JS 绘制地图）。"""
    return (
        f"{GAODE_WEB}/navigation?from={src['lng']},{src['lat']},{quote(src['name'])}"
        f"&to={dst['lng']},{dst['lat']},{quote(dst['name'])}"
        f"&mode=car&policy=1&src=mcp&coordinate=gaode&callnative=0"
    )


def marker_web(p):
    """高德网页版单点标记。"""
    return (
        f"{GAODE_WEB}/marker?position={p['lng']},{p['lat']}"
        f"&name={quote(p['name'])}&src=mcp&coordinate=gaode&callnative=0"
    )


# ---------------------------------------------------------------------------
# 景点数据（坐标 / POI / 图片来自高德地图 MCP maps_text_search）
# ---------------------------------------------------------------------------
SPOTS = {
    "zhongshanling": {
        "name": "中山陵景区", "poiId": "B0FFHVEECG",
        "lng": 118.8595, "lat": 32.0592, "addr": "玄武区石象路7号",
        "time": "09:00 - 11:30",
        "desc": "392 级台阶拾级而上，瞻仰孙中山先生陵寝，登顶可俯瞰紫金山层层林海。",
        "img": "http://store.is.autonavi.com/showpic/46bf800a21c42453ff756fc2b77c710f",
    },
    "mingxiaoling": {
        "name": "明孝陵景区", "poiId": "B0FFFFKG55",
        "lng": 118.8435, "lat": 32.0597, "addr": "玄武区石象路7-8号",
        "time": "12:00 - 14:30",
        "desc": "明太祖朱元璋与马皇后合葬陵，世界文化遗产，神道石象路被誉为最美林荫大道。",
        "img": "http://store.is.autonavi.com/showpic/a9d8eb4d58561ffda8bb4ff08c8a4d2c",
    },
    "fuzimiao": {
        "name": "南京夫子庙", "poiId": "B00190ANHZ",
        "lng": 118.7907, "lat": 32.0208, "addr": "秦淮区贡院街152号",
        "time": "17:00 - 21:00",
        "desc": "十里秦淮核心地带，贡院、大成殿与画舫夜游相映，是金陵夜色的代表。",
        "img": "http://store.is.autonavi.com/showpic/8fd02cf1c04a8a5a91e32a5354d7a023",
    },
    "zongtongfu": {
        "name": "总统府", "poiId": "B00190BMRC",
        "lng": 118.7963, "lat": 32.0445, "addr": "玄武区长江路292号",
        "time": "09:00 - 11:30",
        "desc": "中国近代史遗址博物馆，六百年官署建筑群，一步一景见证百年风云。",
        "img": "http://aos-cdn-image.amap.com/sns/ugccomment/21acde57-d540-4737-974a-11b6c69d23de.jpg",
    },
    "museum": {
        "name": "南京博物院", "poiId": "B001907TGR",
        "lng": 118.8227, "lat": 32.0468, "addr": "玄武区中山东路321号",
        "time": "13:00 - 16:30",
        "desc": "中国三大博物馆之一，一院六馆；民国馆沉浸式复原老街景，拍照与讲解俱佳。",
        "img": "http://store.is.autonavi.com/showpic/6d9679442d9f514b78d55213b43d9417",
    },
    "xuanwuhu": {
        "name": "玄武湖景区", "poiId": "B00190BBCZ",
        "lng": 118.8023, "lat": 32.0780, "addr": "玄武区玄武巷1号",
        "time": "17:00 - 19:30",
        "desc": "江南最大城内公园，五洲相连，环湖步道与明城墙、紫峰大厦同框。",
        "img": "http://store.is.autonavi.com/showpic/ff2f4114639e0110ae96ae76ad0c0287",
    },
    "jimingsi": {
        "name": "古鸡鸣寺", "poiId": "B0FFH62KNA",
        "lng": 118.7889, "lat": 32.0603, "addr": "玄武区鸡鸣寺路1号",
        "time": "08:30 - 10:30",
        "desc": "千年古刹，号称「南朝四百八十寺」之首，药师塔与樱花景观闻名全城。",
        "img": "http://store.is.autonavi.com/query_pic?id=st653d2760-3b45-47e5-ad2c-7a027aea5997&user=search&operate=original",
    },
    "laomendong": {
        "name": "老门东", "poiId": "B00190BU4S",
        "lng": 118.7906, "lat": 32.0145, "addr": "秦淮区剪子巷54号",
        "time": "11:30 - 15:00",
        "desc": "城南传统风貌街区，青砖马头墙、非遗手作与地道小吃云集，烟火气十足。",
        "img": "http://store.is.autonavi.com/showpic/69e7ca3e4d0357955c61d1ec1682a587",
    },
    "jinianguan": {
        "name": "侵华日军南京大屠杀遇难同胞纪念馆", "poiId": "B001905N9D",
        "lng": 118.7383, "lat": 32.0385, "addr": "建邺区水西门大街418号",
        "time": "15:30 - 17:30",
        "desc": "铭记历史、珍爱和平的国家级纪念场馆，参观时请保持肃静与敬意。",
        "img": "http://store.is.autonavi.com/showpic/5bece6e3e3e4e0203fe0f2962394a46d",
    },
}

# 高德地图 MCP maps_schema_take_taxi 生成的「一键打车」URI（同一行程景区间）
TAXI_URIS = {
    ("zhongshanling", "mingxiaoling"):
        "amapuri://drive/takeTaxi?sourceApplication=amapplatform&slat=32.0592&slon=118.8595"
        "&sname=%E4%B8%AD%E5%B1%B1%E9%99%B5%E6%99%AF%E5%8C%BA&dlon=118.8435&dlat=32.0597"
        "&dname=%E6%98%8E%E5%AD%9D%E9%99%B5%E6%99%AF%E5%8C%BA",
    ("mingxiaoling", "fuzimiao"):
        "amapuri://drive/takeTaxi?sourceApplication=amapplatform&slat=32.0597&slon=118.8435"
        "&sname=%E6%98%8E%E5%AD%9D%E9%99%B5%E6%99%AF%E5%8C%BA&dlon=118.7907&dlat=32.0208"
        "&dname=%E5%8D%97%E4%BA%AC%E5%A4%AB%E5%AD%90%E5%BA%99",
    ("zongtongfu", "museum"):
        "amapuri://drive/takeTaxi?sourceApplication=amapplatform&slat=32.0445&slon=118.7963"
        "&sname=%E6%80%BB%E7%BB%9F%E5%BA%9C&dlon=118.8227&dlat=32.0468"
        "&dname=%E5%8D%97%E4%BA%AC%E5%8D%9A%E7%89%A9%E9%99%A2",
    ("museum", "xuanwuhu"):
        "amapuri://drive/takeTaxi?sourceApplication=amapplatform&slat=32.0468&slon=118.8227"
        "&sname=%E5%8D%97%E4%BA%AC%E5%8D%9A%E7%89%A9%E9%99%A2&dlon=118.8023&dlat=32.078"
        "&dname=%E7%8E%84%E6%AD%A6%E6%B9%96%E6%99%AF%E5%8C%BA",
    ("jimingsi", "laomendong"):
        "amapuri://drive/takeTaxi?sourceApplication=amapplatform&slat=32.0603&slon=118.7889"
        "&sname=%E5%8F%A4%E9%B8%A1%E9%B8%A3%E5%AF%BA&dlon=118.7906&dlat=32.0145"
        "&dname=%E8%80%81%E9%97%A8%E4%B8%9C",
    ("laomendong", "jinianguan"):
        "amapuri://drive/takeTaxi?sourceApplication=amapplatform&slat=32.0145&slon=118.7906"
        "&sname=%E8%80%81%E9%97%A8%E4%B8%9C&dlon=118.7383&dlat=32.0385"
        "&dname=%E4%BE%B5%E5%8D%8E%E6%97%A5%E5%86%9B%E5%8D%97%E4%BA%AC%E5%A4%A7%E5%B1%A0%E6%9D%80"
        "%E9%81%87%E9%9A%BE%E5%90%8C%E8%83%9E%E7%BA%AA%E5%BF%B5%E9%A6%86",
}

# 每日行程（每天 3 个景点，含景区间打车段）
DAY_PLAN = [
    {
        "id": "day1", "date": "05-01", "week": "周五",
        "title": "钟山怀古 · 秦淮夜色", "theme": "历史人文",
        "spots": ["zhongshanling", "mingxiaoling", "fuzimiao"],
        "rides": [
            {"from": "zhongshanling", "to": "mingxiaoling", "distance": "7.2 km", "duration": "约 31 分钟"},
            {"from": "mingxiaoling", "to": "fuzimiao", "distance": "9.8 km", "duration": "约 46 分钟"},
        ],
    },
    {
        "id": "day2", "date": "05-02", "week": "周六",
        "title": "民国往事 · 玄武湖光", "theme": "博物寻访",
        "spots": ["zongtongfu", "museum", "xuanwuhu"],
        "rides": [
            {"from": "zongtongfu", "to": "museum", "distance": "3.0 km", "duration": "约 17 分钟"},
            {"from": "museum", "to": "xuanwuhu", "distance": "5.2 km", "duration": "约 19 分钟"},
        ],
    },
    {
        "id": "day3", "date": "05-03", "week": "周日",
        "title": "古寺钟声 · 城南漫步", "theme": "市井烟火",
        "spots": ["jimingsi", "laomendong", "jinianguan"],
        "rides": [
            {"from": "jimingsi", "to": "laomendong", "distance": "8.3 km", "duration": "约 38 分钟"},
            {"from": "laomendong", "to": "jinianguan", "distance": "10.4 km", "duration": "约 28 分钟"},
        ],
    },
]

# 天气（高德天气接口仅返回未来 4 天预报；5/1-5/3 已过，采用历史同期参考值）
WEATHER = [
    {"date": "05-01", "week": "周五", "icon": "⛅", "day": "多云转晴", "night": "晴",
     "low": 18, "high": 26, "wind": "东南风 1-3 级", "hint": "白天舒适，早晚有 8℃ 左右温差"},
    {"date": "05-02", "week": "周六", "icon": "☀️", "day": "晴", "night": "晴",
     "low": 19, "high": 28, "wind": "南风 1-3 级", "hint": "紫外线较强，注意防晒补水"},
    {"date": "05-03", "week": "周日", "icon": "⛅", "day": "多云", "night": "多云",
     "low": 17, "high": 25, "wind": "东风 2-4 级", "hint": "风力略大，适合安排室内展馆"},
]

TIPS = [
    {"icon": "🎫", "title": "预约提醒", "text": "中山陵、南京博物院、纪念馆均免费开放，但需提前 1-7 天在官方公众号实名预约，五一假期名额紧张。"},
    {"icon": "🚕", "title": "打车策略", "text": "假期景区打车排队较久，建议提前 10 分钟叫车；钟山风景区内可乘观光车接驳，省时省力。"},
    {"icon": "🚇", "title": "地铁出行", "text": "夫子庙（3 号线）、总统府（2/3 号线大行宫站）、玄武湖（1 号线玄武门站）地铁直达，错峰更顺畅。"},
    {"icon": "🍜", "title": "必尝美食", "text": "鸭血粉丝汤、盐水鸭、皮肚面、鸡鸣汤包；夫子庙与老门东小吃集中，夜晚人气最旺。"},
    {"icon": "🌦️", "title": "天气装备", "text": "早晚温差约 8℃，建议薄外套 + 舒适步行鞋，随身带伞以防阵雨。"},
    {"icon": "⏰", "title": "错峰建议", "text": "热门景点 9:30 前或 15:00 后入园人较少；纪念馆与博物院午后排队相对更短。"},
]


def build_trip_data():
    """组装前端所需的完整行程数据。"""
    days = []
    for plan in DAY_PLAN:
        spots = []
        for key in plan["spots"]:
            s = SPOTS[key]
            item = dict(s)
            item["key"] = key
            item["map_url"] = marker_web(s)
            spots.append(item)

        rides = []
        for r in plan["rides"]:
            a, b = SPOTS[r["from"]], SPOTS[r["to"]]
            rides.append({
                "from": a["name"], "to": b["name"],
                "distance": r["distance"], "duration": r["duration"],
                "taxi": TAXI_URIS[(r["from"], r["to"])],
                "route": nav_web(a, b),
            })

        # 每日地图：以当天首站 -> 末站的高德网页驾车路线作为总览
        first, last = SPOTS[plan["spots"][0]], SPOTS[plan["spots"][-1]]
        days.append({
            "id": plan["id"], "date": plan["date"], "week": plan["week"],
            "title": plan["title"], "theme": plan["theme"],
            "spots": spots, "rides": rides,
            "map_overview": nav_web(first, last),
        })

    return {
        "title": "南京 · 五一三日游",
        "subtitle": "2026.05.01 - 2026.05.03 ｜ 六朝古都 · 金陵怀古",
        "weather_note": "数据来源：高德地图 MCP 天气接口。接口仅提供未来 4 天预报，5/1-5/3 已过，此处为南京历史同期参考值。",
        "weather": WEATHER,
        "tips": TIPS,
        "personal_map_uri": PERSONAL_MAP_URI,
        "days": days,
    }


# ---------------------------------------------------------------------------
# HTTP 服务
# ---------------------------------------------------------------------------
class Handler(BaseHTTPRequestHandler):
    server_version = "NanJingTrip/1.0"

    def _send(self, status, body, content_type):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?", 1)[0]

        if path in ("/api/trip", "/api/trip/"):
            body = json.dumps(build_trip_data(), ensure_ascii=False).encode("utf-8")
            self._send(200, body, "application/json; charset=utf-8")
            return

        if path in ("", "/"):
            path = "/index.html"

        # 仅允许访问本目录内的静态文件，防目录穿越
        rel = os.path.normpath(path.lstrip("/\\"))
        file_path = os.path.join(BASE_DIR, rel)
        if not os.path.abspath(file_path).startswith(os.path.abspath(BASE_DIR)):
            self._send(403, b"Forbidden", "text/plain; charset=utf-8")
            return
        if os.path.isfile(file_path):
            with open(file_path, "rb") as f:
                body = f.read()
            ctype = "text/html; charset=utf-8"
            if file_path.endswith(".css"):
                ctype = "text/css; charset=utf-8"
            elif file_path.endswith(".js"):
                ctype = "application/javascript; charset=utf-8"
            elif file_path.endswith(".json"):
                ctype = "application/json; charset=utf-8"
            self._send(200, body, ctype)
            return

        self._send(404, b"404 Not Found", "text/plain; charset=utf-8")

    def log_message(self, fmt, *args):
        print("[nanjing-trip] " + (fmt % args))


def pick_port(start):
    for p in range(start, start + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(("127.0.0.1", p))
                return p
            except OSError:
                continue
    return start


def main():
    port = pick_port(DEFAULT_PORT)
    url = f"http://127.0.0.1:{port}/"

    httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print("=" * 56)
    print("  南京 · 五一三日游 旅行攻略 已启动")
    print(f"  访问地址: {url}")
    print("  按 Ctrl+C 停止服务")
    print("=" * 56)

    threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n服务已停止。")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()