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
        "text": "我叫...",
        "pinyin": "wǒ jiào ...",
        "meaning": "My name is ...",
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
    "long": "我叫... 请再说一次 很高兴认识你",
}

# Recommended voice for Mandarin (Kokoro supports zh-CN)
MANDARIN_VOICE = "zh"

# Recommended speed for beginner learners (slower is clearer)
MANDARIN_SPEED = 0.9
