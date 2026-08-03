from pathlib import Path
import requests, base64

invoke_url = "https://integrate.api.nvidia.com/v1/chat/completions"
API_KEY = ""
IMAGE_PATH = "/Users/ccy/Documents/测试三方API/v295_annual_returns.png"

IMAGE_MIME_TYPES = {
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".webp": "image/webp",
}

def read_image_data_url(path):
  path = Path(path)
  with open(path, "rb") as f:
    image_b64 = base64.b64encode(f.read()).decode()
  suffix = path.suffix.lower()
  return f"data:{IMAGE_MIME_TYPES.get(suffix, 'image/png')};base64,{image_b64}"


print("╔══════════════════════════════════════════════╗")
print("║      图片识别测试 - 年度收益对比图表          ║")
print(f"║      图片: {IMAGE_PATH}                      ║")
print("╚══════════════════════════════════════════════╝")

image_data = read_image_data_url(IMAGE_PATH)
print("已加载图片数据...")

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
    "Accept": "application/json"
}

payload = {
    "model": "stepfun-ai/step-3.7-flash",
    "messages": [{
        "role": "user",
        "content": [
            {"type": "text", "text": "请详细分析这张年度收益对比图表，包括：1）图表标题；2）对比的两个策略名称；3）各年度收益数据；4）右侧指标表格中的关键数据。"},
            {"type": "image_url", "image_url": {"url": image_data}}
        ]
    }],
    "max_tokens": 16384,
    "temperature": 0.7,
    "top_p": 0.95,
    "stream": False,
}

try:
    print("\n正在发送请求...")
    response = requests.post(invoke_url, headers=headers, json=payload, timeout=120)
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        content = result["choices"][0]["message"]["content"]
        print("\n" + "="*60)
        print("图片分析结果:")
        print("="*60)
        print(content)
        
        usage = result.get("usage")
        if usage:
            print(f"\nToken用量: {usage}")
    else:
        print(f"\n请求失败: {response.text}")
        
except Exception as e:
    print(f"\n请求异常: {e}")
