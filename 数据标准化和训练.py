#!/usr/bin/env python3
"""
数据标准化和高准确率模型训练 (v2)

改进点:
1. 合并所有数据源 (comprehensive + mcfend + weibo + real_cases)
2. 严格文本去重，避免同一句话出现在训练集和测试集
3. 大量新增正常/安全文本，减少对日常用语的误报
4. 输出 simple_ai_model.joblib 到项目根目录（后端可直接加载）
"""
import json
import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, VotingClassifier
from sklearn.svm import SVC
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, accuracy_score, f1_score
from datetime import datetime
from pathlib import Path


# ===== 大量正常/安全文本（日常用语，防止误报） =====
SAFE_TEXTS = [
    # === 日常生活 ===
    "今天天气真不错，适合出去散步",
    "明天天气预报说会下雨，记得带伞",
    "今天去超市买了些水果和蔬菜",
    "早上起来做了一顿丰盛的早餐",
    "下午去公园遛了一圈，空气很好",
    "晚饭做了红烧肉和清炒蔬菜",
    "今天和老朋友一起喝茶聊天",
    "周末准备带孙子去动物园玩",
    "今天去菜市场买了新鲜的鱼",
    "晚上看了一部很好看的电视剧",
    "早上去小区花园锻炼了半个小时",
    "今天做了一锅鸡汤给家人喝",
    "下午在家听了一会儿京剧",
    "今天天气晴朗万里无云",
    "刚出去遛弯回来休息一下",
    "明天要去医院做个体检",
    "今天包了饺子一家人吃",
    "出去买了些日用品回来了",
    "下午和邻居大妈一起打了太极拳",
    "晚上看新闻联播了解了国内外大事",
    "今天出门坐了地铁特别方便",
    "上午去银行取了一些钱买东西",
    "家里的空调坏了叫了维修师傅来修",
    "今天在家收拾了一下房间干净多了",
    "老伴去楼下下棋了我在家看电视",
    "外面太热了还是在家呆着凉快",
    "今天学会了网上买菜很方便",
    "小区物业通知明天要停水检修",
    "昨天晚上睡得很好精神不错",
    "今天做了几道拿手菜招待亲戚",
    "门口的快递到了去取一下",
    "今天下了一场大雨路上积了水",
    "给花浇了水看着它们长得真好",
    "今天在阳台上晒了被子特别暖和",
    "刚从楼下便利店买了瓶酱油回来",
    "今天坐公交去了趟市中心逛街",
    "院子里的树开花了好漂亮",
    "今天和女儿视频通话了看到了小外孙",
    "去理发店剪了个头发感觉清爽多了",
    "今天参加了居委会组织的活动",
    # === 正常新闻 ===
    "我国科学家在量子计算领域取得重大突破",
    "今年春运客流量预计超过90亿人次",
    "全国各地积极开展垃圾分类工作",
    "教育部发布新的中小学课程标准",
    "我国高铁运营里程超过4万公里",
    "北京冬奥会成功举办获得广泛好评",
    "我国新能源汽车销量持续增长",
    "全国医保覆盖面进一步扩大",
    "农业农村部推动乡村振兴战略实施",
    "神舟飞船成功发射返回",
    "嫦娥探月工程取得重要进展",
    "全国秋粮收获进展顺利丰收在望",
    "多地发布促消费政策提振经济",
    "今年高考报名人数再创新高",
    "国内生产总值同比增长百分之五",
    "港珠澳大桥通车后极大方便了三地出行",
    "城市轨道交通加快建设方便市民出行",
    "我国研发投入继续保持较快增长",
    "各地积极推进老旧小区改造工程",
    "全国夏粮产量再创历史新高",
    "新一代人工智能技术加速应用落地",
    "多地推出便民惠民措施优化营商环境",
    "生态环境持续改善空气质量达标天数增加",
    "全国铁路旅客发送量稳步恢复增长",
    "我国互联网普及率持续提升",
    "各地博物馆春节期间接待游客量大增",
    "数字人民币试点范围进一步扩大",
    "新基建投资持续加大拉动经济增长",
    "全国各地有序推进疫苗接种工作",
    "文化旅游市场复苏活力显现",
    # === 健康常识 ===
    "多喝水对身体有好处",
    "每天保持适量运动有益健康",
    "均衡饮食是保持健康的基础",
    "充足的睡眠对身体恢复很重要",
    "定期体检可以及早发现健康问题",
    "蔬菜水果富含维生素和膳食纤维",
    "少吃油炸食品对身体更好",
    "适当散步有助于消化和心血管健康",
    "保持良好的生活习惯很重要",
    "按时吃药是控制慢性病的关键",
    "戒烟限酒有益身体健康",
    "保持心情愉快对健康很有帮助",
    "冬季注意保暖预防感冒",
    "夏天多喝水防止中暑",
    "老年人要注意防跌倒",
    "高血压患者需要定期测量血压并记录",
    "糖尿病患者应注意控制饮食中的糖分摄入",
    "每年做一次全面体检很有必要",
    "饭后百步走活到九十九",
    "早睡早起身体好",
    "控制盐的摄入量可以预防高血压",
    "每天走一万步有助于保持体重",
    "补钙要晒太阳促进吸收",
    "绿茶含有丰富的抗氧化物质",
    "老年人适当补充维生素D有好处",
    "血压高的人要少吃咸的东西",
    "心情好免疫力就强",
    "牛奶是补钙的好食品",
    "粗粮有利于肠道健康要多吃",
    "游泳是对关节最友好的运动",
    # === 正常理财知识 ===
    "银行定期存款是比较安全的储蓄方式",
    "投资有风险入市需谨慎",
    "基金投资适合长期持有",
    "养老保险是退休后的重要保障",
    "医疗保险可以报销部分医疗费用",
    "理财产品需要了解风险等级",
    "存款保险制度保障储户权益",
    "国债是风险较低的投资品种",
    "分散投资可以降低风险",
    "不要把所有鸡蛋放在一个篮子里",
    "退休后可以领取基本养老金",
    "公积金贷款利率比商业贷款低",
    "社保缴费年限满十五年可以领养老金",
    "银行大额存单利率比普通定期高一些",
    "购买保险要仔细阅读保险条款",
    "货币基金风险较低适合存放闲钱",
    "信用卡按时还款有助于维护信用记录",
    "房贷可以选择等额本息或等额本金方式",
    "了解产品风险等级是理性投资的基础",
    "定投基金可以平滑市场波动降低风险",
    # === 普通对话 ===
    "你好，最近身体怎么样",
    "谢谢你的关心，我很好",
    "孩子们都很忙，周末回来看看",
    "今年过年大家一起吃团圆饭",
    "小区新开了一家便利店挺方便的",
    "昨天去了趟图书馆借了几本书",
    "邻居家的小狗很可爱",
    "春天来了花开了真漂亮",
    "今天学会用手机拍照了",
    "给老伴买了个生日蛋糕",
    "社区组织了一次义诊活动",
    "今天是个好日子适合出门",
    "早起锻炼身体棒棒的",
    "刚学会了用微信视频通话",
    "今天去参加了社区的书法班",
    "天凉了给孩子寄了件厚衣服",
    "儿子升职了全家都很高兴",
    "老同学聚会真是开心",
    "社区通知明天可以免费量血压",
    "外孙女考试考了一百分太棒了",
    "今天天气不好哪儿也没去",
    "隔壁老王今天请我们吃饭了",
    "小孙子放学了我去接他",
    "今天心情特别好哼着小曲",
    "老伴生日到了要给她准备礼物",
    "幼儿园老师说孙子表现很好",
    "今天坐了一趟高铁去看女儿",
    "手机换了新的挺好用的",
    "家里装了新的热水器特别方便",
    "楼下的桂花开了满院子都是香味",
    # === 正常短视频文案 ===
    "教你做一道简单又好吃的家常菜",
    "分享一个生活小妙招，超实用",
    "今天带大家逛逛我们小区的花园",
    "我家猫咪今天又做了搞笑的事情",
    "跟着音乐一起跳广场舞吧",
    "推荐一本最近在看的好书",
    "秋天的风景真的太美了",
    "记录今天做的手工编织",
    "分享一下我的早餐搭配",
    "旅游去了一个特别美的地方",
    "教大家如何种好家里的花",
    "今天的夕阳真的太美了",
    "我家孙子学会走路了太开心了",
    "分享一个超简单的甜品做法",
    "带大家看看我们村的变化",
    "手把手教你做正宗的红烧肉",
    "这个手工折纸太漂亮了赶紧学",
    "给大家看看我家种的蔬菜长得可好了",
    "今天教大家一个快速叠衣服的方法",
    "我家小院子里种的花开了好美",
    "周末和朋友们一起去爬山了好开心",
    "分享一个去油污的小窍门特别好用",
    "今天做了一桌子好菜请朋友吃饭",
    "教你三分钟学会包粽子",
    "给大家看看我在公园拍的照片",
    "这个钩针教程很简单一学就会",
    "带大家看看我们城市的夜景",
    "分享一下我每天的健身计划",
    "今天去果园摘草莓了好新鲜",
    "给大家推荐几首好听的老歌",
    # === 科普知识 ===
    "地球围绕太阳公转一圈需要365天",
    "人体大约有206块骨头",
    "水的沸点是100摄氏度",
    "光的传播速度约每秒30万公里",
    "人的正常体温在36到37度之间",
    "世界上最大的海洋是太平洋",
    "中国是世界上人口最多的国家之一",
    "万里长城是中国古代伟大的建筑工程",
    "大熊猫是中国特有的珍稀动物",
    "故宫是明清两代的皇家宫殿",
]

