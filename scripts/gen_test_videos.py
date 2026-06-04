"""
测试视频生成脚本 — 为 FactSafe AI 守护系统生成多种场景的测试视频

使用方法:
  pip3 install opencv-python-headless numpy gtts pydub
  python3 scripts/gen_test_videos.py

生成的测试视频会放到 test_videos/ 目录下。

测试案例说明:
  1. safe_cooking.mp4       — 安全内容：正常的做菜教程
  2. scam_investment.mp4    — 投资诈骗：语音+字幕都是诈骗内容
  3. scam_medical.mp4       — 医疗虚假：祖传秘方包治百病
  4. conflict_legit_sub_scam_speech.mp4 — ★ ASR/OCR冲突：字幕写"官方推荐安全产品"，语音说"加微信转账"
  5. conflict_legit_speech_scam_sub.mp4 — ★ ASR/OCR冲突：语音说"正规医院认证"，字幕写"扫码领取免费特效药"
  6. urgency_social_card.mp4 — 紧急通知诈骗：社保卡即将失效

你可以用手机录制真实视频替代这些合成视频，以获得更好的 ASR 效果。
以下是每个测试案例的 **文案建议**（你可以自己念出来录制）：
"""

import os
import sys
import json
import textwrap

# ========== 测试案例文案 ==========

TEST_CASES = [
    {
        "name": "safe_cooking",
        "subtitle": "今天教大家做红烧肉，选用五花肉，先焯水去腥",
        "speech": "大家好，今天教大家做一道经典红烧肉。选用五花肉，先焯水去腥，加入老抽生抽冰糖慢炖一小时。",
        "desc": "✅ 安全内容 — 正常做菜教程，BERT/TF-IDF/GPT 都应判定安全",
    },
    {
        "name": "scam_investment",
        "subtitle": "月入10万！保证收益！无风险投资！加微信立即开始",
        "speech": "各位朋友大家好，我是理财导师王老师。保证月收益百分之三十以上，只要998就能加入VIP群！扫描二维码立即加入！",
        "desc": "🚨 投资诈骗 — 语音+字幕都有诈骗关键词，应判定 danger",
    },
    {
        "name": "scam_medical",
        "subtitle": "祖传秘方！三天治愈糖尿病！医院不想让你知道！",
        "speech": "我家祖传的秘方，专治各种疑难杂症。糖尿病高血压癌症都能治好。三天见效七天痊愈。现在下单买三送一！",
        "desc": "🚨 医疗虚假 — 典型虚假医疗宣传",
    },
    {
        "name": "conflict_legit_sub_scam_speech",
        "subtitle": "国家认证安全产品 正规渠道 官方推荐",
        "speech": "加我微信，私下转账三千块，我帮你免费拿到这个产品。不需要走正规渠道，直接给我打钱就行。",
        "desc": "⚠️ ASR/OCR冲突 — 字幕看起来正规(官方认证)，但语音在诱导转账\n   这是最常见的老人诈骗手法：用正规字幕吸引注意力，语音偷偷夹带私货",
    },
    {
        "name": "conflict_legit_speech_scam_sub",
        "subtitle": "扫码领取免费特效药！限时优惠！加微信立即购买",
        "speech": "大家好，我是某三甲医院的李医生。今天给大家科普一下健康知识。有病要去正规医院看，不要轻信偏方。",
        "desc": "⚠️ ASR/OCR冲突 — 语音是正规医生科普，但字幕在推销免费特效药\n   字幕和语音内容完全矛盾，老人可能只看字幕就上当",
    },
    {
        "name": "urgency_social_card",
        "subtitle": "紧急！您的社保卡即将失效！请立即点击链接更新！",
        "speech": "紧急通知！您的社保卡即将于本月底失效！请立即输入身份证号和银行卡信息进行验证更新！限时48小时！",
        "desc": "🚨 紧急通知诈骗 — 冒充官方紧急通知，诱导提供个人信息",
    },
    {
        "name": "conflict_health_sub_scam_speech",
        "subtitle": "健康养生知识科普 正规医院专家讲座",
        "speech": "这个祖传秘方包治百病，三天见效，加我微信私下买，医院不会告诉你的特效药",
        "desc": "⚠️ ASR/OCR冲突 — 字幕是正规养生科普，语音却在推销三无特效药并诱导加微信",
    },
    {
        "name": "conflict_finance_speech_scam_sub",
        "subtitle": "原始股内部认购 保本年化60% 扫码进群最后名额",
        "speech": "大家投资一定要选正规持牌机构，不要相信保本高息，天上不会掉馅饼",
        "desc": "⚠️ ASR/OCR冲突 — 语音是正确反诈提醒，字幕却在推销保本高息原始股骗局",
    },
]


