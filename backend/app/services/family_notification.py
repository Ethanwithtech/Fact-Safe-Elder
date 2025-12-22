"""
家人通知服务
当检测到高风险内容时，自动通知家人

支持的通知方式:
1. 微信消息（通过企业微信/公众号模板消息）
2. 短信提醒
3. 邮件通知
4. App推送通知
"""

import os
import asyncio
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
from loguru import logger

# HTTP客户端
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

# 邮件发送
try:
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    EMAIL_AVAILABLE = True
except ImportError:
    EMAIL_AVAILABLE = False


class NotificationType(Enum):
    """通知类型"""
    WECHAT = "wechat"
    SMS = "sms"
    EMAIL = "email"
    PUSH = "push"


class RiskLevel(Enum):
    """风险等级"""
    SAFE = "safe"
    WARNING = "warning"
    DANGER = "danger"


@dataclass
class FamilyContact:
    """家人联系方式"""
    name: str
    relationship: str  # 儿子、女儿、孙子等
    phone: Optional[str] = None
    email: Optional[str] = None
    wechat_openid: Optional[str] = None
    notification_preferences: List[NotificationType] = None
    notification_threshold: RiskLevel = RiskLevel.DANGER
    
    def __post_init__(self):
        if self.notification_preferences is None:
            self.notification_preferences = [NotificationType.WECHAT, NotificationType.SMS]


@dataclass
class AlertEvent:
    """警报事件"""
    event_id: str
    user_id: str
    risk_level: RiskLevel
    content_summary: str
    detection_time: datetime
    reasons: List[str]
    suggestions: List[str]
    platform: str  # 抖音、微信等
    content_url: Optional[str] = None
    handled: bool = False
    notified_contacts: List[str] = None
    
    def __post_init__(self):
        if self.notified_contacts is None:
            self.notified_contacts = []


@dataclass
class NotificationConfig:
    """通知配置"""
    # 微信配置
    wechat_app_id: str = ""
    wechat_app_secret: str = ""
    wechat_template_id: str = ""
    
    # 短信配置
    sms_api_key: str = ""
    sms_api_secret: str = ""
    sms_sign_name: str = "AI守护"
    sms_template_code: str = ""
    
    # 邮件配置
    smtp_host: str = "smtp.qq.com"
    smtp_port: int = 465
    smtp_user: str = ""
    smtp_password: str = ""
    email_from: str = ""
    
    # 推送配置
    push_api_key: str = ""
    push_api_url: str = ""
    
    # 通知限制
    max_notifications_per_hour: int = 5
    min_notification_interval: int = 300  # 秒


class NotificationRateLimiter:
    """
    通知频率限制器
    防止过度通知
    """
    
    def __init__(self, max_per_hour: int = 5, min_interval: int = 300):
        self.max_per_hour = max_per_hour
        self.min_interval = min_interval
        self.notification_history: Dict[str, List[datetime]] = {}
    
    def can_notify(self, contact_id: str) -> bool:
        """检查是否可以发送通知"""
        now = datetime.now()
        
        if contact_id not in self.notification_history:
            return True
        
        history = self.notification_history[contact_id]
        
        # 检查最小间隔
        if history:
            last_notification = history[-1]
            if (now - last_notification).total_seconds() < self.min_interval:
                return False
        
        # 检查每小时限制
        hour_ago = now - timedelta(hours=1)
        recent_count = sum(1 for t in history if t > hour_ago)
        
        return recent_count < self.max_per_hour
    
    def record_notification(self, contact_id: str):
        """记录通知"""
        if contact_id not in self.notification_history:
            self.notification_history[contact_id] = []
        
        self.notification_history[contact_id].append(datetime.now())
        
        # 清理旧记录（保留24小时内的）
        day_ago = datetime.now() - timedelta(days=1)
        self.notification_history[contact_id] = [
            t for t in self.notification_history[contact_id] if t > day_ago
        ]


