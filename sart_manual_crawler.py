"""
sart_manual_crawler.py
------------------------------------------------------------
用途：
    从萨特官网 (sartfuse.com) "选型手册" 页面下载全部型号选型手册图片，
    并合并成一份 PDF，方便整理成结构化的选型参数表。

安装依赖（在命令行执行）：
    pip install requests beautifulsoup4 img2pdf

运行：
    python sart_manual_crawler.py

输出：
    ./sart_manual/images/                  -> 下载的所有原始图片（按页码命名）
    ./sart_manual/萨特产品选型手册.pdf      -> 合并后的PDF文件

说明：
    - 官网选型手册页面把PDF拆成了一张张图片展示（page188），
      本脚本会自动解析该页面，抓取所有手册图片链接并下载。
    - 如果官网页面结构有调整导致抓不到图片，脚本会打印提示，
      需要手动打开 https://www.sartfuse.com/page188 看一下网页源码
      里图片链接的实际写法，再调整下面 get_manual_image_urls() 里的匹配规则。
    - 请求之间加了 0.5 秒间隔，避免对官网服务器造成压力。
------------------------------------------------------------
"""

import os
import re
import time
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.sartfuse.com"
MANUAL_PAGE = f"{BASE_URL}/page188"
OUTPUT_DIR = "sart_manual"
IMG_DIR = os.path.join(OUTPUT_DIR, "images")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": BASE_URL,
}


def get_manual_image_urls():
    """解析选型手册页面，返回所有手册页图片的URL列表（保持原始顺序）"""
    resp = requests.get(MANUAL_PAGE, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    urls = []
    for img in soup.find_all("img"):
        src = img.get("src", "")
        if "选型手册" in src:
            urls.append(src)

    # 兜底方案：如果上面按 <img> 标签解析不到，直接用正则从原始 HTML 里扒图片链接
    if not urls:
        urls = re.findall(
            r'https?://[^\s"\']+选型手册[^\s"\']+\.(?:png|jpg|jpeg)',
            resp.text,
        )

    # 去重并保持出现顺序（页面里图片一般按页码顺序排列）
    seen = set()
    ordered = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            ordered.append(u)
    return ordered


def download_images(urls):
    os.makedirs(IMG_DIR, exist_ok=True)
    paths = []
    for i, url in enumerate(urls, 1):
        ext = url.split(".")[-1].split("?")[0]
        fname = os.path.join(IMG_DIR, f"page_{i:03d}.{ext}")
        if os.path.exists(fname):
            print(f"[{i}/{len(urls)}] 已存在，跳过：{fname}")
            paths.append(fname)
            continue
        print(f"[{i}/{len(urls)}] 下载：{url}")
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            r.raise_for_status()
            with open(fname, "wb") as f:
                f.write(r.content)
            paths.append(fname)
        except Exception as e:
            print(f"    下载失败：{e}")
        time.sleep(0.5)
    return paths


def images_to_pdf(image_paths, out_pdf):
    import img2pdf

    # img2pdf 只吃 jpg/png，且要求都是同类颜色模式，出问题时可跳过这步，直接用图片文件夹
    with open(out_pdf, "wb") as f:
        f.write(img2pdf.convert(image_paths))
    print(f"\n已生成 PDF：{out_pdf}")


def main():
    print("正在解析选型手册页面...")
    urls = get_manual_image_urls()
    if not urls:
        print("没有解析到任何图片链接，页面结构可能有变化。")
        print(f"请手动打开 {MANUAL_PAGE} 查看网页源码，确认图片链接的写法后再调整脚本。")
        return

    print(f"共找到 {len(urls)} 张手册页图片\n")
    paths = download_images(urls)

    if paths:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        try:
            images_to_pdf(paths, os.path.join(OUTPUT_DIR, "萨特产品选型手册.pdf"))
        except Exception as e:
            print(f"\n合并PDF失败（不影响图片已下载）：{e}")
            print(f"原始图片都在 {IMG_DIR} 文件夹里，可以手动查看或用其他工具合并。")


if __name__ == "__main__":
    main()