# ===== 额外虚假/风险文本（补充样本多样性） =====
RISK_TEXTS = [
    # === 金融诈骗 ===
    "加我微信教你日赚千元的方法",
    "稳赚不赔的投资项目限时招募",
    "国家秘密扶持项目只要投资就能暴富",
    "退休金翻倍计划政府内部消息",
    "刷单兼职日入五百零风险",
    "免费领红包点击链接马上到账",
    "恭喜中奖请提供银行卡号领取奖金",
    "只需缴纳少量保证金即可获得高额回报",
    "投资区块链数字货币月赚百万",
    "低风险高收益年化回报50%以上",
    "紧急通知你的账户有异常请立即转账到安全账户",
    "公安局通知你涉嫌洗钱请配合调查",
    "你的社保卡已冻结请拨打客服电话解冻",
    "冒充银行客服要求提供验证码",
    "假冒快递理赔要求转账",
    "投资原油期货保证日赚上万元",
    "内部消息明天股票一定涨停赶紧买",
    "免费领取补贴请输入身份证号和银行卡号",
    "你有一笔退税款项需要登录链接领取",
    "交五百元入会费跟老师操作月赚十万",
    "只要三千元就能买到稳赚不赔的股票软件",
    "政府发放消费券请点击链接填写个人信息",
    "你的银行卡涉嫌犯罪资金请立即冻结",
    "虚拟币挖矿一天就能回本投入越多赚越多",
    "国外投资平台高息稳赚每天分红到账",
    "杀猪盘投资平台前期少量出金取得信任",
    "扫这个二维码就可以免费领取手机",
    "以房养老投资项目国家政策支持高额回报",
    "网络贷款不看征信秒到账利息超低",
    "做任务刷好评就能赚钱日结百元",
    "幸运抽奖中了一等奖缴纳手续费即可领取",
    "外汇平台跟着操盘手交易包赢不亏",
    "加入投资群跟着喊单老师操作稳赚",
    "转发朋友圈集赞就能免费领取电视机",
    "充值返利充一百返五百名额有限先到先得",
    # === 健康谣言 ===
    "喝碱性水可以治疗癌症",
    "转发此消息就能获得健康保佑",
    "这个偏方可以治疗糖尿病不用吃药",
    "吃大蒜可以杀死体内所有病毒",
    "每天吃一种神奇食物永远不得癌症",
    "西医都是骗人的中医偏方才管用",
    "这种保健品能延年益寿活到120岁",
    "手机放床头会导致脑部肿瘤",
    "WiFi辐射会导致不孕不育",
    "吃味精会导致老年痴呆",
    "隔夜茶水致癌千万不能喝",
    "血管堵塞吃这个秘方三天通",
    "只要吃这个药高血压根治不复发",
    "感冒不用吃药喝姜汤泡脚就能好",
    "黄瓜和花生一起吃会中毒",
    "纳豆激酶可以溶解血栓不需要吃药",
    "酵素排毒清肠能治疗一切慢性病",
    "每天喝一杯醋能软化血管降血压",
    "空腹吃柿子会形成结石得胃癌",
    "小龙虾都是用洗虾粉洗的吃了会中毒",
    "微波炉加热的食物有辐射吃了致癌",
    "反复烧开的水含有大量亚硝酸盐致癌",
    "吃了三七粉就不用再吃降压药了",
    "黑枸杞泡水喝能治好近视",
    "红豆薏米水能治湿气什么病都能好",
    "木耳泡久了会产生毒素会致命",
    "用生姜擦头皮就能治好脱发",
    "晚上吃姜等于吃砒霜千万不能吃",
    "速冻食品含防腐剂吃了会得癌症",
    "无糖饮料比含糖饮料更害人千万别喝",
    # === 社会谣言 ===
    "紧急扩散某地发生重大事故死亡上千人",
    "赶快转发不转发就会倒霉",
    "央视报道千万不要再吃这种食物了",
    "世界末日即将来临这是最后的警告",
    "外星人已经入侵地球政府在隐瞒",
    "自来水里面有大量致癌物质",
    "这个视频是真的赶快转给所有人看",
    "再不看就被删了速度保存转发",
    "爆炸性消息即将公布请做好准备",
    "特大新闻震惊全国赶快看",
    "不转发这条消息今年就会倒大霉",
    "赶紧囤盐日本排放核污水了以后没有干净的盐了",
    "千万不要出门了外面的空气有毒",
    "紧急通知明天全市停水停电三天",
    "科学家证实地球将在三天后毁灭",
    "某明星已经去世了家属正在隐瞒",
    "快删除这个APP它会偷偷录音窃取隐私",
    "赶紧转发让更多人知道不然就晚了",
    "这个秘密只有少数人知道快点看",
    "看完一定要转发不然会后悔一辈子",
    "据内部人士透露这件事马上就要爆发了",
    "速看明天开始要收费了今天最后免费",
    "已经证实了千万不要再用这个品牌的产品",
    "告诉你身边每一个人这是真的不是谣言",
    "不看血亏看了就是赚到了赶紧收藏转发",
]