class FamilyNotificationService:
    """
    家人通知服务
    """
    
    def __init__(self, config: Optional[NotificationConfig] = None):
        self.config = config or NotificationConfig()
        self.rate_limiter = NotificationRateLimiter(
            max_per_hour=self.config.max_notifications_per_hour,
            min_interval=self.config.min_notification_interval
        )
        
        # 事件历史
        self.event_history: Dict[str, AlertEvent] = {}
        
        # HTTP客户端
        self.http_client = httpx.AsyncClient() if HTTPX_AVAILABLE else None
        
        logger.info("家人通知服务已初始化")
    
    async def notify_family(
        self,
        event: AlertEvent,
        contacts: List[FamilyContact]
    ) -> Dict[str, bool]:
        """
        通知家人
        
        Args:
            event: 警报事件
            contacts: 家人联系方式列表
            
        Returns:
            每个联系人的通知结果
        """
        results = {}
        
        for contact in contacts:
            # 检查是否需要通知
            if not self._should_notify(event, contact):
                results[contact.name] = False
                continue
            
            # 检查频率限制
            contact_id = self._get_contact_id(contact)
            if not self.rate_limiter.can_notify(contact_id):
                logger.warning(f"通知频率限制: {contact.name}")
                results[contact.name] = False
                continue
            
            # 发送通知
            success = await self._send_notifications(event, contact)
            results[contact.name] = success
            
            if success:
                self.rate_limiter.record_notification(contact_id)
                event.notified_contacts.append(contact.name)
        
        # 保存事件
        self.event_history[event.event_id] = event
        
        return results
    
    def _should_notify(self, event: AlertEvent, contact: FamilyContact) -> bool:
        """检查是否应该通知"""
        risk_order = {
            RiskLevel.SAFE: 0,
            RiskLevel.WARNING: 1,
            RiskLevel.DANGER: 2
        }
        
        return risk_order[event.risk_level] >= risk_order[contact.notification_threshold]
    
    def _get_contact_id(self, contact: FamilyContact) -> str:
        """生成联系人ID"""
        data = f"{contact.name}_{contact.phone}_{contact.email}"
        return hashlib.md5(data.encode()).hexdigest()[:12]
    
    async def _send_notifications(
        self,
        event: AlertEvent,
        contact: FamilyContact
    ) -> bool:
        """发送通知"""
        success = False
        
        for notification_type in contact.notification_preferences:
            try:
                if notification_type == NotificationType.WECHAT:
                    result = await self._send_wechat(event, contact)
                elif notification_type == NotificationType.SMS:
                    result = await self._send_sms(event, contact)
                elif notification_type == NotificationType.EMAIL:
                    result = await self._send_email(event, contact)
                elif notification_type == NotificationType.PUSH:
                    result = await self._send_push(event, contact)
                else:
                    result = False
                
                if result:
                    success = True
                    logger.info(f"通知发送成功: {contact.name} via {notification_type.value}")
                    break
                    
            except Exception as e:
                logger.error(f"通知发送失败: {contact.name} via {notification_type.value}: {e}")
        
        return success
    
    async def _send_wechat(self, event: AlertEvent, contact: FamilyContact) -> bool:
        """
        发送微信通知
        通过微信公众号模板消息
        """
        if not contact.wechat_openid:
            return False
        
        if not self.config.wechat_app_id or not self.config.wechat_template_id:
            logger.warning("微信配置不完整")
            return False
        
        try:
            # 获取access_token
            access_token = await self._get_wechat_access_token()
            if not access_token:
                return False
            
            # 构建消息
            message = {
                "touser": contact.wechat_openid,
                "template_id": self.config.wechat_template_id,
                "data": {
                    "first": {
                        "value": f"⚠️ {contact.relationship}您好，检测到可疑信息",
                        "color": "#FF0000"
                    },
                    "keyword1": {
                        "value": self._get_risk_level_text(event.risk_level),
                        "color": "#FF0000" if event.risk_level == RiskLevel.DANGER else "#FFA500"
                    },
                    "keyword2": {
                        "value": event.content_summary[:50] + "...",
                        "color": "#333333"
                    },
                    "keyword3": {
                        "value": event.detection_time.strftime("%Y-%m-%d %H:%M"),
                        "color": "#333333"
                    },
                    "keyword4": {
                        "value": event.platform,
                        "color": "#333333"
                    },
                    "remark": {
                        "value": "建议：" + (event.suggestions[0] if event.suggestions else "请关注老人的网络使用情况"),
                        "color": "#666666"
                    }
                }
            }
            
            # 发送请求
            url = f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={access_token}"
            
            if self.http_client:
                response = await self.http_client.post(url, json=message)
                result = response.json()
                return result.get('errcode', -1) == 0
            
            return False
            
        except Exception as e:
            logger.error(f"微信通知失败: {e}")
            return False
    
    async def _get_wechat_access_token(self) -> Optional[str]:
        """获取微信access_token"""
        if not self.http_client:
            return None
        
        url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={self.config.wechat_app_id}&secret={self.config.wechat_app_secret}"
        
        try:
            response = await self.http_client.get(url)
            result = response.json()
            return result.get('access_token')
        except Exception as e:
            logger.error(f"获取微信access_token失败: {e}")
            return None
    
    async def _send_sms(self, event: AlertEvent, contact: FamilyContact) -> bool:
        """
        发送短信通知
        支持阿里云短信/腾讯云短信
        """
        if not contact.phone:
            return False
        
        if not self.config.sms_api_key:
            logger.warning("短信配置不完整")
            return False
        
        try:
            # 构建短信内容
            risk_text = self._get_risk_level_text(event.risk_level)
            content = f"【AI守护】您的家人正在观看可疑内容，风险等级：{risk_text}。建议：{event.suggestions[0] if event.suggestions else '请关注老人网络使用情况'}"
            
            # 这里应该调用实际的短信API
            # 示例：阿里云短信
            # from aliyunsdkcore.client import AcsClient
            # from aliyunsdkdysmsapi.request.v20170525.SendSmsRequest import SendSmsRequest
            
            logger.info(f"[模拟] 发送短信到 {contact.phone}: {content}")
            
            # 模拟发送成功
            return True
            
        except Exception as e:
            logger.error(f"短信发送失败: {e}")
            return False
    
    async def _send_email(self, event: AlertEvent, contact: FamilyContact) -> bool:
        """发送邮件通知"""
        if not contact.email:
            return False
        
        if not EMAIL_AVAILABLE or not self.config.smtp_user:
            logger.warning("邮件配置不完整")
            return False
        
        try:
            # 构建邮件
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"⚠️ AI守护提醒：检测到{self._get_risk_level_text(event.risk_level)}内容"
            msg['From'] = self.config.email_from or self.config.smtp_user
            msg['To'] = contact.email
            
            # HTML内容
            html = self._build_email_html(event, contact)
            msg.attach(MIMEText(html, 'html', 'utf-8'))
            
            # 发送邮件
            with smtplib.SMTP_SSL(self.config.smtp_host, self.config.smtp_port) as server:
                server.login(self.config.smtp_user, self.config.smtp_password)
                server.send_message(msg)
            
            return True
            
        except Exception as e:
            logger.error(f"邮件发送失败: {e}")
            return False
    
    def _build_email_html(self, event: AlertEvent, contact: FamilyContact) -> str:
        """构建邮件HTML内容"""
        risk_color = "#FF0000" if event.risk_level == RiskLevel.DANGER else "#FFA500"
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: {risk_color}; color: white; padding: 20px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 20px; border-radius: 0 0 10px 10px; }}
                .info-row {{ margin: 10px 0; padding: 10px; background: white; border-radius: 5px; }}
                .label {{ font-weight: bold; color: #666; }}
                .reasons {{ background: #fff3cd; padding: 15px; border-radius: 5px; margin: 10px 0; }}
                .suggestions {{ background: #d4edda; padding: 15px; border-radius: 5px; margin: 10px 0; }}
                .footer {{ text-align: center; margin-top: 20px; color: #999; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>⚠️ AI守护安全提醒</h1>
                    <p>检测到可疑内容</p>
                </div>
                <div class="content">
                    <p>尊敬的{contact.relationship}：</p>
                    <p>您的家人在使用手机时，AI守护系统检测到了可能存在风险的内容。</p>
                    
                    <div class="info-row">
                        <span class="label">风险等级：</span>
                        <span style="color: {risk_color}; font-weight: bold;">{self._get_risk_level_text(event.risk_level)}</span>
                    </div>
                    
                    <div class="info-row">
                        <span class="label">检测时间：</span>
                        {event.detection_time.strftime("%Y年%m月%d日 %H:%M")}
                    </div>
                    
                    <div class="info-row">
                        <span class="label">内容来源：</span>
                        {event.platform}
                    </div>
                    
                    <div class="info-row">
                        <span class="label">内容摘要：</span>
                        {event.content_summary[:100]}...
                    </div>
                    
                    <div class="reasons">
                        <strong>🔍 检测到的风险因素：</strong>
                        <ul>
                            {''.join(f'<li>{r}</li>' for r in event.reasons[:3])}
                        </ul>
                    </div>
                    
                    <div class="suggestions">
                        <strong>💡 建议措施：</strong>
                        <ul>
                            {''.join(f'<li>{s}</li>' for s in event.suggestions[:3])}
                        </ul>
                    </div>
                    
                    <p>请适时与老人沟通，帮助他们识别和防范网络诈骗。</p>
                </div>
                <div class="footer">
                    <p>本邮件由AI守护系统自动发送</p>
                    <p>如有疑问，请登录App查看详情</p>
                </div>
            </div>
        </body>
        </html>
        """
        return html
    
    async def _send_push(self, event: AlertEvent, contact: FamilyContact) -> bool:
        """发送App推送通知"""
        if not self.config.push_api_key:
            return False
        
        try:
            # 构建推送内容
            push_data = {
                "title": f"⚠️ AI守护提醒",
                "body": f"检测到{self._get_risk_level_text(event.risk_level)}内容：{event.content_summary[:30]}...",
                "data": {
                    "event_id": event.event_id,
                    "risk_level": event.risk_level.value,
                    "type": "risk_alert"
                }
            }
            
            # 这里应该调用实际的推送API
            logger.info(f"[模拟] 发送推送通知: {push_data}")
            
            return True
            
        except Exception as e:
            logger.error(f"推送通知失败: {e}")
            return False
    
    def _get_risk_level_text(self, level: RiskLevel) -> str:
        """获取风险等级文本"""
        return {
            RiskLevel.SAFE: "安全",
            RiskLevel.WARNING: "可疑",
            RiskLevel.DANGER: "高风险"
        }.get(level, "未知")
    
    def get_event_history(
        self,
        user_id: Optional[str] = None,
        limit: int = 20
    ) -> List[AlertEvent]:
        """获取事件历史"""
        events = list(self.event_history.values())
        
        if user_id:
            events = [e for e in events if e.user_id == user_id]
        
        # 按时间排序
        events.sort(key=lambda x: x.detection_time, reverse=True)
        
        return events[:limit]
    
    async def cleanup(self):
        """清理资源"""
        if self.http_client:
            await self.http_client.aclose()


class MultiLevelAlertSystem:
    """
    多级预警系统
    
    根据风险等级和用户设置执行不同的预警措施
    """
    
    # 预警级别配置
    ALERT_LEVELS = {
        RiskLevel.SAFE: {
            "color": "#52c41a",  # 绿色
            "icon": "✅",
            "title": "内容安全",
            "action": "normal",  # 正常显示
            "notify_family": False,
            "play_sound": False,
            "block_content": False
        },
        RiskLevel.WARNING: {
            "color": "#faad14",  # 黄色
            "icon": "⚠️",
            "title": "注意风险",
            "action": "warn",  # 警告提示
            "notify_family": False,  # 默认不通知
            "play_sound": True,
            "block_content": False
        },
        RiskLevel.DANGER: {
            "color": "#ff4d4f",  # 红色
            "icon": "🚨",
            "title": "高风险警告",
            "action": "block",  # 阻断并警告
            "notify_family": True,  # 自动通知家人
            "play_sound": True,
            "block_content": True
        }
    }
    
    def __init__(self, notification_service: FamilyNotificationService):
        self.notification_service = notification_service
        
        # 用户设置缓存
        self.user_settings: Dict[str, Dict] = {}
        
        logger.info("多级预警系统已初始化")
    
    def get_alert_config(self, risk_level: RiskLevel, user_id: Optional[str] = None) -> Dict:
        """
        获取预警配置
        
        Args:
            risk_level: 风险等级
            user_id: 用户ID（用于获取个性化设置）
            
        Returns:
            预警配置
        """
        base_config = self.ALERT_LEVELS[risk_level].copy()
        
        # 应用用户设置
        if user_id and user_id in self.user_settings:
            user_config = self.user_settings[user_id]
            
            # 敏感度调整
            sensitivity = user_config.get('sensitivity', 'normal')
            if sensitivity == 'high':
                # 高敏感度：WARNING也通知家人
                if risk_level == RiskLevel.WARNING:
                    base_config['notify_family'] = True
            elif sensitivity == 'low':
                # 低敏感度：只有DANGER通知
                if risk_level != RiskLevel.DANGER:
                    base_config['notify_family'] = False
            
            # 声音设置
            if not user_config.get('enable_sound', True):
                base_config['play_sound'] = False
        
        return base_config
    
    async def execute_alert(
        self,
        risk_level: RiskLevel,
        event: AlertEvent,
        family_contacts: List[FamilyContact],
        user_id: Optional[str] = None
    ) -> Dict:
        """
        执行预警
        
        Args:
            risk_level: 风险等级
            event: 警报事件
            family_contacts: 家人联系方式
            user_id: 用户ID
            
        Returns:
            预警执行结果
        """
        config = self.get_alert_config(risk_level, user_id)
        
        result = {
            "risk_level": risk_level.value,
            "config": config,
            "notifications_sent": {},
            "actions_taken": []
        }
        
        # 播放警告音
        if config['play_sound']:
            result['actions_taken'].append("play_warning_sound")
        
        # 阻断内容
        if config['block_content']:
            result['actions_taken'].append("block_content")
        
        # 通知家人
        if config['notify_family'] and family_contacts:
            notification_results = await self.notification_service.notify_family(
                event, family_contacts
            )
            result['notifications_sent'] = notification_results
            result['actions_taken'].append("notify_family")
        
        logger.info(f"预警执行完成: {risk_level.value}, 动作: {result['actions_taken']}")
        
        return result
    
    def update_user_settings(self, user_id: str, settings: Dict):
        """更新用户设置"""
        self.user_settings[user_id] = settings
    
    def get_user_settings(self, user_id: str) -> Dict:
        """获取用户设置"""
        return self.user_settings.get(user_id, {
            "sensitivity": "normal",
            "enable_sound": True,
            "auto_notify_family": True,
            "notification_threshold": RiskLevel.DANGER.value
        })


# 全局服务实例
_notification_service: Optional[FamilyNotificationService] = None
_alert_system: Optional[MultiLevelAlertSystem] = None


def get_notification_service() -> FamilyNotificationService:
    """获取通知服务实例"""
    global _notification_service
    if _notification_service is None:
        _notification_service = FamilyNotificationService()
    return _notification_service


def get_alert_system() -> MultiLevelAlertSystem:
    """获取预警系统实例"""
    global _alert_system
    if _alert_system is None:
        _alert_system = MultiLevelAlertSystem(get_notification_service())
    return _alert_system


# 导出
__all__ = [
    'NotificationType',
    'RiskLevel',
    'FamilyContact',
    'AlertEvent',
    'NotificationConfig',
    'FamilyNotificationService',
    'MultiLevelAlertSystem',
    'get_notification_service',
    'get_alert_system'
]





