"""Mandarin phrase fixtures for TTS benchmark validation."""

# Basic greetings and common phrases
# Format: dict with text, pinyin, meaning keys

MANDARIN_PHRASES = {
    "ni_hao": {
        "text": "你好",
        "pinyin": "nǐ hǎo",
        "meaning": "Hello",
    },
    "xie_xie": {
        "text": "谢谢",
        "pinyin": "xiè xie",
        "meaning": "Thank you",
    },
    "zai_jian": {
        "text": "再见",
        "pinyin": "zài jiàn",
        "meaning": "Goodbye",
    },
    "wo_jiao": {
        "text": "我叫小明",
        "pinyin": "wǒ jiào xiǎo míng",
        "meaning": "My name is Xiao Ming",
    },
    "qing_zai_shuo": {
        "text": "请再说一次",
        "pinyin": "qǐng zài shuō yī cì",
        "meaning": "Please say that again",
    },
    "ni_jiao_shen_me": {
        "text": "你叫什么？",
        "pinyin": "nǐ jiào shén me?",
        "meaning": "What is your name?",
    },
    "hen_gao_xing": {
        "text": "很高兴认识你",
        "pinyin": "hěn gāo xìng rèn shi nǐ",
        "meaning": "Nice to meet you",
    },
}

# Full text for TTS testing (characters only)
MANDARIN_TEXT_SET = {
    "short": "你好",
    "medium": "谢谢，再见",
    "long": "我叫小明，请再说一次，很高兴认识你",
}

# Recommended voice for Mandarin (mlx-audio Kokoro model uses zf_ voices)
# Note: kokoro-onnx does NOT support Mandarin (espeak-ng only supports en-us/en-gb)
MANDARIN_VOICE = "zf_xiaoyi"

# Recommended speed for beginner learners (slower is clearer)
MANDARIN_SPEED = 0.9