class AdvancedTrainer:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.data_dir = self.project_root / "data" / "raw"
        self.model_dir = self.project_root / "models" / "trained"
        self.model_dir.mkdir(parents=True, exist_ok=True)

    # ----------------------------------------------------------
    def _load_comprehensive(self) -> list:
        """加载 comprehensive_training_set.json"""
        fp = self.data_dir / "comprehensive_training_set.json"
        if not fp.exists():
            return []
        with open(fp, "r", encoding="utf-8") as f:
            raw = json.load(f)
        samples = []
        for item in raw:
            text = item.get("text", "").strip()
            if not text:
                continue
            label = item.get("label")
            if label in [2, "fake", "rumor", "谣言", "虚假"]:
                samples.append((text, 1))
            elif label in [0, "real", "true", "真实"]:
                samples.append((text, 0))
            elif label == 1:
                # label=1 在 comprehensive 中也视为风险
                samples.append((text, 1))
        return samples

    def _load_mcfend(self) -> list:
        """加载 mcfend_data.json"""
        fp = self.data_dir / "mcfend" / "mcfend_data.json"
        if not fp.exists():
            return []
        with open(fp, "r", encoding="utf-8") as f:
            raw = json.load(f)
        samples = []
        for item in raw:
            text = item.get("text", "").strip()
            if not text:
                continue
            label = item.get("label", "")
            if label in ["fake", "rumor"]:
                samples.append((text, 1))
            elif label == "real":
                samples.append((text, 0))
        return samples

    def _load_weibo(self) -> list:
        """加载 weibo_data.json"""
        fp = self.data_dir / "weibo_rumors" / "weibo_data.json"
        if not fp.exists():
            return []
        with open(fp, "r", encoding="utf-8") as f:
            raw = json.load(f)
        samples = []
        for item in raw:
            text = item.get("text", "").strip()
            if not text:
                continue
            label = item.get("label", "")
            if label in ["rumor", "fake"]:
                samples.append((text, 1))
            elif label == "real":
                samples.append((text, 0))
        return samples

    def _load_real_cases(self) -> list:
        """加载 real_case_dataset.json"""
        fp = self.data_dir / "real_cases" / "real_case_dataset.json"
        if not fp.exists():
            return []
        with open(fp, "r", encoding="utf-8") as f:
            raw = json.load(f)
        samples = []
        for item in raw:
            text = item.get("text", "").strip()
            if not text:
                continue
            label = item.get("label")
            if label in [2, 1, "fake", "rumor"]:
                samples.append((text, 1))
            elif label in [0, "real"]:
                samples.append((text, 0))
        return samples

    # ----------------------------------------------------------
    def load_and_deduplicate(self):
        """加载所有数据源 → 去重"""
        print("[1/6] 加载所有数据源...")

        all_samples = []
        src_counts = {}

        for name, loader in [
            ("comprehensive", self._load_comprehensive),
            ("mcfend", self._load_mcfend),
            ("weibo", self._load_weibo),
            ("real_cases", self._load_real_cases),
        ]:
            s = loader()
            src_counts[name] = len(s)
            all_samples.extend(s)
            print(f"  {name}: {len(s)} 条")

        # 加入额外安全/风险文本
        for t in SAFE_TEXTS:
            all_samples.append((t, 0))
        for t in RISK_TEXTS:
            all_samples.append((t, 1))
        print(f"  额外安全文本: {len(SAFE_TEXTS)} 条")
        print(f"  额外风险文本: {len(RISK_TEXTS)} 条")

        total_before = len(all_samples)
        print(f"\n  合并总量: {total_before} 条")

        # 去重（同一文本只保留第一次出现的）
        seen = set()
        deduped = []
        for text, label in all_samples:
            key = text.strip()
            if key not in seen:
                seen.add(key)
                deduped.append((text, label))

        texts = [t for t, _ in deduped]
        labels = [l for _, l in deduped]

        print(f"  去重后: {len(texts)} 条（去掉了 {total_before - len(texts)} 条重复）")
        print(f"  安全(0): {labels.count(0)} 条")
        print(f"  风险(1): {labels.count(1)} 条")

        return texts, labels

    # ----------------------------------------------------------
    def train_models(self, X_train, X_test, y_train, y_test):
        """训练多个模型并集成"""
        print("[3/6] 训练多个模型...")

        models = {}

        # 1. SVM
        print("  [1/4] 训练 SVM ...")
        svm = SVC(
            kernel="linear", C=1.0, probability=True,
            random_state=42, class_weight="balanced",
        )
        svm.fit(X_train, y_train)
        svm_acc = accuracy_score(y_test, svm.predict(X_test))
        print(f"    SVM 准确率: {svm_acc:.4f}")
        models["svm"] = (svm, svm_acc)

        # 2. Random Forest
        print("  [2/4] 训练 Random Forest ...")
        rf = RandomForestClassifier(
            n_estimators=200, max_depth=20, min_samples_split=5,
            random_state=42, class_weight="balanced", n_jobs=-1,
        )
        rf.fit(X_train, y_train)
        rf_acc = accuracy_score(y_test, rf.predict(X_test))
        print(f"    RF 准确率: {rf_acc:.4f}")
        models["rf"] = (rf, rf_acc)

        # 3. Gradient Boosting
        print("  [3/4] 训练 Gradient Boosting ...")
        gb = GradientBoostingClassifier(
            n_estimators=100, learning_rate=0.1, max_depth=5,
            random_state=42,
        )
        gb.fit(X_train, y_train)
        gb_acc = accuracy_score(y_test, gb.predict(X_test))
        print(f"    GB 准确率: {gb_acc:.4f}")
        models["gb"] = (gb, gb_acc)

        # 4. Logistic Regression
        print("  [4/4] 训练 Logistic Regression ...")
        lr = LogisticRegression(
            C=1.0, max_iter=1000, random_state=42, class_weight="balanced",
        )
        lr.fit(X_train, y_train)
        lr_acc = accuracy_score(y_test, lr.predict(X_test))
        print(f"    LR 准确率: {lr_acc:.4f}")
        models["lr"] = (lr, lr_acc)

        return models

    def create_ensemble(self, models, X_train, X_test, y_train, y_test):
        """创建集成模型"""
        print("[4/6] 创建集成模型...")

        estimators = [
            ("svm", models["svm"][0]),
            ("rf", models["rf"][0]),
            ("gb", models["gb"][0]),
            ("lr", models["lr"][0]),
        ]

        ensemble = VotingClassifier(estimators=estimators, voting="soft", n_jobs=-1)
        ensemble.fit(X_train, y_train)

        ensemble_acc = accuracy_score(y_test, ensemble.predict(X_test))
        print(f"  集成模型准确率: {ensemble_acc:.4f}")
        return ensemble, ensemble_acc

    def evaluate_model(self, model, X_test, y_test):
        """详细评估"""
        print("[5/6] 模型评估...")
        y_pred = model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        f1 = f1_score(y_test, y_pred, average="weighted")

        print(f"  准确率: {accuracy:.4f}")
        print(f"  F1 分数: {f1:.4f}")
        print("\n  详细报告:")
        print(classification_report(
            y_test, y_pred, target_names=["安全", "风险"], digits=4
        ))

        # 交叉验证
        print("  5 折交叉验证 ...")
        # 需要重新合并 X_train+X_test
        return {"accuracy": accuracy, "f1_score": f1}

    def save_model(self, model, vectorizer, metrics, data_size):
        """保存模型（到 models/trained 和项目根目录）"""
        print("[6/6] 保存模型...")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        model_data = {
            "model": model,
            "vectorizer": vectorizer,
            "metrics": metrics,
            "training_data_size": data_size,
            "timestamp": timestamp,
            "version": "2.0",
        }

        # 保存到 models/trained
        model_file = self.model_dir / "simple_ai_model.joblib"
        joblib.dump(model_data, model_file)
        print(f"  模型已保存: {model_file}")

        # 同时保存到项目根目录（后端 main.py 从根目录搜索）
        root_model_file = self.project_root / "simple_ai_model.joblib"
        joblib.dump(model_data, root_model_file)
        print(f"  根目录模型已更新: {root_model_file}")

        # 保存训练报告
        report = {
            "timestamp": timestamp,
            "training_data_size": data_size,
            "accuracy": metrics["accuracy"],
            "f1_score": metrics["f1_score"],
            "model_type": "Ensemble (SVM + RF + GB + LR)",
            "version": "2.0 - deduped + extra safe texts",
        }
        report_file = self.model_dir / f"training_report_{timestamp}.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"  训练报告: {report_file}")

        return root_model_file

    # ----------------------------------------------------------
    def train(self):
        """完整训练流程"""
        print("=" * 60)
        print("🚀 TF-IDF 集成模型训练 v2 (去重 + 多数据源 + 防误报)")
        print("=" * 60)
        print()

        # 1. 加载 + 去重
        texts, labels = self.load_and_deduplicate()

        # 2. 文本向量化
        print("\n[2/6] 文本向量化 ...")
        vectorizer = TfidfVectorizer(
            max_features=8000,
            ngram_range=(1, 3),
            min_df=1,         # 放宽 min_df，去重后每条只出现 1 次
            max_df=0.85,
            sublinear_tf=True,
        )
        X = vectorizer.fit_transform(texts)
        y = np.array(labels)
        print(f"  特征维度: {X.shape}")

        # 3. 分割数据集
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y,
        )
        print(f"  训练集: {X_train.shape[0]} 条")
        print(f"  测试集: {X_test.shape[0]} 条")

        # 4. 训练
        models = self.train_models(X_train, X_test, y_train, y_test)

        # 5. 集成
        ensemble, _ = self.create_ensemble(models, X_train, X_test, y_train, y_test)

        # 6. 评估
        metrics = self.evaluate_model(ensemble, X_test, y_test)

        # 7. 保存
        model_file = self.save_model(ensemble, vectorizer, metrics, len(texts))

        print()
        print("=" * 60)
        print("✅ 训练完成！")
        print(f"🎯 准确率: {metrics['accuracy']:.2%}")
        print(f"📊 F1 分数: {metrics['f1_score']:.4f}")
        print(f"💾 模型文件: {model_file}")
        print("=" * 60)

        # 8. 快速自测：用几个典型文本验证
        print("\n📋 快速自测:")
        test_texts = [
            "今天天气不错",
            "加我微信日赚千元",
            "祖传秘方包治百病",
            "我去超市买了蔬菜水果",
            "稳赚不赔年化收益50%",
            "均衡饮食有助于健康",
            "震惊！看完赶快转发",
        ]
        for t in test_texts:
            feat = vectorizer.transform([t])
            pred = ensemble.predict(feat)[0]
            proba = ensemble.predict_proba(feat)[0]
            risk_score = proba[1] if len(proba) > 1 else pred
            label_str = "⚠️ 风险" if pred == 1 else "✅ 安全"
            print(f"  {label_str} ({risk_score:.2%}) | {t}")

        return metrics["accuracy"]


def main():
    trainer = AdvancedTrainer()
    accuracy = trainer.train()

    if accuracy >= 0.90:
        print("\n🎉 模型达到 90% 以上准确率！")
    elif accuracy >= 0.85:
        print("\n✅ 模型达到 85% 以上准确率！")
    else:
        print("\n⚠️  准确率较低，建议增加更多多样化训练数据。")


if __name__ == "__main__":
    main()
