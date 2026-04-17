"""
个人身份信息 (PII) 脱敏模块
基于正则表达式检测和替换敏感信息

功能:
- 手机号码脱敏 (11 位中国手机号)
- 身份证号脱敏 (18 位中国身份证)
- 银行卡号脱敏 (16-19 位)
- 地址信息脱敏 (省市区街道)
- Email 脱敏
- 其他数字序列脱敏 (可能的账号/密码)

引用: FYP Final Report Section 5.5.1 - Privacy Protection
"""

import re
from typing import Dict, List, Tuple
from loguru import logger


class PIIRedactor:
    """PII 脱敏器"""
    
    # 中国手机号: 1[3-9]开头 + 9位数字
    PHONE_PATTERN = re.compile(r'1[3-9]\d{9}')
    
    # 中国身份证: 18位数字或17位数字+X
    ID_CARD_PATTERN = re.compile(r'\d{17}[\dXx]|\d{15}')
    
    # 银行卡号: 16-19位数字
    BANK_CARD_PATTERN = re.compile(r'\d{16,19}')
    
    # Email 地址
    EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
    
    # 地址 (简化版,匹配"省市区县+路街道+数字"模式)
    ADDRESS_PATTERN = re.compile(r'[省市区县]{1,3}.*?[路街道巷弄里]{1,2}\d+')
    
    # 连续6位以上数字 (可能的账号/验证码,在已检测到其他PII时才触发)
    LONG_NUMBER_PATTERN = re.compile(r'\b\d{6,}\b')
    
    # QQ号: 5-11位数字
    QQ_PATTERN = re.compile(r'\b[1-9]\d{4,10}\b')
    
    # 微信号: wx开头或类似账号格式
    WECHAT_PATTERN = re.compile(r'\b(?:wx|WX|微信)[a-zA-Z0-9_-]{4,20}\b|(?:微信号|微信|WeChat)[：:]\s*[a-zA-Z0-9_-]{4,20}')
    
    def __init__(self, aggressive: bool = False):
        """
        初始化 PII 脱敏器
        
        Args:
            aggressive: 是否启用激进模式 (脱敏更多可能的敏感信息,可能误伤)
        """
        self.aggressive = aggressive
        self.redaction_log: List[Tuple[str, str]] = []  # (pattern_name, matched_value)
    
    def redact(self, text: str) -> str:
        """
        脱敏文本中的 PII
        
        Args:
            text: 原始文本
            
        Returns:
            脱敏后的文本
        """
        if not text or not text.strip():
            return text
        
        self.redaction_log.clear()
        original_text = text
        
        # 1. 手机号脱敏
        text, phone_count = self._redact_pattern(
            text, 
            self.PHONE_PATTERN, 
            '<PHONE_REDACTED>',
            'phone'
        )
        
        # 2. 身份证脱敏
        text, id_count = self._redact_pattern(
            text,
            self.ID_CARD_PATTERN,
            '<ID_CARD_REDACTED>',
            'id_card'
        )
        
        # 3. 银行卡脱敏 (但排除手机号的16位片段)
        text, bank_count = self._redact_bank_card(text)
        
        # 4. Email 脱敏
        text, email_count = self._redact_pattern(
            text,
            self.EMAIL_PATTERN,
            '<EMAIL_REDACTED>',
            'email'
        )
        
        # 5. 地址脱敏
        text, addr_count = self._redact_pattern(
            text,
            self.ADDRESS_PATTERN,
            '<ADDRESS_REDACTED>',
            'address'
        )
        
        # 6. QQ 号脱敏 (仅在激进模式或已检测到其他 PII 时)
        if self.aggressive or len(self.redaction_log) > 0:
            text, qq_count = self._redact_pattern(
                text,
                self.QQ_PATTERN,
                '<QQ_REDACTED>',
                'qq',
                min_length=5
            )
        
        # 7. 微信号脱敏
        text, wx_count = self._redact_pattern(
            text,
            self.WECHAT_PATTERN,
            '<WECHAT_REDACTED>',
            'wechat'
        )
        
        # 8. 其他长数字序列 (仅在激进模式 + 已检测到其他 PII 时)
        if self.aggressive and len(self.redaction_log) > 2:
            text, long_num_count = self._redact_pattern(
                text,
                self.LONG_NUMBER_PATTERN,
                '<NUMBER_REDACTED>',
                'long_number'
            )
        
        # 日志记录
        if self.redaction_log:
            redaction_summary = ', '.join(
                f"{name}({val[:4]}...)" for name, val in self.redaction_log[:5]
            )
            logger.info(f"PII 脱敏: {len(self.redaction_log)} 项 | {redaction_summary}")
        
        return text
    
    def _redact_pattern(
        self, 
        text: str, 
        pattern: re.Pattern, 
        replacement: str,
        name: str,
        min_length: int = 0
    ) -> Tuple[str, int]:
        """
        使用正则表达式脱敏
        
        Args:
            text: 输入文本
            pattern: 正则模式
            replacement: 替换文本
            name: 模式名称 (用于日志)
            min_length: 最小匹配长度 (过滤短匹配)
            
        Returns:
            (脱敏后文本, 匹配数量)
        """
        matches = pattern.findall(text)
        count = 0
        
        for match in matches:
            if len(match) >= min_length:
                text = text.replace(match, replacement, 1)
                self.redaction_log.append((name, match))
                count += 1
        
        return text, count
    
    def _redact_bank_card(self, text: str) -> Tuple[str, int]:
        """
        脱敏银行卡号 (特殊处理以避免误伤手机号)
        
        银行卡号通常为 16/19 位,手机号为 11 位
        需要避免将两个手机号连在一起误判为银行卡
        """
        matches = self.BANK_CARD_PATTERN.findall(text)
        count = 0
        
        for match in matches:
            # 检查是否已经被标记为手机号
            if '<PHONE_REDACTED>' in text:
                continue
            
            # 检查是否为两个11位数字拼接 (可能是两个手机号)
            if len(match) == 22 and match[:11].startswith('1') and match[11:].startswith('1'):
                continue
            
            text = text.replace(match, '<BANK_CARD_REDACTED>', 1)
            self.redaction_log.append(('bank_card', match))
            count += 1
        
        return text, count
    
    def get_redaction_summary(self) -> Dict[str, int]:
        """
        获取脱敏统计摘要
        
        Returns:
            {pattern_name: count} 字典
        """
        summary = {}
        for name, _ in self.redaction_log:
            summary[name] = summary.get(name, 0) + 1
        return summary


# 全局单例
_redactor: PIIRedactor = None


def get_redactor(aggressive: bool = False) -> PIIRedactor:
    """获取 PII 脱敏器实例"""
    global _redactor
    if _redactor is None:
        _redactor = PIIRedactor(aggressive=aggressive)
    return _redactor


def redact_pii(text: str, aggressive: bool = False) -> str:
    """
    便捷函数: 脱敏文本中的 PII
    
    Args:
        text: 输入文本
        aggressive: 是否启用激进模式
        
    Returns:
        脱敏后的文本
    """
    redactor = get_redactor(aggressive=aggressive)
    return redactor.redact(text)


# 导出
__all__ = ['PIIRedactor', 'get_redactor', 'redact_pii']