def print_test_cases():
    """打印所有测试案例的录制指南"""
    print("=" * 70)
    print("  FactSafe AI 测试视频录制指南")
    print("=" * 70)
    print()
    print("你可以用手机 + 剪映/iMovie 制作以下测试视频：")
    print("建议每个视频 10-20 秒，.mov 或 .mp4 格式。")
    print()

    for i, case in enumerate(TEST_CASES, 1):
        print(f"━━━ 案例 {i}: {case['name']}.mov ━━━")
        print(f"  说明: {case['desc']}")
        print()
        print(f"  📝 字幕/画面文字 (用剪映加字幕):")
        print(f"     {case['subtitle']}")
        print()
        print(f"  🎙️ 语音/念的内容 (用手机录音):")
        for line in textwrap.wrap(case['speech'], width=60):
            print(f"     {line}")
        print()

    print("=" * 70)
    print("录制完成后，上传到 FactSafe 系统的「文件上传检测」页面测试。")
    print()
    print("★ 重点测试案例 4 和 5（ASR/OCR 冲突）：")
    print("  - 案例 4：嘴巴说诈骗内容，但字幕显示正规文字")
    print("  - 案例 5：嘴巴说正规内容，但字幕显示诈骗文字")
    print("  系统应该能检测到语音和字幕的矛盾，标记为危险信号。")
    print("=" * 70)


