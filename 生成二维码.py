#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
酮伴妈妈问卷二维码生成器
"""

import qrcode
from PIL import Image, ImageDraw, ImageFont
import os

# 问卷网址
URL = "https://wondrous-alfajores-37b4c0.netlify.app/keto-mom-interactive-quiz.html"

def generate_qrcode():
    """生成问卷二维码"""
    
    print("=" * 60)
    print("🎨 酮伴妈妈问卷 - 二维码生成器")
    print("=" * 60)
    print()
    
    # 创建二维码对象
    qr = qrcode.QRCode(
        version=1,  # 控制二维码大小 (1-40)
        error_correction=qrcode.constants.ERROR_CORRECT_H,  # 高容错率
        box_size=10,  # 每个格子的像素大小
        border=4,  # 边框格子数
    )
    
    # 添加数据
    qr.add_data(URL)
    qr.make(fit=True)
    
    # 生成基础二维码图片
    img = qr.make_image(fill_color="black", back_color="white")
    img = img.convert('RGB')
    
    # 保存基础版本
    basic_filename = "keto-quiz-qrcode-basic.png"
    img.save(basic_filename)
    print(f"✅ 基础二维码已生成: {basic_filename}")
    print(f"   尺寸: {img.size[0]}x{img.size[1]} 像素")
    print()
    
    # 生成带文字说明的版本
    generate_qrcode_with_text(img)
    
    # 生成彩色版本
    generate_colored_qrcode()
    
    print()
    print("=" * 60)
    print("🎉 所有二维码已生成完成！")
    print("=" * 60)
    print()
    print("📁 生成的文件：")
    print("   1. keto-quiz-qrcode-basic.png       - 基础黑白二维码")
    print("   2. keto-quiz-qrcode-with-text.png   - 带文字说明版")
    print("   3. keto-quiz-qrcode-colored.png     - 彩色版本")
    print()
    print("💡 使用建议：")
    print("   - 打印海报：使用 with-text 版本")
    print("   - 社交媒体：使用 colored 版本")
    print("   - 名片/传单：使用 basic 版本")
    print()
    print(f"🔗 问卷链接: {URL}")
    print()

def generate_qrcode_with_text(qr_img):
    """生成带文字说明的二维码"""
    
    # 创建新画布，增加空间放文字
    width, height = qr_img.size
    new_height = height + 120  # 增加底部空间
    
    new_img = Image.new('RGB', (width, new_height), 'white')
    
    # 粘贴二维码
    new_img.paste(qr_img, (0, 0))
    
    # 添加文字
    draw = ImageDraw.Draw(new_img)
    
    try:
        # 尝试使用中文字体
        font_large = ImageFont.truetype("C:\\Windows\\Fonts\\msyh.ttc", 28)  # 微软雅黑
        font_small = ImageFont.truetype("C:\\Windows\\Fonts\\msyh.ttc", 18)
    except:
        # 如果找不到字体，使用默认字体
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    # 文字内容
    title = "扫码体验酮伴妈妈故事"
    subtitle = "完成问卷赢取健康小食"
    
    # 计算文字位置（居中）
    title_bbox = draw.textbbox((0, 0), title, font=font_large)
    title_width = title_bbox[2] - title_bbox[0]
    title_x = (width - title_width) // 2
    
    subtitle_bbox = draw.textbbox((0, 0), subtitle, font=font_small)
    subtitle_width = subtitle_bbox[2] - subtitle_bbox[0]
    subtitle_x = (width - subtitle_width) // 2
    
    # 绘制文字
    draw.text((title_x, height + 20), title, fill='black', font=font_large)
    draw.text((subtitle_x, height + 60), subtitle, fill='gray', font=font_small)
    
    # 保存
    filename = "keto-quiz-qrcode-with-text.png"
    new_img.save(filename)
    print(f"✅ 带文字二维码已生成: {filename}")
    print(f"   尺寸: {new_img.size[0]}x{new_img.size[1]} 像素")
    print()

def generate_colored_qrcode():
    """生成彩色二维码"""
    
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    
    qr.add_data(URL)
    qr.make(fit=True)
    
    # 使用品牌色：绿色主题
    img = qr.make_image(fill_color="#2E7D32", back_color="#E8F5E9")
    img = img.convert('RGB')
    
    filename = "keto-quiz-qrcode-colored.png"
    img.save(filename)
    print(f"✅ 彩色二维码已生成: {filename}")
    print(f"   尺寸: {img.size[0]}x{img.size[1]} 像素")
    print(f"   配色: 绿色主题（健康感）")
    print()

if __name__ == "__main__":
    generate_qrcode()
    
    # 在 Windows 上自动打开文件夹
    try:
        os.system('explorer .')
    except:
        pass

