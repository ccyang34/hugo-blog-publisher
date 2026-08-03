#!/usr/bin/env python3
"""
OCR工具模块 - macOS Vision 框架
通用化OCR功能，任何平台都能用
"""

import os
from typing import List, Dict, Optional

try:
    import Vision
    import Cocoa
    import Quartz
    HAS_VISION = True
except ImportError:
    HAS_VISION = False


def macos_ocr(image_path: str, languages: List[str] = None) -> str:
    """
    使用 macOS Vision 框架识别图片中的文字
    
    Args:
        image_path: 图片文件路径
        languages: 语言列表，默认 ["zh-Hans", "en"]
    
    Returns:
        识别出的文字内容
    """
    if not HAS_VISION:
        raise ImportError("macOS Vision 框架不可用，仅支持 macOS 系统")
    
    if languages is None:
        languages = ["zh-Hans", "en"]
    
    try:
        img_url = Cocoa.NSURL.fileURLWithPath_(image_path)
        source = Quartz.CGImageSourceCreateWithURL(img_url, None)
        if not source:
            return "[OCR失败: 无法读取图片]"
        
        cg_image = Quartz.CGImageSourceCreateImageAtIndex(source, 0, None)
        if not cg_image:
            return "[OCR失败: 无法解码图片]"
        
        request = Vision.VNRecognizeTextRequest.alloc().init()
        request.setRecognitionLanguages_(languages)
        request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
        request.setUsesLanguageCorrection_(True)
        
        handler = Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(cg_image, None)
        success, error = handler.performRequests_error_([request], None)
        
        if not success:
            return f"[OCR失败: {error}]"
        
        results = []
        for obs in request.results() or []:
            text = obs.topCandidates_(1)[0].string()
            confidence = obs.topCandidates_(1)[0].confidence()
            y = float(obs.boundingBox().origin.y)
            results.append({"text": text, "confidence": float(confidence), "y": y})
        
        # 按垂直位置排序（从上到下）
        results.sort(key=lambda r: -r["y"])
        return "\n".join(r["text"] for r in results if r["confidence"] > 0.3)
        
    except Exception as e:
        return f"[OCR异常: {e}]"


def ocr_image_batch(image_paths: List[str], languages: List[str] = None) -> List[Dict]:
    """
    批量OCR识别图片
    
    Args:
        image_paths: 图片路径列表
        languages: 语言列表
    
    Returns:
        结果列表，每项包含 {path, text, has_text, char_count}
    """
    results = []
    
    for path in image_paths:
        text = macos_ocr(path, languages)
        has_text = len(text) > 10 and not text.startswith("[OCR")
        
        results.append({
            "path": path,
            "filename": os.path.basename(path),
            "text": text,
            "has_text": has_text,
            "char_count": len(text),
        })
    
    return results


def ocr_from_url(url: str, save_dir: str = "/tmp/ocr_images") -> str:
    """
    从URL下载图片并OCR
    
    Args:
        url: 图片URL
        save_dir: 保存目录
    
    Returns:
        识别出的文字
    """
    import httpx
    
    os.makedirs(save_dir, exist_ok=True)
    
    try:
        resp = httpx.get(url, timeout=30, follow_redirects=True)
        resp.raise_for_status()
        
        ext = ".jpg"
        ct = resp.headers.get("content-type", "")
        if "png" in ct: ext = ".png"
        elif "webp" in ct: ext = ".webp"
        
        filepath = os.path.join(save_dir, f"temp_ocr{ext}")
        with open(filepath, "wb") as f:
            f.write(resp.content)
        
        return macos_ocr(filepath)
        
    except Exception as e:
        return f"[下载或OCR失败: {e}]"


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python3 ocr_utils.py <图片路径>")
        sys.exit(1)
    
    result = macos_ocr(sys.argv[1])
    print(result)