def try_generate_synthetic():
    """
    尝试用 OpenCV + gTTS 生成合成测试视频（如果依赖可用）
    """
    try:
        import cv2
        import numpy as np
    except ImportError:
        print("\n⚠️  opencv-python 未安装，跳过合成视频生成。")
        print("    pip3 install opencv-python-headless numpy")
        return False

    out_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "test_videos")
    os.makedirs(out_dir, exist_ok=True)

    has_tts = False
    try:
        from gtts import gTTS
        has_tts = True
    except ImportError:
        print("⚠️  gTTS 未安装，只生成无声视频（有字幕）。")
        print("    pip3 install gtts pydub")

    for case in TEST_CASES:
        name = case["name"]
        subtitle = case["subtitle"]
        video_path = os.path.join(out_dir, f"{name}.mp4")

        # 生成带字幕的视频帧
        fps = 10
        duration = 5  # 5 seconds
        width, height = 640, 360
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(video_path, fourcc, fps, (width, height))

        # 尝试用 PIL 渲染中文字幕
        use_pil = False
        pil_font = None
        try:
            from PIL import Image, ImageDraw, ImageFont
            use_pil = True
            # macOS 系统中文字体
            font_paths = [
                "/System/Library/Fonts/STHeiti Light.ttc",
                "/System/Library/Fonts/PingFang.ttc",
                "/System/Library/Fonts/Hiragino Sans GB.ttc",
                "/Library/Fonts/Arial Unicode.ttf",
            ]
            for fp in font_paths:
                if os.path.exists(fp):
                    pil_font = ImageFont.truetype(fp, 22)
                    break
            if pil_font is None:
                pil_font = ImageFont.load_default()
        except ImportError:
            pass

        for _ in range(fps * duration):
            if use_pil:
                # 用 PIL 创建带中文字幕的帧
                img = Image.new("RGB", (width, height), (30, 30, 50))
                draw = ImageDraw.Draw(img)
                # 自动换行
                max_chars = 20
                lines = [subtitle[i:i+max_chars] for i in range(0, len(subtitle), max_chars)]
                y_start = height // 2 - len(lines) * 15
                for j, line in enumerate(lines):
                    draw.text((40, y_start + j * 32), line, fill=(255, 255, 255), font=pil_font)
                frame = np.array(img)
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            else:
                frame = np.zeros((height, width, 3), dtype=np.uint8)
                frame[:] = (30, 30, 50)
                cv2.putText(frame, subtitle[:50], (20, height // 2),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            writer.write(frame)

        writer.release()
        print(f"  ✅ 生成: {video_path}  ({'带中文字幕' if use_pil else '仅英文字幕'})")

    # 如果有 gTTS，尝试添加音频
    if has_tts:
        try:
            from pydub import AudioSegment
            import subprocess
            import tempfile

            for case in TEST_CASES:
                name = case["name"]
                speech = case["speech"]
                video_path = os.path.join(out_dir, f"{name}.mp4")
                final_path = os.path.join(out_dir, f"{name}_with_audio.mp4")

                # 生成 TTS 音频
                tts = gTTS(text=speech, lang="zh-cn", slow=False)
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                    tts.save(tmp.name)
                    audio_path = tmp.name

                # 用 ffmpeg 合并
                ffmpeg = os.path.expanduser("~/bin/ffmpeg")
                if not os.path.exists(ffmpeg):
                    ffmpeg = "ffmpeg"

                cmd = [
                    ffmpeg, "-y",
                    "-i", video_path,
                    "-i", audio_path,
                    "-c:v", "copy",
                    "-c:a", "aac",
                    "-shortest",
                    final_path,
                ]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    # 替换原文件
                    os.replace(final_path, video_path)
                    print(f"  🎙️ 添加音频: {video_path}")
                else:
                    print(f"  ⚠️  ffmpeg 合并失败: {name}")

                os.unlink(audio_path)
        except Exception as e:
            print(f"  ⚠️  音频合成失败: {e}")

    print(f"\n  📁 测试视频目录: {out_dir}")
    return True


# ========== 跨模态错位 OOD 评测集（突破点1：联合推理对照实验用）==========

# 额外的"纯文本对"错位评测样本（无需生成视频即可评估 OCR/ASR 联合推理）
# label: "mismatch" = 跨模态错位(危险), "consistent_scam" = 双模态都诈骗, "consistent_safe" = 双模态都安全
MISMATCH_EVAL_EXTRA = [
    {"ocr_text": "国家认证安全产品 官方推荐 正规渠道", "asr_text": "加我微信私下转账三千块我帮你免费拿到不用走正规渠道", "label": "mismatch", "expected_risk": "danger"},
    {"ocr_text": "扫码领取免费特效药 限时优惠 加微信购买", "asr_text": "我是三甲医院李医生科普健康知识有病要去正规医院不要轻信偏方", "label": "mismatch", "expected_risk": "danger"},
    {"ocr_text": "健康养生知识科普 正规医院专家讲座", "asr_text": "这个祖传秘方包治百病三天见效加我微信私下买", "label": "mismatch", "expected_risk": "danger"},
    {"ocr_text": "原始股内部认购 保本年化60% 扫码进群最后名额", "asr_text": "投资要选正规持牌机构不要相信保本高息天上不会掉馅饼", "label": "mismatch", "expected_risk": "danger"},
    {"ocr_text": "公安反诈宣传 切勿向陌生人转账", "asr_text": "赶紧把验证码发给我不然你的账户马上就冻结了", "label": "mismatch", "expected_risk": "danger"},
    {"ocr_text": "央视权威报道 老年健康讲座", "asr_text": "充值五千返三万原始股稳赚不赔名额有限今天截止", "label": "mismatch", "expected_risk": "danger"},
    # 双模态一致的诈骗（联合推理也应判危险，但非"错位"）
    {"ocr_text": "月入十万保证收益无风险投资加微信", "asr_text": "保证月收益百分之三十只要998加入VIP群扫码立即加入", "label": "consistent_scam", "expected_risk": "danger"},
    {"ocr_text": "祖传秘方三天治愈糖尿病医院不想让你知道", "asr_text": "我家祖传秘方专治疑难杂症糖尿病高血压都能治好下单买三送一", "label": "consistent_scam", "expected_risk": "danger"},
    # 双模态一致的安全内容（联合推理应判安全）
    {"ocr_text": "今天教大家做红烧肉 五花肉焯水去腥", "asr_text": "大家好今天教大家做一道经典红烧肉选用五花肉先焯水去腥", "label": "consistent_safe", "expected_risk": "safe"},
    {"ocr_text": "社区老年大学书法班招生 免费报名", "asr_text": "欢迎各位老年朋友报名书法班每周三上午在社区活动中心免费教学", "label": "consistent_safe", "expected_risk": "safe"},
]


def write_mismatch_eval_set():
    """
    生成跨模态错位 OOD 评测集 -> data/raw/crossmodal_mismatch_eval.json
    供 scripts/run_evaluation.py 做"单模态独立分析 vs 联合推理"对照实验。
    """
    out_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "raw")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "crossmodal_mismatch_eval.json")

    samples = []
    # 来自合成视频文案（重点是 conflict_* 错位案例）
    for case in TEST_CASES:
        name = case["name"]
        if name.startswith("conflict_"):
            label = "mismatch"
            expected = "danger"
        elif name.startswith("scam_") or name.startswith("urgency_"):
            label = "consistent_scam"
            expected = "danger"
        else:
            label = "consistent_safe"
            expected = "safe"
        samples.append({
            "ocr_text": case["subtitle"],
            "asr_text": case["speech"],
            "label": label,
            "expected_risk": expected,
            "source": f"gen_test_videos:{name}",
        })
    # 额外纯文本对
    for s in MISMATCH_EVAL_EXTRA:
        s = dict(s)
        s.setdefault("source", "mismatch_eval_extra")
        samples.append(s)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(samples, f, ensure_ascii=False, indent=2)

    from collections import Counter
    dist = Counter(s["label"] for s in samples)
    print(f"✅ 跨模态错位评测集已生成: {out_path}")
    print(f"   样本数: {len(samples)} | 分布: {dict(dist)}")
    return out_path


if __name__ == "__main__":
    if "--eval-set" in sys.argv:
        write_mismatch_eval_set()
        sys.exit(0)

    print_test_cases()

    if "--generate" in sys.argv:
        print("\n正在生成合成测试视频...\n")
        try_generate_synthetic()
        write_mismatch_eval_set()
    else:
        print("\n💡 如需自动生成合成视频，运行:")
        print("   python3 scripts/gen_test_videos.py --generate")
        print("\n💡 仅生成跨模态错位评测集(无需 opencv):")
        print("   python3 scripts/gen_test_videos.py --eval-set")
        print("\n💡 推荐：用手机按照上面的文案自行录制，效果更真实。")
