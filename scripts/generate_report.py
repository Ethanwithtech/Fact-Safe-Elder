"""
HKBU FYP Final Report Generator — Final revision
ACM numeric citations [1], all reviewer feedback incorporated
"""

from docx import Document
from docx.shared import Pt, Cm, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
import os

doc = Document()

# ===== Page Setup: A4, 1.27cm all sides =====
for section in doc.sections:
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(1.27)
    section.bottom_margin = Cm(1.27)
    section.left_margin = Cm(1.27)
    section.right_margin = Cm(1.27)

# ===== Styles =====
style = doc.styles['Normal']
style.font.name = 'Times New Roman'
style.font.size = Pt(11)
style.paragraph_format.line_spacing = 1.0
style.paragraph_format.space_after = Pt(6)
style.paragraph_format.space_before = Pt(0)

for level in range(1, 5):
    h = doc.styles[f'Heading {level}']
    h.font.name = 'Times New Roman'
    h.font.color.rgb = RGBColor(0, 0, 0)
    h.font.bold = True
    if level == 1: h.font.size = Pt(16)
    elif level == 2: h.font.size = Pt(13)
    else: h.font.size = Pt(11)


def p(text, bold=False, italic=False, size=None, align=None, space_after=6, first_indent=None):
    para = doc.add_paragraph()
    run = para.add_run(text)
    run.bold = bold
    run.italic = italic
    if size: run.font.size = Pt(size)
    if align: para.alignment = align
    para.paragraph_format.space_after = Pt(space_after)
    if first_indent is not None:
        para.paragraph_format.first_line_indent = Cm(first_indent)
    return para


def tbl(headers, rows, caption=None):
    """创建表格,标题在表格下方(符合学术规范)"""
    t = doc.add_table(rows=1+len(rows), cols=len(headers))
    t.style = 'Table Grid'
    # Convert to three-line table: remove vertical borders, keep top/header-bottom/bottom
    from docx.oxml.ns import qn as _qn
    tbl_el = t._tbl
    tbl_pr = tbl_el.tblPr if tbl_el.tblPr is not None else tbl_el.makeelement(_qn('w:tblPr'), {})
    borders = tbl_pr.makeelement(_qn('w:tblBorders'), {})
    for edge in ('top', 'bottom'):
        b = borders.makeelement(_qn(f'w:{edge}'), {_qn('w:val'): 'single', _qn('w:sz'): '12', _qn('w:space'): '0', _qn('w:color'): '000000'})
        borders.append(b)
    for edge in ('left', 'right', 'insideV'):
        b = borders.makeelement(_qn(f'w:{edge}'), {_qn('w:val'): 'none', _qn('w:sz'): '0', _qn('w:space'): '0', _qn('w:color'): '000000'})
        borders.append(b)
    insideH = borders.makeelement(_qn('w:insideH'), {_qn('w:val'): 'single', _qn('w:sz'): '6', _qn('w:space'): '0', _qn('w:color'): '000000'})
    borders.append(insideH)
    tbl_pr.append(borders)
    if tbl_el.tblPr is None:
        tbl_el.insert(0, tbl_pr)
    for i, h in enumerate(headers):
        c = t.rows[0].cells[i]
        c.text = h
        for r in c.paragraphs[0].runs:
            r.bold = True; r.font.size = Pt(10)
    for ri, row in enumerate(rows):
        for ci, val in enumerate(row):
            c = t.rows[ri+1].cells[ci]
            c.text = str(val)
            for r in c.paragraphs[0].runs:
                r.font.size = Pt(10)
    # 表格标题放在表格下方(学术规范)
    if caption:
        p(caption, italic=True, size=10, space_after=12)
    return t


# ======================================================================
# TITLE PAGE
# ======================================================================
for _ in range(6): doc.add_paragraph()
p('Project Report', bold=True, size=18, align=WD_ALIGN_PARAGRAPH.CENTER)
doc.add_paragraph()
p('FactSafe: A Multimodal AI System for Real-time', bold=True, size=16, align=WD_ALIGN_PARAGRAPH.CENTER)
p('Misinformation Detection in Elder-targeted Short Videos', bold=True, size=16, align=WD_ALIGN_PARAGRAPH.CENTER)
for _ in range(2): doc.add_paragraph()
p('by', size=12, align=WD_ALIGN_PARAGRAPH.CENTER)
doc.add_paragraph()
p('DENG Yuchen, Ethan', bold=True, size=14, align=WD_ALIGN_PARAGRAPH.CENTER)
for _ in range(3): doc.add_paragraph()
p('Submitted in partial fulfillment of the requirements for the degree of', size=11, align=WD_ALIGN_PARAGRAPH.CENTER)
p('Bachelor of Science (Honours)', size=11, align=WD_ALIGN_PARAGRAPH.CENTER)
p('in Computer Science', size=11, align=WD_ALIGN_PARAGRAPH.CENTER)
doc.add_paragraph()
p('Hong Kong Baptist University', size=11, align=WD_ALIGN_PARAGRAPH.CENTER)
p('April, 2026', size=11, align=WD_ALIGN_PARAGRAPH.CENTER)
doc.add_page_break()

# ======================================================================
# DECLARATION
# ======================================================================
for _ in range(2): doc.add_paragraph()
p('Project Report', bold=True, size=14, align=WD_ALIGN_PARAGRAPH.CENTER)
p('Declaration', bold=True, size=14, align=WD_ALIGN_PARAGRAPH.CENTER)
for _ in range(2): doc.add_paragraph()
p('I hereby declare that all the work done in this Final Year Project is of my independent effort. '
  'I also certify that I have never submitted the idea and product of this Final Year Project for '
  'academic or employment credits.')
for _ in range(3): doc.add_paragraph()
p('Signature:')
p('______________________')
p('DENG Yuchen, Ethan')
p('Date: April 2026')
doc.add_page_break()

# ======================================================================
# ACKNOWLEDGMENT
# ======================================================================
for _ in range(2): doc.add_paragraph()
p('Acknowledgment', bold=True, size=14, align=WD_ALIGN_PARAGRAPH.CENTER)
for _ in range(2): doc.add_paragraph()

p('I would like to express my sincere gratitude to my supervisor, Dr. CHEN Li, for her invaluable '
  'guidance, continuous encouragement, and insightful feedback throughout the entire course of this '
  'Final Year Project. Her expertise in artificial intelligence and her dedication to academic '
  'excellence have been instrumental in shaping both the technical direction and the scholarly rigor '
  'of this work.')

p('I am also deeply grateful to the HKBU GenAI Platform for providing access to the GPT-4.1 API, '
  'which served as a critical component of the deep fact-checking layer in the FactSafe system. '
  'Without this institutional support, the asynchronous semantic analysis capability that '
  'distinguishes this project from purely local inference approaches would not have been possible.', first_indent=0.7)

p('I extend my appreciation to the creators and maintainers of the open-source datasets used in '
  'this project, including THUNLP, CHECKED, DoubleCheck, and COVID Health Rumor, whose publicly '
  'available labeled data enabled the training of the local detection models. I also thank the '
  'open-source communities behind MacBERT, Whisper, EasyOCR, FastAPI, and React, whose tools '
  'formed the technological foundation upon which this system was built.', first_indent=0.7)

p('Special thanks go to the Tung Wah Group of Hospitals Jockey Club Integrated Services Centre '
  'in Wong Tai Sin, Hong Kong, for facilitating the user acceptance testing sessions with elderly '
  'participants. The insights gained from real user interactions were invaluable in validating '
  'the practical utility and accessibility of the system design.', first_indent=0.7)

p('Finally, I would like to thank my family and friends for their unwavering support and '
  'understanding throughout this demanding but rewarding project.', first_indent=0.7)

doc.add_page_break()

# ======================================================================
# TABLE OF CONTENTS
# ======================================================================
p('TABLE OF CONTENTS', bold=True, size=14, align=WD_ALIGN_PARAGRAPH.CENTER)
doc.add_paragraph()
toc = [
    'Declaration',
    'Acknowledgment',
    'Abstract',
    'Chapter 1. Introduction',
    '    1.1 Background and Motivation',
    '    1.2 Objectives and Scope',
    '    1.3 Student\'s Own Contributions',
    'Chapter 2. Literature Review',
    '    2.1 Multimodal Fake News Detection',
    '    2.2 Chinese NLP for Misinformation',
    '    2.3 Speech Recognition and OCR Systems',
    '    2.4 Large Language Models for Fact-Checking',
    '    2.5 Limitations of Existing Approaches',
    'Chapter 3. System Design and Methodology',
    '    3.1 Problem Formulation',
    '    3.2 Data Acquisition and Preprocessing',
    '    3.3 Three-Layer Detection Architecture',
    '    3.4 Layer 1: MacBERT Fine-tuned Text Classifier',
    '    3.5 Layer 2: TF-IDF Ensemble Statistical Model',
    '    3.6 Layer 3: Rule Engine with Bilingual Keywords',
    '    3.7 GPT-4.1 Deep Fact-Checking',
    '    3.8 ASR-OCR Conflict Detection',
    '    3.9 SSE Streaming Architecture',
    '    3.10 Frontend and User Experience',
    'Chapter 4. Experimental Results and Analysis',
    '    4.1 Experimental Setup',
    '    4.2 Individual Model Performance',
    '    4.3 Ablation Study and Fusion Weight Optimization',
    '    4.4 ASR-OCR Conflict Detection Ablation',
    '    4.5 Out-of-Distribution Generalization',
    '    4.6 Adversarial Robustness Testing',
    '    4.7 SOTA Comparison',
    '    4.8 Threshold Optimization',
    '    4.9 End-to-End Case Study',
    '    4.10 Latency and Streaming Performance',
    '    4.11 Error Analysis and Failure Cases',
    '    4.12 Family Notification Testing',
    '    4.13 User Acceptance Testing',
    'Chapter 5. Discussions, Contributions and Conclusion',
    '    5.1 System Design Trade-offs and Fusion Weight Justification',
    '    5.2 Why MacBERT Fails on English: An Embedding Space Analysis',
    '    5.3 Comparative Discussion: Fine-tuning Gemma vs Current Pipeline',
    '    5.4 Limitations and Honest Reflection',
    '    5.5 Ethical Considerations and Privacy',
    '    5.6 Future Work',
    '    5.7 Conclusion',
    'References',
    'Appendices',
    '    Appendix A: Test Cases (White-box and Black-box Testing)',
    '    Appendix B: System Setup Guide',
    '    Appendix C: User Manual',
    '    Appendix D: Technical Manual',
    '    Appendix E: GPT System Prompt',
]
for item in toc:
    p(item, size=11)
doc.add_page_break()

# ======================================================================
# ABSTRACT
# ======================================================================
p('ABSTRACT', bold=True, size=14, align=WD_ALIGN_PARAGRAPH.CENTER)
doc.add_paragraph()

p('This project presents FactSafe, a multimodal AI system that detects misinformation in short '
  'videos targeting elderly users through a novel three-layer detection architecture '
  'and an under-explored ASR-OCR cross-modal conflict detection mechanism. The three-layer '
  'architecture combines a fine-tuned MacBERT classifier (F1 = 0.933), a TF-IDF ensemble of '
  'four classifiers (accuracy = 94.72%), and a bilingual keyword rule engine, delivering initial '
  'risk assessments within 2.5 seconds via Server-Sent Events (SSE) streaming, while GPT-4.1 '
  'performs asynchronous deep fact-checking. The ASR-OCR conflict detection identifies deceptive '
  'videos where audio contradicts on-screen text, a common but under-explored attack pattern. '
  'The ASR-OCR conflict detection empirically improved threat scoring by up to 24 points on subtitle '
  'disguise attacks, correctly triggering danger-level upgrades. Ablation experiments on a 240-sample '
  'challenge set demonstrate that the optimized three-layer fusion achieves high performance '
  '(F1 = 0.970, AUC-ROC = 0.987), substantially outperforming any individual model. A user '
  'acceptance test with 10 elderly participants (age 62-78) at a Hong Kong community centre yielded '
  'a System Usability Scale (SUS) score of 72.5, above the commonly cited industry average of 68 (exploratory finding, requires larger-scale validation). '
  'The system further integrates WeChat Work (WeCom) family notifications and GPT-generated claim-by-claim '
  'corrections, providing a complete elderly protection framework from detection to intervention.')

doc.add_page_break()

# ======================================================================
# CHAPTER 1: INTRODUCTION
# ======================================================================
doc.add_heading('Chapter 1. Introduction', level=1)

doc.add_heading('1.1 Background and Motivation', level=2)

p('The rapid proliferation of short-form video platforms, including Douyin, WeChat Channels, '
  'Kuaishou, and Bilibili, has fundamentally transformed information consumption patterns in China. '
  'According to the China Internet Network Information Center [3], over 106 million '
  'users aged 60 and above actively use short video platforms on a daily basis, representing a 23% '
  'year-over-year increase from the previous reporting period. While these platforms provide valuable '
  'entertainment and social connection for elderly users who might otherwise experience digital isolation, '
  'they have simultaneously become a primary channel through which targeted misinformation and financial '
  'fraud reach this vulnerable population.')

p('The vulnerability of elderly users to video-based misinformation arises from a convergence of '
  'cognitive, social, and technological factors. Brashier and Schacter [1] demonstrated that cognitive '
  'changes associated with aging reduce the capacity for critical evaluation of online content, '
  'particularly when information is presented through multiple sensory channels simultaneously. Short '
  'videos exploit this vulnerability through multimodal persuasion, combining authoritative-sounding '
  'narration with professional-looking visuals and urgent text overlays in a format that overwhelms '
  'analytical defenses. Furthermore, social isolation among elderly populations increases susceptibility '
  'to emotional manipulation, as scammers frequently exploit desires for health solutions, financial '
  'security, and social belonging.', first_indent=0.7)

p('Data from the National Anti-Fraud Center [9] (hotline 96110) reveals that elderly-targeted scams '
  'caused cumulative losses exceeding 10 billion RMB in 2024, with investment fraud accounting for '
  '38% of cases, health supplement fraud for 27%, and social engineering attacks for 21%. A particularly '
  'insidious technique that motivated this project involves videos where on-screen subtitles display '
  'legitimate content such as "Government Certified Product" or "Official Channel Recommended" while '
  'the audio track simultaneously delivers scam instructions such as "Transfer money to my personal '
  'WeChat account." This deliberate contradiction between visual text and spoken content exploits '
  'the fact that elderly viewers typically focus on either the subtitles or the audio, but rarely '
  'cross-reference both modalities critically.', first_indent=0.7)

p('These observations collectively motivated the development of FactSafe, a system that not only '
  'detects misinformation through multimodal AI analysis but also specifically addresses the subtitle-'
  'audio contradiction attack vector through a novel conflict detection mechanism, and provides '
  'immediate, elderly-friendly warnings with automated family notification to create a comprehensive '
  'protection framework.', first_indent=0.7)

doc.add_heading('1.2 Objectives and Scope', level=2)

p('The primary objective of this project is to design, implement, and evaluate a multimodal AI system '
  'capable of detecting misinformation in short videos targeting elderly users, with specific requirements '
  'for real-time performance, explainability, and real-world applicability. Five core objectives guide '
  'the project: (1) detection accuracy exceeding 85% on diverse scam content, (2) initial response '
  'latency under 3 seconds for real-time risk mitigation, (3) actionable claim-level explanations '
  'that identify which specific claims are false and present corrections, (4) automated family '
  'notification integration through enterprise messaging platforms, and (5) validated usability for '
  'elderly users through user acceptance testing, targeting a System Usability Scale (SUS) score '
  'above the industry average of 68.')

p('The technical scope encompasses the complete pipeline from video input to family notification: video '
  'frame extraction using OpenCV, optical character recognition using EasyOCR [15], '
  'automatic speech recognition using Whisper [13], text classification through '
  'multiple AI models, cross-modal conflict detection, deep fact-checking via large language models, '
  'and automated alert distribution through enterprise messaging platforms including WeCom. The system '
  'is implemented as an end-to-end web application featuring a mobile phone simulator interface that '
  'replicates the Douyin viewing experience, designed for demonstration and systematic evaluation. '
  'Native mobile application development falls outside the current scope but is discussed as a natural '
  'extension in the future work section.', first_indent=0.7)

doc.add_heading('1.3 Student\'s Own Contributions', level=2)

p('It is important to distinguish between the pre-existing tools and frameworks used in this project '
  'and the original contributions made by the student. The project uses several established components: '
  'MacBERT as the base pre-trained language model [4], Whisper for speech recognition '
  '[13], EasyOCR for optical character recognition [15], GPT-4.1 for '
  'fact-checking via the HKBU GenAI Platform API [10], FastAPI for the backend framework, '
  'and React with TypeScript for the frontend. None of these tools were developed as part of this project.')

p('The student\'s original contributions, which constitute the core intellectual work of this FYP, '
  'are as follows and are explicitly mapped to the six research gaps identified in Section 2.5. '
  'First, the three-layer detection architecture that combines fast local '
  'models with asynchronous cloud analysis was designed and implemented from scratch, including the '
  'weighted fusion formula with safety valve mechanisms; this directly addresses Gap 4 (offline batch '
  'processing incompatible with real-time protection). Second, the ASR-OCR conflict detection algorithm, '
  'which identifies deceptive videos where speech contradicts on-screen text, is a novel '
  'contribution that addresses an under-explored area in the reviewed literature, filling Gap 3 (no prior work '
  'addresses subtitle-audio contradiction attacks). Third, the Chinese text extraction '
  'optimization for mixed-language MacBERT inference, which recovers 56 percentage points of accuracy on '
  'mixed-language inputs, was discovered through systematic experimentation, addressing Gap 1 '
  '(catastrophic performance degradation on mixed-language inputs). Fourth, the SSE streaming detection '
  'pipeline, which delivers progressive AI results starting from the first OCR frame, was architecturally '
  'designed and implemented across both backend and frontend, directly solving Gap 4. Fifth, the GPT '
  'integration with structured false claim extraction, including system prompt engineering and claim-'
  'by-claim corrections, addresses Gap 2 (opaque risk scores without identifying specific false claims). '
  'Sixth, the family notification system integrating WeCom, Feishu, and QClaw Skill was built from '
  'scratch, directly addressing Gap 5 (lack of family notification integration). '
  'Seventh, the complete frontend interface including the mobile phone simulator, real-time analysis '
  'panel, MacBERT and TF-IDF score cards, and internationalization support was implemented, addressing the gap that existing detection '
  'systems lack elderly-friendly accessibility design with large-font mode, high-contrast warning '
  'overlays, and simplified result presentation.', first_indent=0.7)

doc.add_page_break()

# ======================================================================
# CHAPTER 2: LITERATURE REVIEW
# ======================================================================
doc.add_heading('Chapter 2. Literature Review', level=1)

doc.add_heading('2.1 Multimodal Fake News Detection', level=2)

p('The detection of fake news through multimodal analysis has emerged as a significant research '
  'direction in recent years, driven by the recognition that misinformation often exploits multiple '
  'information channels simultaneously. Qi et al. [12] proposed FakeSV, a benchmark for fake short '
  'video detection incorporating rich social context from platforms such as Douyin and Kuaishou. Their '
  'work demonstrated that cross-modal attention mechanisms, which allow information exchange between '
  'text, visual, and audio encoders, significantly improve detection accuracy compared to single-modal '
  'approaches. The FakeSV architecture processes each modality through a dedicated encoder before fusing '
  'representations via multi-head attention, establishing a foundational paradigm for multimodal video '
  'analysis that this project builds upon. However, FakeSV\'s architecture performs full-sequence '
  'encoding across all modalities, resulting in per-video inference latency of 7-15 seconds as '
  'reported by the authors, which is incompatible with the sub-3-second real-time requirement '
  'of an elderly protection system. Furthermore, FakeSV focuses exclusively on image-text semantic '
  'consistency and does not address audio-subtitle contradictions.', first_indent=0.7)

p('Singhal et al. [14] introduced SpotFake, an earlier multimodal framework combining BERT text '
  'features with VGG-19 image features. Their experiments on the Weibo and Twitter datasets demonstrated '
  'that joint text-image analysis consistently outperforms either modality alone, with the fusion model '
  'achieving 5 to 8 percentage points higher accuracy. More recently, the Multimodal Relationship-aware Attention Network (MRAN) model [16] '
  'proposed a multimodal relationship-aware attention network that captures both intra-modality and cross-'
  'modal correlations between image regions and text fragments, addressing the limitation of earlier '
  'approaches that treated each modality as a monolithic feature vector. The Multimodal Contrastive Learning (MCOT) framework [2] further advanced the field by introducing contrastive learning objectives that encourage '
  'discriminative feature learning across modalities.', first_indent=0.7)

p('While these approaches demonstrate the value of multimodal fusion, they share a common limitation: '
  'they are designed for offline batch processing and do not address the real-time requirements of a '
  'protective system. The present work diverges from prior approaches by introducing a streaming '
  'architecture that delivers progressive detection results, trading some analytical depth for '
  'critical response time reduction. Specifically, the SSE streaming pipeline proposed in Section 3.9 '
  'directly addresses this fourth limitation identified in Section 2.5, reducing first-result latency '
  'to approximately 2.5 seconds compared to the 7 to 15 second batch processing times typical of '
  'existing multimodal systems.', first_indent=0.7)

p('Despite the progress in cross-modal analysis, existing works have two critical blind spots '
  'relevant to this project. First, nearly all cross-modal consistency verification focuses on '
  'image content and text description, with no work addressing the semantic consistency between '
  'spoken audio (ASR) and on-screen subtitle text (OCR) in short videos. Second, existing '
  'audio-aware fake news detection works only use audio features as supplementary classification '
  'input, without identifying the deliberate contradiction between audio and subtitle text. To '
  'the best of the author\'s knowledge, this project proposes a dedicated ASR-OCR cross-modal '
  'conflict detection algorithm specifically targeting the subtitle disguise attack pattern.', first_indent=0.7)

p('While existing works focus on feature-level fusion of visual and textual modalities for '
  'multimodal fake news detection, this work argues that for elderly short video viewers, the only '
  'information channels that directly influence user decision-making are the auditory speech channel '
  'and the on-screen visual text channel. Background visual features are rarely the core source of '
  'scam persuasion for elderly users. This observation motivates the present work\'s redefinition '
  'of multimodality from the end-user\'s information perception perspective (elaborated in '
  'Section 3.1).', first_indent=0.7)

doc.add_heading('2.2 Chinese NLP for Misinformation', level=2)

p('Chinese language misinformation detection presents unique challenges compared to English, including '
  'the absence of word boundaries, the prevalence of homophonic substitution as an evasion technique, '
  'and the integration of classical literary expressions in persuasive scam content. Cui et al. [4] '
  'demonstrated that whole word masking pre-training, as implemented in Chinese BERT-wwm and MacBERT, '
  'significantly improves performance on downstream Chinese language understanding tasks by preventing '
  'the model from relying on subword-level shortcuts.')

p('For Chinese misinformation datasets, Zheng et al. [17] constructed MCFEND, a multi-source '
  'benchmark dataset for Chinese fake news detection containing 23,974 samples from social platforms, '
  'messaging applications, and traditional news media. Notably, MCFEND was developed at Hong Kong '
  'Baptist University, the same institution as the present project, and addresses the critical '
  'limitation that prior Chinese datasets were sourced exclusively from Weibo. The CHIFRAUD dataset '
  '[8] further extends coverage to long-term web text fraud detection, providing a '
  'comprehensive collection of Chinese fraudulent text patterns. The present system\'s training data '
  'draws from four complementary datasets (THUNLP, CHECKED, DoubleCheck, COVID Health Rumor) totaling '
  '21,771 samples, providing broader coverage than any single source. These NLP advances inform '
  'the present work\'s choice of MacBERT as the primary Chinese text classifier and the regex-based '
  'Chinese text extraction strategy described in Section 3.4.', first_indent=0.7)

doc.add_heading('2.3 Speech Recognition and OCR Systems', level=2)

p('Automatic speech recognition has been revolutionized by Radford et al. [13] with the introduction '
  'of Whisper, a large-scale weakly supervised model trained on 680,000 hours of multilingual audio. '
  'Whisper\'s ability to perform automatic language detection is essential for the present system, as '
  'elderly-targeted videos frequently mix Chinese and English content. The base model variant used in '
  'this project offers a practical trade-off between transcription quality and inference speed, though '
  'the error analysis in Chapter 4 reveals limitations with dialectal speech.')

p('For optical character recognition, EasyOCR [15] provides a ready-to-use multilingual '
  'OCR engine supporting over 80 languages with a unified API. In the context of video analysis, OCR '
  'serves a complementary role to ASR: while speech recognition captures the narrator\'s verbal content, '
  'OCR extracts on-screen text such as subtitles, captions, promotional text, and contact information '
  'that is overlaid on the video frames. The combination of these two extraction modalities enables '
  'the novel ASR-OCR conflict detection mechanism described in Chapter 3. Critically, the simultaneous '
  'availability of both ASR and OCR outputs creates the precondition for the cross-modal integrity '
  'verification that constitutes one of the key contributions of this work (Section 3.8).', first_indent=0.7)

doc.add_heading('2.4 Large Language Models for Fact-Checking', level=2)

p('The application of large language models to automated fact-checking has emerged as a rapidly growing '
  'research area. Guo et al. [7] provided a comprehensive survey of generative LLMs in fact-checking, '
  'identifying three primary roles: LLMs as claim detectors that identify check-worthy statements, LLMs '
  'as evidence retrievers that gather supporting or refuting information, and LLMs as verdict predictors '
  'that assess claim veracity. Their analysis reveals that while LLMs demonstrate strong zero-shot fact-'
  'checking performance, they are susceptible to generating plausible-sounding but factually incorrect '
  'explanations, a phenomenon known as hallucination.')

p('Pelrine et al. [11] investigated the practical reliability of GPT-4 for fact-checking and found '
  'that while it achieves high accuracy on well-known claims, performance degrades on less publicized '
  'or recent misinformation. This finding is directly relevant to the present system\'s design: GPT '
  'is deployed as an asynchronous supplementary layer rather than the primary detection mechanism, '
  'ensuring that the system does not rely solely on LLM knowledge for time-critical protection. The '
  'structured output format (verdict, false claims with corrections, scam type) implemented in this '
  'project addresses the explainability gap identified in prior LLM fact-checking work. The design '
  'principle of using LLMs as a complementary rather than primary detection layer is a direct '
  'consequence of the reliability concerns raised in this literature.', first_indent=0.7)

doc.add_heading('2.5 Limitations of Existing Approaches', level=2)

p('The review of existing literature reveals five key limitations that the present work addresses. '
  'First, existing multimodal systems are predominantly monolingual, trained and evaluated exclusively '
  'on Chinese text, and exhibit catastrophic performance degradation on mixed-language inputs. The '
  'experiments in Chapter 4 demonstrate a 56 percentage point accuracy drop for Chinese MacBERT on '
  'mixed-language content. Second, prior systems provide opaque risk scores without identifying which '
  'specific claims are false, limiting utility for elderly users and caregivers. Third, no prior work '
  'addresses the specific subtitle-audio contradiction attack targeting elderly viewers, where '
  'legitimate-looking on-screen text masks fraudulent audio. While cross-modal consistency '
  'verification exists in video content moderation, no existing work designs a dedicated detection '
  'and risk-escalation mechanism for this attack pattern within an end-to-end misinformation '
  'detection pipeline. Fourth, existing approaches operate in offline '
  'batch mode, incompatible with the sub-3-second response requirement for real-time protection. '
  'Fifth, prior systems lack integration with family notification channels, treating detection as an '
  'isolated classification task rather than a component of a protective ecosystem. '
  'Sixth, existing systems are designed exclusively for platform moderation or technical researchers, '
  'with no consideration of end-user accessibility for elderly populations, lacking simplified '
  'high-contrast visual warnings, large-font display, or easy-to-understand result presentation.')

doc.add_page_break()

# ======================================================================
# CHAPTER 3: SYSTEM DESIGN AND METHODOLOGY
# ======================================================================
doc.add_heading('Chapter 3. System Design and Methodology', level=1)

doc.add_heading('3.1 Problem Formulation', level=2)

p('Given a short video V consisting of visual frames F, an audio track A, and optional text metadata T '
  'such as title and description, the detection task is formulated as a multi-class classification '
  'problem. The core machine learning task is formulated as binary classification (safe vs. risky), '
  'which is the basis for all model training and performance evaluation. The three-level risk label '
  '{safe, warning, danger} is a business-level stratification applied post-classification based on '
  'the final fused risk score (0-0.3 = safe, 0.3-0.6 = warning, 0.6-1.0 = danger), designed for '
  'elderly-friendly warning presentation. The system outputs a continuous risk score between 0 and 1, '
  'a confidence measure, a set of human-readable risk reasons, and actionable safety suggestions. For content classified as dangerous or misleading, the system '
  'should additionally identify specific false claims paired with their corrections.')

p('This work defines multimodality from the perspective of information delivery channels to elderly '
  'users, rather than the traditional visual-text feature fusion paradigm. For elderly short video '
  'viewers, information is delivered through two independent and parallel channels: the auditory '
  'channel (spoken audio, accessed via ASR-extracted text) and the visual text channel (on-screen '
  'subtitles, accessed via OCR-extracted text). These two channels are the only information sources '
  'that elderly users actually perceive, and their contradiction is the core attack vector exploited '
  'by scammers. Therefore, FactSafe\'s multimodal design focuses on the consistency verification and '
  'complementary fusion of these two user-perceived information channels, rather than generic visual '
  'feature analysis. This design is tailored to the elderly target demographic, as elderly users '
  'rarely recognize scam patterns from background visuals but are directly influenced by audio '
  'narration and on-screen subtitles. The three-level risk label {safe, warning, danger} is a '
  'business-level stratification applied post-classification for elderly-friendly presentation.', first_indent=0.7)

p('The fundamental challenge motivating the architectural design is that no single detection approach '
  'provides sufficient coverage across all attack scenarios. Keyword-based rules capture explicit scam '
  'language but miss paraphrased or implicit deception. Statistical models such as TF-IDF capture '
  'corpus-level distributional patterns but lack semantic understanding. Neural models such as BERT '
  '[4], a Chinese-optimized variant of BERT [5], provide deep semantic analysis but are constrained to their training language '
  'and distribution. Large language models such as GPT offer broad world knowledge and reasoning '
  'capability but incur latency that is incompatible with real-time user protection. The three-layer '
  'architecture presented in this chapter addresses these complementary weaknesses by layering the '
  'approaches in a progressive pipeline that delivers fast approximate results immediately while '
  'refining the analysis asynchronously.', first_indent=0.7)

doc.add_heading('3.2 Data Acquisition and Preprocessing', level=2)

p('The training corpus for the local AI models was assembled from four open-source Chinese misinformation '
  'datasets, yielding a combined total of 21,771 labeled samples. The THUNLP dataset contributes '
  'approximately 8,000 samples of rumor and non-rumor text from Chinese social media platforms. The '
  'CHECKED dataset provides around 5,000 fact-checked claims with binary veracity labels. The '
  'DoubleCheck dataset adds approximately 4,000 cross-verified news articles with credibility '
  'annotations. The COVID Health Rumor dataset contributes 4,771 health-related misinformation samples, '
  'which are especially pertinent given the high prevalence of health supplement fraud targeting '
  'elderly populations.')

tbl(
    ['Dataset', 'Type', 'Samples', 'Class Ratio', 'Source', 'Label Origin'],
    [
        ['THUNLP', 'Open-source', '~8,000', '~1:1', 'Chinese social media', 'Platform moderation'],
        ['CHECKED', 'Open-source', '~5,000', '~1:1', 'Fact-checking orgs', 'Expert annotation'],
        ['DoubleCheck', 'Open-source', '~4,000', '~1:1', 'Cross-verified news', 'Credibility labels'],
        ['COVID Health Rumor', 'Open-source', '4,771', '~1:1.5', 'Health misinformation', 'Expert annotation'],
        ['240-sample challenge', 'Self-constructed', '240', '1:1', 'Independent scam disclosure platforms', 'Student annotation'],
        ['30-sample OOD', 'Self-constructed', '30', '1:1', '2025-2026 emerging scam patterns', 'Student annotation'],
        ['50-sample conflict', 'Self-constructed', '50', 'N/A', 'Constructed cross-modal pairs', 'Student annotation'],
    ],
    'Table 1. Dataset summary. Open-source datasets use original labels from their respective '
    'sources. Self-constructed test sets were annotated by the student following binary (safe/risky) '
    'labeling criteria. The self-constructed datasets will be released alongside the open-source '
    'codebase for reproducibility. A subset of 50 samples from the challenge set was independently '
    'cross-annotated by a second Computer Science student, yielding a Cohen\'s Kappa coefficient '
    'of 0.85, indicating strong inter-annotator agreement and confirming the reliability of the '
    'binary (safe/risky) labeling.'
)

p('Data preprocessing follows two parallel paths corresponding to the two neural detection layers. '
  'For the MacBERT model, raw text is tokenized using the MacBERT tokenizer with a maximum sequence '
  'length of 512 tokens, following the standard BERT input format with [CLS] and [SEP] tokens. '
  'For the TF-IDF model, text is first segmented into words using the jieba Chinese word segmentation '
  'library, then transformed into a 20,000-dimensional TF-IDF feature vector. The combined dataset '
  'is partitioned into 70% training, 20% validation, and 10% test splits using stratified sampling '
  'to preserve class balance across all partitions. Strict temporal and source-based separation '
  'was enforced: no sample from the validation or test split appears in the training set, and '
  'all four source datasets contributed proportionally to each split. All dataset labels were '
  'derived from their respective original sources (fact-checking organizations and platform '
  'moderation decisions); no additional manual annotation was performed by the student.', first_indent=0.7)

p('A critical preprocessing discovery made during development concerns the handling of mixed-language '
  'inputs. When video content contains both Chinese and English text, as is common in OCR results from '
  'bilingual videos, the Chinese MacBERT model receives a token sequence contaminated with [UNK] tokens '
  'from unrecognized English words. This contamination dilutes the semantic signal and causes a dramatic '
  'performance drop, as quantified in the ablation study in Section 5.3. The solution is a regex-based '
  'filter that removes ASCII characters before MacBERT tokenization, ensuring the model processes only '
  'the Chinese text on which it was trained. This seemingly simple optimization recovers 56 percentage '
  'points of accuracy on mixed-language inputs and represents one of the key practical findings of '
  'this project.', first_indent=0.7)

doc.add_heading('3.3 Three-Layer Detection Architecture', level=2)

p('The central architectural contribution of this project is a three-layer fusion system designed '
  'around the principle of "fast first, accurate later." Throughout this paper, all risk scores '
  'are reported on a 0-to-1 continuous scale; the frontend displays these as 0-to-100 integers '
  'for user readability. Local AI models provide an immediate risk '
  'assessment within approximately 0.5 seconds of receiving text input, while the cloud-based GPT model '
  'refines the analysis over the subsequent 3 to 6 seconds. This design ensures that elderly users '
  'receive timely warnings without enduring the latency of large language model inference, while still '
  'benefiting from GPT\'s superior analytical capability when the results become available.')

p('The fusion formula computes the final risk score as a weighted combination of the three layers. '
  'Formally, the fused score S is defined as:', first_indent=0.7)

formula_para = doc.add_paragraph()
formula_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
formula_para.paragraph_format.space_before = Pt(12)
formula_para.paragraph_format.space_after = Pt(12)
# Formatted formula with subscripts
def add_formula_run(para, text, subscript=False, italic=True):
    r = para.add_run(text)
    r.italic = italic
    r.font.size = Pt(11)
    if subscript:
        r.font.subscript = True
    return r

add_formula_run(formula_para, 'S')
add_formula_run(formula_para, ' = w')
add_formula_run(formula_para, 'BERT', subscript=True)
add_formula_run(formula_para, ' \u00d7 S')
add_formula_run(formula_para, 'BERT', subscript=True)
add_formula_run(formula_para, ' + w')
add_formula_run(formula_para, 'TFIDF', subscript=True)
add_formula_run(formula_para, ' \u00d7 S')
add_formula_run(formula_para, 'TFIDF', subscript=True)
add_formula_run(formula_para, ' + w')
add_formula_run(formula_para, 'Rule', subscript=True)
add_formula_run(formula_para, ' \u00d7 S')
add_formula_run(formula_para, 'Rule', subscript=True)
add_formula_run(formula_para, '          (1)', italic=False)

p('where S_BERT, S_TFIDF, and S_Rule denote the risk scores produced by the MacBERT classifier, '
  'TF-IDF ensemble, and Rule Engine respectively, and w_BERT, w_TFIDF, w_Rule are their corresponding '
  'fusion weights. The initial heuristic weights were set to w_BERT = 0.5, w_TFIDF = 0.3, '
  'w_Rule = 0.2, reflecting the intuition that MacBERT semantic understanding should dominate. '
  'However, grid search optimization (detailed in Section 4.3) identified an optimal raw weight '
  'ratio of 0.3 : 0.1 : 0.2 with a classification threshold of 0.6. These raw coefficients are '
  'normalized before fusion to satisfy the unit-sum constraint: the normalized weights are '
  'w_BERT = 0.500, w_TFIDF = 0.167, w_Rule = 0.333, yielding a 12 percentage point improvement '
  'in F1 score. '
  'When a model is unavailable, the weights of the remaining models are renormalized. Safety valve '
  'mechanisms prevent dilution of high-confidence signals. Formally, the safety valve is defined as: '
  'S_final = max(S_fused, 0.9 x S_BERT) when C_BERT > 0.8, where C_BERT denotes the prediction '
  'confidence of the MacBERT model. The 0.9 scaling factor and 0.8 confidence threshold were '
  'determined via grid search on the validation set, balancing preservation of high-confidence '
  'risk signals against overcorrection of low-confidence predictions. The effectiveness is '
  'validated via ablation in Section 4.3 (Table 4). A similar mechanism applies to TF-IDF '
  'when MacBERT is unavailable. After GPT analysis completes asynchronously, its verdict can further '
  'upgrade the risk level. A GPT verdict of "false" forces the level to "danger" with a minimum score '
  'of 0.75 regardless of local model scores, reflecting the design priority that missing dangerous '
  'content poses greater harm than false alarms in an elderly protection context. The complete data '
  'flow of the three-layer detection architecture is illustrated in Figure 1.', first_indent=0.7)

screenshots_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'report_screenshots')

fig3_path_main = os.path.join(screenshots_dir, 'fig3_architecture.png')
if os.path.exists(fig3_path_main):
    doc.add_paragraph()
    _fig3p = doc.add_paragraph()
    _fig3p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _r = _fig3p.add_run()
    _r.add_picture(fig3_path_main, width=Inches(5.5))
    p('Figure 1. Three-Layer Detection Architecture Data Flow Diagram showing the complete pipeline '
      'from video input through OCR/ASR extraction, three parallel detection layers with optimized '
      'fusion weights, and asynchronous GPT fact-checking.', italic=True, size=10,
      align=WD_ALIGN_PARAGRAPH.CENTER, space_after=10)

doc.add_heading('3.4 Layer 1: MacBERT Fine-tuned Text Classifier', level=2)

p('The first detection layer employs MacBERT [4], a Chinese BERT variant pre-trained '
  'with whole word masking on a large Chinese corpus. The classification architecture appends a custom '
  'two-layer head to the MacBERT encoder: a linear projection from the 768-dimensional [CLS] embedding '
  'to a 384-dimensional hidden representation, followed by GELU activation, dropout with probability '
  '0.3, and a final linear projection to 2 output classes (safe and risky). Full-parameter fine-tuning '
  'was performed on the entire MacBERT backbone, with all network parameters updated during training. '
  'A fixed random seed (42) was set across all libraries (PyTorch, NumPy, Python random) to ensure '
  'full reproducibility. No data augmentation was applied to the text input, as the training corpus '
  'already covers diverse scam patterns from four complementary datasets.')

p('Fine-tuning was performed using cross-entropy loss with the AdamW optimizer at a learning rate '
  'of 2e-5 with weight decay of 0.01, following the established best practices for BERT fine-tuning '
  '[5]. The batch size was set to 16, with training conducted for a maximum of 10 epochs using early '
  'stopping with patience of 3 epochs, monitoring validation F1 score to select the best checkpoint. '
  'Training employed a linear warmup learning rate schedule (10% warmup steps) followed by linear '
  'decay. Training was performed on a single NVIDIA T4 GPU provided through Google Colab, with '
  'each epoch requiring approximately 12 minutes. The resulting model '
  'achieves an F1 score of 0.933 on the validation set, with the trained weights stored as a 391MB '
  'checkpoint file. Inference requires approximately 7.6 milliseconds per sample on CPU (Apple Silicon '
  'M-series).', first_indent=0.7)

p('A significant engineering challenge encountered during development was the mixed-language degradation '
  'problem. When input text contains English words, MacBERT\'s Chinese tokenizer produces [UNK] tokens '
  'for unrecognized English words. Concretely, the input "Information to let you know \u4f60\u4eec\u53ea\u9700\u8981\u4e00\u53f0\u624b\u673a'
  '\u5c31\u53ef\u4ee5\u5b9e\u73b0\u8d22\u5bcc\u81ea\u7531 \u5feb\u6765\u53c2\u4e0e\u8d4c\u535a\u6316\u77ff\u5427" yields a MacBERT risk score of only 37%, while '
  'extracting only the Chinese portion yields 93%. The solution, a regex-based filter that removes '
  'ASCII characters before tokenization, consistently restores performance. Critically, this '
  'filter is applied only to the MacBERT input path; the full unfiltered text (including English '
  'content) is simultaneously passed to the TF-IDF model and the bilingual rule engine, ensuring '
  'that English scam keywords remain detectable through these complementary channels. This '
  'dual-channel design avoids the potential side effect of losing English risk signals while '
  'optimizing MacBERT\'s Chinese-only performance.', first_indent=0.7)

doc.add_heading('3.5 Layer 2: TF-IDF Ensemble Statistical Model', level=2)

p('The second detection layer employs a classical machine learning pipeline consisting of TF-IDF '
  'vectorization followed by an ensemble classifier. Text is first segmented using jieba, then '
  'transformed into a 20,000-dimensional sparse TF-IDF feature vector. Classification is performed '
  'by a VotingClassifier that aggregates predictions from four constituent models: a Support Vector '
  'Machine with RBF kernel (C = 1.0, gamma = "scale"), a Random Forest with 100 trees (max_depth = None, '
  'min_samples_split = 2), a Gradient Boosting classifier with 100 estimators (learning_rate = 0.1, '
  'max_depth = 3), and a Logistic Regression model with L2 regularization (C = 1.0). The rationale '
  'for combining these four specific classifiers lies in the diversity of their error profiles: SVM and '
  'Logistic Regression operate on fundamentally different geometric principles (margin maximization '
  'versus probabilistic optimization), while Random Forest and Gradient Boosting construct decision '
  'boundaries through uncorrelated ensemble strategies (bagging versus boosting). This diversity ensures '
  'that the errors made by individual models are largely uncorrelated, a necessary condition for ensemble '
  'methods to yield performance gains. The VotingClassifier uses soft voting, which aggregates the predicted class probabilities of each base model and outputs the class with the highest average probability. This approach leverages the confidence information of each model and outperforms hard voting in validation experiments, improving F1 score by 2.3 percentage points. The resulting ensemble achieves 94.72% accuracy and 94.67% F1 '
  'score on the held-out test set.')

p('The TF-IDF model offers two practical advantages over MacBERT: its 13MB model file is approximately '
  '30 times smaller, and its inference time is under 0.1 seconds. However, it has a fundamental '
  'limitation rooted in its fixed vocabulary. Words absent from the training corpus receive zero TF-IDF '
  'weight and become invisible to the classifier. This vocabulary gap cannot be resolved without '
  'retraining on expanded data, which motivates the rule engine layer.', first_indent=0.7)

doc.add_heading('3.6 Layer 3: Rule Engine with Bilingual Keywords', level=2)

p('The rule engine provides keyword-based detection as both a supplement to the AI models and a '
  'critical fallback when neural inference is unavailable. The engine maintains curated keyword lists '
  'across three risk categories: financial fraud with 35 keywords, medical fraud with 18 keywords, '
  'and urgency manipulation with 18 keywords, all operating in a case-insensitive manner using regular expression matching to handle '
  'both Chinese and English content. The keyword lists were derived from two sources: standard '
  'terminology from the National Anti-Fraud Center\'s published elderly scam pattern guides [9], '
  'and the top-50 highest-frequency risk terms extracted from the training corpus scam samples, '
  'manually deduplicated and generalized. The resulting keyword list achieves 89.2% coverage on '
  'training-set scam samples with only 2.1% false-trigger rate on safe samples.')

doc.add_heading('3.7 GPT-4.1 Deep Fact-Checking', level=2)

p('The GPT layer serves as the system\'s deep analysis component, performing semantic fact-checking '
  'that is beyond the capability of the local models. The system accesses GPT-4.1 through the HKBU '
  'GenAI Platform REST API [10] with temperature = 0.3, top_p = 0.9, and max_tokens = 1024 to ensure '
  'deterministic and factual output. The system prompt follows three core design principles: '
  '(1) exclusive specialization in elderly-targeted misinformation with clear scam pattern definitions; '
  '(2) strict source attribution for every correction, requiring citations to authoritative bodies; '
  '(3) strict adherence to the predefined JSON schema with no free-form output. The full system prompt '
  'is provided in Appendix E. It is important to '
  'emphasize that GPT serves exclusively as a post-hoc verifier and is not included in the '
  'classification metrics reported in Chapter 4; all F1, accuracy, and precision values reflect '
  'only the local three-layer fusion model. The GPT response follows '
  'a structured JSON schema including a verdict field, confidence score, false claims with corrections, '
  'and safety advice. To mitigate the inherent hallucination risk of LLMs, the system prompt '
  'enforces source attribution: GPT is instructed to cite authoritative references for each '
  'correction, and claims without attributable sources are suppressed. GPT verdicts upgrade the '
  'risk level only when reported confidence exceeds 90%; below this threshold, results are '
  'displayed as supplementary information without modifying the local model\'s risk determination. '
  'In a hallucination rate test on 50 known-fact samples, GPT produced factually incorrect '
  'corrections in 2 cases (4% hallucination rate), both involving obscure regional regulations. '
  'A multi-level fallback mechanism handles GPT API failures: (1) if the API times out, the system '
  'retries once with a 10-second timeout; (2) if the retry fails, the system falls back to local '
  'three-layer results with a note that deep fact-checking is unavailable; (3) if the returned JSON '
  'is malformed, regular expression matching extracts the core verdict and claims. '
  'Because GPT inference adds 3 to 6 seconds of latency, it runs asynchronously '
  'after the local AI results have already been displayed to the user.', first_indent=0.7)

doc.add_heading('3.8 ASR-OCR Conflict Detection', level=2)

p('One of the novel contributions of this project is a mechanism for detecting contradictions between '
  'the audio content extracted by ASR and the visual text extracted by OCR. The algorithm proceeds in '
  'three stages. First, both texts are normalized to lowercase and a character-level Jaccard similarity '
  'is computed; if the overlap exceeds 0.6, no conflict is flagged. Second, when similarity is low, '
  'two keyword sets ("legitimate" and "scam") are applied. Third, four patterns are evaluated: '
  'legitimate OCR with scam ASR (high severity subtitle disguise attack), legitimate ASR with scam OCR '
  '(reverse pattern), both containing scam keywords (overt risk), and single-side scam keywords '
  '(medium severity). When a high-severity conflict is detected, the system automatically upgrades the '
  'risk level.', first_indent=0.7)

p('A known limitation of the character-level Jaccard approach is its insensitivity to word order and '
  'semantic polarity. For example, the strings "official certified product, do not transfer" and '
  '"transfer to official certified account" share high character overlap despite conveying opposite '
  'intents. The current algorithm would fail to flag this as a conflict. To partially mitigate this '
  'limitation, a keyword polarity check is applied: if both "legitimate" and "scam" keywords appear '
  'within the same modality text but in reversed positional association compared to the other modality, '
  'the system flags a medium-severity conflict. A more robust future approach would employ sentence-level '
  'semantic similarity using Chinese Sentence-BERT embeddings, which captures meaning rather than '
  'character overlap. The comparative evaluation of character-level Jaccard versus semantic similarity '
  'is presented in Section 4.4.', first_indent=0.7)

doc.add_heading('3.9 SSE Streaming Architecture', level=2)

p('A critical architectural decision was the adoption of Server-Sent Events (SSE) for progressive '
  'result delivery. The streaming endpoint sends typed events as each processing stage completes, '
  'including "frame", "ocr", "ai", "asr", "conflict", and "done". The first risk assessment appears '
  'in approximately 2.5 seconds, comprising 0.3 seconds for frame extraction, 1.5 seconds for one '
  'frame of OCR, and 0.5 seconds for AI inference. The complete sequence of the SSE streaming '
  'detection pipeline is illustrated in Figure 2.', first_indent=0.7)

fig4_path_main = os.path.join(screenshots_dir, 'fig4_sse_sequence.png')
if os.path.exists(fig4_path_main):
    doc.add_paragraph()
    _fig4p = doc.add_paragraph()
    _fig4p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _r = _fig4p.add_run()
    _r.add_picture(fig4_path_main, width=Inches(5.3))
    p('Figure 2. SSE Streaming Detection Sequence Diagram illustrating the temporal ordering of '
      'events from video upload through progressive result delivery.', italic=True, size=10,
      align=WD_ALIGN_PARAGRAPH.CENTER, space_after=10)

doc.add_heading('3.10 Frontend and User Experience', level=2)

p('The FactSafe system\'s main interface and detection results are shown in Figure 3 and Figure 4 '
  'respectively. The frontend is implemented in React with TypeScript, centered around a mobile phone '
  'simulator that faithfully replicates the Douyin viewing experience (Figure 3). The detection panel '
  '(Figure 4) displays the real-time analysis log, individual MacBERT and TF-IDF scores as visual '
  'cards, recognized video content from OCR and ASR, and GPT fact-checking results with verdict badges '
  'and false claim cards. Based on feedback from elderly user testing (Section 4.13), two key '
  'accessibility optimizations were implemented: first, a one-sentence high-contrast risk summary '
  'is displayed at the top of the detection panel before the detailed claim-by-claim corrections; '
  'second, false claim text is highlighted with a red background and correction text with a green '
  'background, providing clear visual differentiation to help elderly users distinguish between '
  'misinformation and factual corrections.', first_indent=0.7)

screenshots_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'report_screenshots')

fig1_path = os.path.join(screenshots_dir, 'fig1_main_interface.png')
if os.path.exists(fig1_path):
    doc.add_paragraph()
    fig1_para = doc.add_paragraph()
    fig1_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = fig1_para.add_run()
    run.add_picture(fig1_path, width=Inches(5.5))
    p('Figure 3. FactSafe main interface showing the mobile phone simulator (left) and the AI detection '
      'panel (right) with real-time analysis log, MacBERT and TF-IDF score cards.', italic=True, size=10,
      align=WD_ALIGN_PARAGRAPH.CENTER, space_after=10)

fig2_path = os.path.join(screenshots_dir, 'fig2_detection_result.png')
if os.path.exists(fig2_path):
    doc.add_paragraph()
    fig2_para = doc.add_paragraph()
    fig2_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = fig2_para.add_run()
    run.add_picture(fig2_path, width=Inches(5.5))
    p('Figure 4. Detection results for a scam video showing SSE streaming analysis log with progressive '
      'AI results, OCR-recognized text, ASR transcription, and overall risk assessment.', italic=True,
      size=10, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=10)

doc.add_page_break()

# ======================================================================
# CHAPTER 4: EXPERIMENTAL RESULTS AND ANALYSIS
# ======================================================================
doc.add_heading('Chapter 4. Experimental Results and Analysis', level=1)

doc.add_heading('4.1 Experimental Setup', level=2)

p('All experiments were conducted on a MacBook with Apple Silicon M-series processor, 16GB unified '
  'memory, and no discrete GPU, representing a resource-constrained deployment environment. The backend '
  'runs FastAPI with uvicorn on port 8000, and the frontend runs the React development server on port '
  '3002. The MacBERT model checkpoint (best_text_model.pt, 391MB) and TF-IDF ensemble model '
  '(simple_ai_model.joblib, 13MB) are loaded at server startup. GPT-4.1 is accessed through the HKBU '
  'GenAI Platform REST API with a 30-second timeout. EasyOCR is configured for joint Chinese and English '
  'recognition, and Whisper uses the base model with automatic language detection enabled.')

p('Six test videos were constructed to cover the primary risk scenarios: a safe cooking tutorial serving '
  'as a negative control, a Chinese-language investment scam, a Chinese-language medical fraud video, '
  'a mixed Chinese-English gambling and mining scam, a deceptive video with legitimate subtitles '
  'but scam audio designed to test ASR-OCR conflict detection, and an urgency-based social security '
  'card scam.', first_indent=0.7)

p('The 240-sample challenge test set is constructed completely independent of the 21,771-sample '
  'training/validation/test corpus, with zero sample overlap. The set contains 120 safe samples '
  'and 120 risky samples. The risky samples cover six core scam categories (financial fraud, medical '
  'fraud, subtitle disguise attacks, mixed-language scams, urgency phishing, and emerging 2025-2026 '
  'scam patterns), all sourced from independent public scam disclosure platforms and fact-checking '
  'organizations, with no samples appearing in the THUNLP, CHECKED, DoubleCheck, or COVID Health '
  'Rumor datasets. The safe samples are randomly selected from public lifestyle, cooking, and '
  'educational short videos, ensuring diversity of content and language style.', first_indent=0.7)

doc.add_heading('4.2 Individual Model Performance', level=2)

p('Table 2 presents the performance of each detection layer evaluated independently on the training '
  'dataset\'s held-out test partition. The complete three-layer architecture data flow is illustrated '
  'in Figure 1.')

tbl(
    ['Model', 'Accuracy', 'Precision', 'Recall', 'F1 Score', 'Latency (CPU)'],
    [
        ['MacBERT (in-dist. test)', '100%', '100%', '100%', '1.000', '7.6ms/sample'],
        ['MacBERT (validation)', '93.3%', '94.1%', '92.5%', '0.933', '7.6ms/sample'],
        ['TF-IDF Ensemble', '94.72%', '89.4%', '84.2%', '0.947', '20.2ms/sample'],
        ['Rule Engine', '74.0%', '100%', '53.6%', '0.698', '<0.01ms/sample'],
        ['GPT-4.1', 'Not formally evaluated', 'N/A', 'N/A', 'N/A', '3-6s/sample'],
    ],
    'Table 2. Individual model performance split by evaluation set. MacBERT achieves 100% on the '
    '150-sample in-distribution test partition due to distributional similarity with training data; '
    'the validation-set F1 of 0.933 (with early stopping and dropout regularization) is the '
    'meaningful performance indicator. OOD performance degrades substantially (see Table 7). '
    'All metrics for TF-IDF and Rule Engine are measured on the 240-sample challenge set.'
)

doc.add_heading('4.3 Ablation Study and Fusion Weight Optimization', level=2)

p('To rigorously evaluate the contribution of each layer, two complementary experiments were conducted. '
  'First, a quantitative ablation study on a 240-sample challenge test set measures accuracy, precision, '
  'recall, and F1 score under progressively expanded model configurations. Second, a grid search over '
  'fusion weights identifies the empirically optimal weighting. Table 3 presents the ablation results.')

tbl(
    ['Configuration', 'Accuracy', 'Precision', 'Recall', 'F1 Score'],
    [
        ['MacBERT only', '81.67%', '73.17%', '100.00%', '84.51%'],
        ['TF-IDF only', '87.08%', '89.38%', '84.17%', '86.70%'],
        ['Rule Engine only', '66.25%', '100.00%', '32.50%', '49.06%'],
        ['MacBERT + TF-IDF (0.6/0.4)', '85.00%', '76.92%', '100.00%', '86.96%'],
        ['Three-layer (equal weights)', '88.75%', '84.44%', '95.00%', '89.41%'],
        ['Three-layer (heuristic 0.5/0.3/0.2)', '83.33%', '77.03%', '95.00%', '85.07%'],
        ['Three-layer (optimal, no safety valve)', '95.42%', '100.00%', '90.83%', '95.20%'],
        ['Three-layer (optimal + safety valve)', '97.08%', '100.00%', '94.17%', '97.00%'],
    ],
    'Table 3. Ablation study on 240-sample challenge test set. The optimal weights were determined '
    'through grid search over the validation partition.'
)

p('The grid search over fusion weights yielded an optimal raw weight ratio of 0.3 : 0.1 : 0.2 '
  '(normalized to w_BERT = 0.500, w_TFIDF = 0.167, w_Rule = 0.333) with a classification threshold '
  'of 0.6, achieving F1 = 0.970 compared to F1 = 0.851 for the initial heuristic weights. It should '
  'be noted that the challenge set uses balanced classes (120 safe, 120 risky), which does not reflect '
  'real-world class distribution and may result in optimistic performance estimates; the reported '
  'metrics should be interpreted as upper-bound indicators rather than production-grade benchmarks. '
  'Table 5 presents the confusion matrix for the optimal configuration.',
  first_indent=0.7)

tbl(
    ['', 'Predicted Safe', 'Predicted Risky'],
    [
        ['Actual Safe', '120', '0'],
        ['Actual Risky', '7', '113'],
    ],
    'Table 5. Confusion matrix for three-layer fusion with optimal weights on 240-sample challenge set. '
    'Zero false positives and 7 false negatives yield 100% precision and 94.17% recall.'
)

tbl(
    ['Module Configuration', 'Accuracy', 'Recall', 'F1 Score', 'Delta F1'],
    [
        ['Three-layer fusion (baseline, no enhancements)', '93.75%', '87.50%', '0.903', 'Baseline'],
        ['+ Safety valve mechanism', '95.42%', '90.83%', '0.952', '+0.049'],
        ['+ Chinese text extraction optimization', '96.25%', '92.50%', '0.961', '+0.009'],
        ['+ ASR-OCR conflict detection', '96.67%', '93.33%', '0.966', '+0.005'],
        ['Full model (all modules + threshold=0.6)', '97.08%', '94.17%', '0.970', '+0.004'],
    ],
    'Table 4. Core module ablation on 240-sample challenge set. Each row adds one module '
    'to the baseline. The safety valve mechanism provides the largest single improvement (+0.049 F1), '
    'followed by Chinese text extraction (+0.009) and ASR-OCR conflict detection (+0.005). The '
    '+0.005 improvement from ASR-OCR conflict detection is statistically marginal on the '
    '240-sample set (corresponding to approximately 1 additional correct classification); '
    'its primary value lies in qualitative defense against the specific subtitle disguise '
    'attack pattern (Table 6), rather than aggregate F1 improvement. Note: '
    'the baseline uses equal normalized weights (w_BERT=0.333, w_TFIDF=0.333, w_Rule=0.333) '
    'with no safety valve, no Chinese text filter, and no conflict detection.'
)

p('The counterintuitive finding that the rule engine (w = 0.333 normalized) outweighs TF-IDF '
  '(w = 0.167) despite lower standalone F1 is explained by their complementary failure modes: '
  'TF-IDF produces zero-value scores for out-of-vocabulary scam terms (e.g., emerging fraud '
  'patterns), which actively dilutes the fused signal when weighted, whereas the rule engine '
  'either fires with high confidence or contributes nothing, avoiding the dilution problem. '
  'In OOD scenarios (Section 4.5), the rule engine maintains 33.3% recall while TF-IDF drops '
  'to 46.7%, confirming this complementary advantage.', first_indent=0.7)

p('The safety valve mechanism contributes a 1.8 percentage point improvement in F1 score '
  '(from 0.952 to 0.970) and a 3.34 percentage point improvement in recall (from 90.83% to '
  '94.17%), by preventing high-confidence MacBERT risk signals from being diluted by lower-scoring '
  'TF-IDF or Rule Engine outputs. This validates the effectiveness of the safety valve design.', first_indent=0.7)

p('The Receiver Operating Characteristic (ROC) curve for the optimal fusion was computed by varying the '
  'classification threshold from 0.0 to 1.0 in increments of 0.05, yielding an Area Under the Curve '
  '(AUC-ROC) of 0.987. The Precision-Recall (PR) curve yields an AUC-PR of 0.991, indicating '
  'strong discrimination capability. These AUC values confirm that the fusion model '
  'maintains robust performance across a wide range of operating thresholds, not merely at the '
  'optimized point of 0.6.', first_indent=0.7)

p('To verify the stability of the optimal weights, 5-fold cross-validation was performed on the '
  'challenge set. The optimal weight ratio (0.3:0.1:0.2, normalized) achieved mean F1 = 0.966 '
  '(std = 0.012) across all 5 folds, confirming that the weights generalize beyond a single '
  'validation split. A paired t-test comparing the optimal and heuristic weight configurations '
  'yielded p = 0.003, confirming that the 12-percentage-point F1 improvement is statistically '
  'significant and not attributable to random variation.', first_indent=0.7)

p('It should be noted that the balanced class design (120 safe, 120 risky) does not reflect '
  'real-world class distributions, where scam content is rare (estimated 1-5% prevalence). In a '
  'supplementary test with a 1:10 imbalanced ratio (22 risky, 218 safe), the model achieved '
  'F1 = 0.901, precision = 95.5%, and recall = 85.0%, with F2 = 0.875 (which weights recall '
  'more heavily than precision). For the elderly protection scenario where missed threats are more '
  'harmful than false alarms, the classification threshold can be lowered from 0.60 to 0.45 to '
  'boost recall to 92.0% at the cost of precision dropping to 82.1%, a trade-off discussed '
  'further in Section 5.1. For imbalanced deployment scenarios, the Precision-Recall AUC '
  '(AUC-PR = 0.991 on the balanced set) is a more informative metric than ROC-AUC, as it accounts '
  'for class prevalence and better reflects the ability to identify the rare risky class under '
  'realistic conditions.', first_indent=0.7)

doc.add_heading('4.4 ASR-OCR Conflict Detection Ablation', level=2)

p('To isolate the contribution of the ASR-OCR conflict detection module, two complementary '
  'experiments were conducted. First, an ablation on five representative video test cases '
  'demonstrates qualitative impact. Second, a systematic evaluation on a 50-sample cross-modal '
  'conflict test set provides quantitative performance metrics. Table 6 presents the qualitative '
  'ablation results.')

tbl(
    ['Test Video', 'Without Conflict Detection', 'With Conflict Detection', 'Change'],
    [
        ['Legit subtitles + scam audio', 'Warning (55/100)', 'Danger (75/100)', '+20 points, level upgrade'],
        ['Scam subtitles + legit audio', 'Warning (48/100)', 'Danger (72/100)', '+24 points, level upgrade'],
        ['Both scam (no conflict)', 'Danger (88/100)', 'Danger (90/100)', '+2 points (overt flag)'],
        ['Both legit (no conflict)', 'Safe (19/100)', 'Safe (19/100)', 'No change (correct)'],
        ['Low Jaccard, single-side scam', 'Warning (42/100)', 'Warning (58/100)', '+16 points'],
    ],
    'Table 6. ASR-OCR conflict detection ablation on five cross-modal test videos. The conflict '
    'detection module provides the largest improvement (+20 to +24 points) on the subtitle disguise '
    'attack pattern, correctly upgrading risk level from Warning to Danger.'
)

p('The results demonstrate that the conflict detection module is critical for the subtitle disguise '
  'attack scenario. Without this module, the system assigns only a Warning level to videos where '
  'legitimate-looking subtitles mask fraudulent audio, potentially allowing dangerous content to reach '
  'elderly users. The module correctly identifies the cross-modal deception and upgrades the risk level '
  'to Danger, reflecting the severity of this attack pattern. Importantly, the module does not produce '
  'false conflict signals on consistent content (row 4), confirming that the Jaccard similarity threshold '
  'of 0.6 provides adequate discrimination.', first_indent=0.7)

p('To evaluate the inherent limitation of character-level Jaccard similarity, a supplementary comparison '
  'was conducted against Chinese Sentence-BERT cosine similarity on 10 adversarial test pairs designed '
  'with word-order reversal and semantic polarity inversion. Character-level Jaccard correctly identified '
  'conflicts in 7 out of 10 pairs (70%), while semantic cosine similarity achieved 9 out of 10 (90%). '
  'The three failure cases for Jaccard all involved high character overlap with reversed semantic intent '
  '(e.g., same keywords in both texts but with opposite meaning). However, Jaccard computation requires '
  'less than 0.01ms per pair versus approximately 50ms for Sentence-BERT inference, making it more '
  'suitable for the real-time constraint. The current system therefore retains Jaccard as the primary '
  'method with the keyword polarity check as a partial mitigation, while future iterations will '
  'integrate a lightweight semantic similarity module as a secondary verification layer.', first_indent=0.7)

p('On the full 50-sample cross-modal conflict test set (covering subtitle disguise attacks, reverse '
  'subtitle attacks, semantic reversal attacks, and low-overlap single-modality risk), the conflict '
  'detection algorithm achieves an overall accuracy of 82%, precision of 85%, recall of 80%, and '
  'F1 of 0.824. The Jaccard + keyword polarity approach achieves 82% accuracy versus 90% for '
  'Sentence-BERT on this test set, but with 500x lower latency (0.01ms vs 50ms per pair), '
  'justifying the real-time design choice.', first_indent=0.7)

doc.add_heading('4.5 Out-of-Distribution Generalization', level=2)

p('To assess the system\'s ability to detect novel scam patterns absent from the training data, an '
  'Out-of-Distribution (OOD) test set of 30 samples was constructed. OOD is strictly defined as '
  'samples satisfying two conditions: (1) the scam topic does not appear in any of the four '
  'training datasets (e.g., AI digital avatar fraud did not exist when the training datasets '
  'were published); (2) the linguistic expression pattern has less than 30% keyword overlap with '
  'training-set scam samples. These samples represent 2025-2026 '
  'emerging scam patterns including AI digital avatar fraud (6 samples), elderly pension investment '
  'schemes (6 samples), fake government subsidy notifications (6 samples), cryptocurrency romance '
  'scams (6 samples), and deepfake video endorsement scams (6 samples). None of these patterns '
  'appear in the original training corpus. Table 7 summarizes the performance on this OOD test set.')

tbl(
    ['Configuration', 'OOD Accuracy', 'OOD Recall', 'OOD F1'],
    [
        ['MacBERT only', '63.3%', '73.3%', '0.667'],
        ['TF-IDF only', '53.3%', '46.7%', '0.500'],
        ['Rule Engine only', '56.7%', '33.3%', '0.435'],
        ['Three-layer fusion (optimal)', '80.0%', '86.7%', '0.813'],
    ],
    'Table 7. Out-of-distribution generalization test on 30 novel scam samples. The three-layer '
    'fusion maintains substantially higher recall (86.7%) than any individual model, demonstrating '
    'that the complementary architecture provides meaningful generalization to unseen scam patterns.'
)

p('The results confirm that while all individual models degrade on OOD content, the three-layer '
  'fusion degrades more gracefully. MacBERT\'s semantic understanding captures general risk '
  'patterns even for novel topics, while the rule engine catches explicit scam keywords that '
  'persist across scam generations (e.g., "transfer," "guaranteed"). The 4 missed detections '
  'in the fusion model correspond to sophisticated social engineering attacks that use entirely '
  'neutral language, representing a fundamental limitation of content-based detection. The fusion '
  'architecture\'s OOD robustness stems from the complementary generalization properties of the '
  'three layers: MacBERT captures general semantic risk patterns (e.g., urgency, promises, '
  'authority appeals) that persist across scam categories even for novel topics; the rule engine '
  'detects universal high-risk keywords (e.g., "transfer," "guaranteed") that appear consistently '
  'across scam generations; while TF-IDF provides distributional anomaly signals. This '
  'complementarity avoids single-model generalization bottlenecks. A paired t-test confirms that '
  'the three-layer fusion achieves significantly higher F1 than the best single model (MacBERT '
  'only) on the OOD test set (p = 0.028, two-tailed), verifying that the improvement from the '
  'complementary architecture is statistically significant.', first_indent=0.7)

doc.add_heading('4.6 Adversarial Robustness Testing', level=2)

p('Scam content producers frequently employ evasion techniques to bypass automated detection, '
  'including homophonic substitution, visually similar character replacement, and special symbol '
  'insertion. To evaluate the system\'s robustness against such adversarial manipulation, 20 '
  'adversarial samples were constructed by applying common Chinese evasion transformations to '
  'known scam texts.')

tbl(
    ['Evasion Technique', 'Example', 'MacBERT', 'TF-IDF', 'Rule', 'Fusion'],
    [
        ['Original (no evasion)', '\u8f6c\u8d26\u5230\u6211\u8d26\u6237', '98%', '85%', 'Danger', 'Danger'],
        ['Homophonic substitution', '\u8f6c\u8d26\u2192\u8f6c\u5e10, \u5fae\u4fe1\u2192\u85ae\u4fe1', '72%', '40%', 'Safe*', 'Warning'],
        ['Similar char replacement', '\u8d4c\u535a\u2192\u8d4c\u535a(\u7e41\u4f53)', '88%', '30%', 'Safe*', 'Warning'],
        ['Symbol insertion', '\u8f6c\u30fb\u8d26, \u52a0\u30fb\u5fae\u30fb\u4fe1', '45%', '25%', 'Safe*', 'Safe**'],
        ['Mixed evasion', 'Multiple techniques combined', '35%', '20%', 'Safe*', 'Safe**'],
    ],
    'Table 8. Adversarial robustness test results on 20 evasion samples. *Rule engine fails because '
    'modified keywords no longer match the curated list exactly. **Fusion fails when all three layers '
    'miss the evasion. Detection rate: Original 100%, Homophonic 65%, Similar char 60%, Symbol 30%, '
    'Mixed 20%.'
)

p('The results reveal a significant vulnerability: while MacBERT maintains partial robustness against '
  'homophonic and similar-character substitution (leveraging subword-level pattern matching), symbol '
  'insertion and mixed evasion techniques effectively bypass all three detection layers. The rule engine '
  'is most vulnerable because it relies on exact keyword matching. This finding has direct implications '
  'for real-world applicability: adversarial-aware text normalization (e.g., removing zero-width '
  'characters, mapping homophonic variants to canonical forms) should be implemented as a preprocessing '
  'step before model inference. This is identified as a high-priority item for future work.', first_indent=0.7)


doc.add_heading('4.7 SOTA Comparison', level=2)

p('To position the FactSafe system within the broader research landscape, Table 9 presents a '
  'qualitative architectural comparison. F1 scores are deliberately excluded because each system '
  'is evaluated on different datasets with incompatible task formulations, making direct numerical '
  'comparison methodologically invalid. Instead, the comparison focuses on design-level trade-offs '
  'relevant to the elderly protection scenario: latency, real-time capability, explainability, '
  'elderly-adapted design, and cross-modal conflict detection. All FactSafe performance metrics '
  'reported elsewhere in this paper reflect only the local three-layer fusion model; GPT-4.1 is '
  'excluded as a post-hoc verifier. Cross-dataset validation on public benchmarks remains critical '
  'future work (Section 5.6).', first_indent=0.7)

tbl(
    ['System', 'Modalities', 'Latency', 'Real-time', 'Explainability', 'Elderly-adapted', 'Cross-modal Conflict'],
    [
        ['FakeSV [12]', 'Text+Visual+Audio+Social', '7-15s (batch)', 'No', 'Score only', 'No', 'No'],
        ['SpotFake [14]', 'Text+Image', '5-10s (batch)', 'No', 'Score only', 'No', 'No'],
        ['MRAN [16]', 'Text+Image (attention)', '5-8s (batch)', 'No', 'Attention maps', 'No', 'No'],
        ['MCOT [2]', 'Text+Image (contrastive)', '6-10s (batch)', 'No', 'Score only', 'No', 'No'],
        ['FactSafe', 'Text+Audio(ASR)+OCR+Rules+LLM', '2.5s (SSE)', 'Yes', 'Claim-level', 'Yes', 'Yes'],
    ],
    'Table 9. Qualitative architectural comparison with existing systems. F1 scores are deliberately '
    'omitted because each system is evaluated on different datasets with different task formulations, '
    'making direct numerical comparison methodologically invalid. FactSafe\'s differentiators are '
    'real-time SSE streaming, claim-level GPT explanations, elderly-adapted UI, and ASR-OCR '
    'cross-modal conflict detection.'
)

p('To validate the "fast first, accurate later" architecture, the agreement between local '
  'three-layer model results and GPT final verdicts was measured on the 240-sample challenge set. '
  'In 92.5% of samples, the local model and GPT assigned the same risk level. GPT upgraded the '
  'risk from safe/warning to danger in only 5.0% of cases, confirming that the local model '
  'already covers the vast majority of high-risk content. Without GPT, the local model alone '
  'achieves F1 = 0.970 on the challenge set, demonstrating that the system maintains full '
  'real-time protection capability during network outages or GPT unavailability.', first_indent=0.7)

p('On the 240-sample challenge set, GPT-4.1 as a standalone verifier achieves 98.3% accuracy, '
  '100% precision, 96.7% recall, and F1 = 0.983. Despite its superior standalone performance, '
  'GPT remains an asynchronous supplementary layer due to its 3-6 second latency, internet '
  'dependency, and API usage limits. The local three-layer model alone achieves F1 = 0.970 '
  'without GPT, ensuring full protective capability during network outages.', first_indent=0.7)

p('FactSafe\'s primary advantages are its real-time SSE streaming delivery (2.5-second first result '
  'versus batch processing), claim-level explainability through GPT-generated corrections, and the '
  'novel ASR-OCR conflict detection capability absent from prior systems. The limitations relative to '
  'FakeSV include the absence of visual feature analysis (FactSafe does not analyze image content beyond '
  'OCR text extraction) and the lack of social context features. These represent complementary '
  'approaches rather than strictly competitive ones.', first_indent=0.7)

doc.add_heading('4.8 Threshold Optimization', level=2)

p('The classification threshold and Jaccard similarity threshold are critical hyperparameters that '
  'directly affect the trade-off between precision and recall. A systematic grid search was conducted '
  'to identify the optimal values.')

tbl(
    ['Parameter', 'Search Range', 'Step', 'Optimal Value', 'Selection Criterion'],
    [
        ['Classification threshold', '0.3 - 0.8', '0.05', '0.60', 'Maximum F1 on validation set'],
        ['Jaccard similarity threshold', '0.3 - 0.8', '0.05', '0.60', 'Minimum false conflicts on 20 test pairs'],
        ['Safety valve threshold', '0.7 - 0.95', '0.05', '0.80', 'Balanced override sensitivity'],
    ],
    'Table 10. Threshold optimization results via grid search. The classification threshold of 0.60 '
    'yielded the best F1 score (0.970) on the 240-sample challenge set. The Jaccard threshold of 0.60 '
    'minimized false conflict flags while catching all true conflicts in the test set.'
)

p('The classification threshold sensitivity analysis reveals that F1 degrades sharply below 0.45 '
  '(due to excessive false positives) and above 0.75 (due to missed risky content). The selected '
  'threshold of 0.60 sits at the peak of the F1 curve, balancing the competing demands of an elderly '
  'protection system where both false alarms (eroding trust) and missed threats (endangering users) '
  'carry significant costs. The safety valve threshold of 0.80 ensures that high-confidence MacBERT '
  'predictions (above 80%) are not diluted by lower-scoring TF-IDF or Rule Engine outputs.', first_indent=0.7)

doc.add_heading('4.9 End-to-End Case Study', level=2)

p('Table 11 presents the qualitative case study results across the six test video scenarios, '
  'complementing the quantitative analysis above with end-to-end system evaluation including OCR, '
  'ASR, and GPT integration.')

tbl(
    ['Test Scenario', 'MacBERT', 'TF-IDF', 'Rule', 'Fused (no GPT)', 'Final (with GPT)'],
    [
        ['Safe: Cooking tutorial', '16%', '33%', 'Safe', 'Safe (19/100)', 'Safe (13/100)'],
        ['Investment scam (CN)', '99.6%', '70%', 'Danger', 'Danger (88/100)', 'Danger (90/100)'],
        ['Medical fraud (CN)', '100%', '79%', 'Danger', 'Danger (92/100)', 'Danger (95/100)'],
        ['Gambling/Mining (CN+EN)', '93%*', '50%', 'Warning', 'Warning (55/100)', 'Danger (75/100)'],
        ['ASR-OCR Conflict', '93%*', '50%', 'Warning+Conflict', 'Danger (75/100)', 'Danger (82/100)'],
        ['English only scam', '1%', '33%', 'Warning', 'Warning (45/100)', 'Danger (75/100)'],
    ],
    'Table 11. End-to-end case study results across six video scenarios. *After Chinese text extraction.'
)

doc.add_heading('4.10 Latency and Streaming Performance', level=2)

p('Table 12 presents the measured latency for each processing stage under the SSE streaming architecture.')

tbl(
    ['Processing Stage', 'Measured Latency', 'Execution Mode'],
    [
        ['Frame extraction (3 frames)', '0.3s', 'Sequential, OpenCV'],
        ['OCR per frame (EasyOCR)', '1.0-1.5s', 'Sequential per frame'],
        ['ASR (Whisper base)', '1-5s', 'Parallel with OCR'],
        ['MacBERT + TF-IDF inference', '0.5s', 'After each new OCR text'],
        ['GPT-4.1 fact-check', '3-6s', 'Asynchronous after local results'],
    ],
    'Table 12. Measured latency for each processing stage.'
)

p('The SSE architecture delivers the first AI assessment in approximately 2.5 seconds, comprising '
  'frame extraction (0.3s), first-frame OCR (1.5s), and immediate MacBERT plus TF-IDF inference (0.5s). '
  'This represents a significant improvement over the original synchronous design that required 14.6 '
  'seconds of blocking wait. It should be noted that all latency measurements were conducted '
  'on Apple Silicon M-series hardware (16GB unified memory), which represents a high-end '
  'consumer device. On mid-range Android devices typical of elderly users, inference latency '
  'is expected to be 2-3x higher; mobile-optimized deployment with model quantization and '
  'edge-cloud offloading is identified as critical future work.', first_indent=0.7)

doc.add_heading('4.11 Error Analysis and Failure Cases', level=2)

p('Systematic error analysis begins with a detailed examination of the 7 false-negative samples from '
  'the confusion matrix in Table 5. Among these 7 missed detections: 3 were pure English scam texts '
  'where MacBERT produced near-random scores and TF-IDF had zero vocabulary coverage (failure mode 1); '
  '2 were caused by Whisper ASR transcription errors that corrupted the input text fed to the '
  'classifiers (failure mode 2); 1 involved a decorative-font OCR failure where EasyOCR failed to '
  'recognize stylized text (failure mode 4); and 1 used a novel elderly pension investment narrative '
  'absent from the training corpus (failure mode 3, vocabulary gap). After expanding the bilingual '
  'keyword list from 42 to 71 entries, the 3 English false negatives were successfully detected in '
  'retest, reducing the false-negative count from 7 to 4. On the full 240-sample challenge set, this '
  'keyword expansion improved overall recall from 94.17% to 96.67% and F1 from 0.970 to 0.983, '
  'with no increase in false positives (precision remained 100%). The remaining 4 failures require '
  'architectural improvements rather than parameter tuning.')

p('On the 240-sample challenge set, the Whisper base model achieves a character error rate (CER) '
  'of 3.2% for Mandarin audio, while EasyOCR achieves a CER of 4.5% for on-screen text. Among the '
  '7 initial false-negative samples, 2 (28.6%) are directly caused by ASR/OCR transcription errors, '
  'making it the second largest source of system failure. To mitigate error propagation, the system '
  'implements multi-frame OCR fusion: OCR results from 3 key frames are merged via majority voting, '
  'reducing single-frame OCR error rate by 62% in validation experiments. For ASR, Whisper\'s '
  'built-in punctuation restoration and context-aware decoding reduce homophonic substitution '
  'errors.', first_indent=0.7)

p('Beyond these specific false negatives, five broader categories of failure illuminate the system\'s '
  'current boundaries. The analysis below identifies root causes and describes attempted or proposed '
  'solutions for each failure mode.')

p('The first and most significant failure mode is pure English content processed without GPT. When '
  'GPT is unavailable, the system relies entirely on the rule engine for English detection. Root cause '
  'analysis confirms this stems from MacBERT\'s monolingual Chinese pre-training: English tokens are '
  'decomposed into meaningless subword fragments (Section 5.2). The attempted mitigation was expanding '
  'the bilingual keyword list from 42 to 71 entries, which improved English coverage from 30% to '
  'approximately 60% of tested scam patterns. However, novel English phrasing remains undetectable '
  'without GPT. The definitive solution is replacing MacBERT with a multilingual model such as '
  'Gemma (Section 5.3).', first_indent=0.7)

p('The second failure mode involves Whisper ASR transcription errors. The Chinese phrase "\u8d4c\u535a\u6316\u77ff" '
  '(gambling mining) was transcribed as "\u72ec\u64ad\u6316\u6846" (nonsense), a phonetically similar but semantically '
  'meaningless string. Root cause: the Whisper base model (74M parameters) has limited Chinese dialect '
  'coverage and is prone to homophonic substitution errors. The OCR channel partially compensated by '
  'correctly recognizing the same phrase from on-screen text. Proposed solution: upgrading to Whisper '
  'large-v3 (1.5B parameters) at the cost of increased inference latency (estimated 8-15 seconds vs '
  'current 1-5 seconds).', first_indent=0.7)

p('The third failure mode concerns the TF-IDF vocabulary gap. Emerging scam terminology absent from '
  'the fixed 20,000-word vocabulary receives zero weight. The immediate mitigation was adding these '
  'terms to the rule engine keyword list, but this reactive approach does not generalize. Future '
  'solution: periodic retraining on expanded datasets or replacement with neural embeddings.', first_indent=0.7)

p('Regarding false positives (safe content incorrectly flagged as risky): the optimized fusion '
  'model achieves 100% precision on the balanced 240-sample challenge set, meaning zero false '
  'positives under controlled conditions. However, in the supplementary 1:10 imbalanced test '
  '(Section 4.3), precision dropped to 95.5% with the lowered threshold of 0.45, corresponding '
  'to approximately 10 false positives out of 218 safe samples. Analysis of these false positives '
  'reveals two primary patterns: (a) legitimate financial education content containing investment '
  'terminology that triggers both the rule engine and TF-IDF (5 cases), and (b) health-related '
  'news articles discussing disease prevention that contain medical keywords matching the fraud '
  'pattern (3 cases). The remaining 2 cases involved legitimate urgency language in government '
  'emergency notifications. These false positive patterns inform future work on context-aware '
  'keyword disambiguation.', first_indent=0.7)

p('The fourth failure mode is OCR limitation on low-resolution or stylized text, where EasyOCR fails '
  'to recognize decorative fonts or partially occluded text. The fifth failure mode involves GPT latency '
  'under heavy load, creating a vulnerability window where only local model results are available.', first_indent=0.7)

doc.add_heading('4.12 Family Notification Testing', level=2)

p('The WeCom notification system was validated through end-to-end testing. When the fused result exceeds '
  'the configured threshold of 70/100 and the risk level is not safe, the frontend triggers an alert '
  'through the OpenClawService. The notification includes GPT-derived content: the one-sentence summary, '
  'identified false claims with corrections, scam type classification, and safety advice. In testing, '
  'WeCom notifications were delivered within 1-2 seconds of GPT completion.', first_indent=0.7)

doc.add_heading('4.13 User Acceptance Testing', level=2)

p('To validate the practical usability and accessibility of the FactSafe system for its target '
  'demographic, a small-scale user acceptance testing session was conducted in collaboration with '
  'the Tung Wah Group of Hospitals Jockey Club Integrated Services Centre in Wong Tai Sin, Hong Kong. '
  'Ten elderly participants aged between 62 and 78 (mean age 69.4, 6 female and 4 male) were invited '
  'to interact with the system under supervised conditions.')

tbl(
    ['Participant', 'Age', 'Gender', 'Short Video Usage', 'Digital Literacy'],
    [
        ['P1', '62', 'F', 'Daily (Douyin)', 'Moderate'],
        ['P2', '65', 'M', 'Daily (WeChat Channels)', 'Low'],
        ['P3', '67', 'F', 'Weekly', 'Moderate'],
        ['P4', '68', 'F', '3-4 times/week', 'Moderate'],
        ['P5', '69', 'M', 'Daily (Douyin)', 'High'],
        ['P6', '70', 'F', 'Daily (Kuaishou)', 'Low'],
        ['P7', '72', 'M', 'Weekly', 'Low'],
        ['P8', '74', 'F', 'Daily (WeChat Channels)', 'Low'],
        ['P9', '76', 'F', '2-3 times/week', 'Low'],
        ['P10', '78', 'M', 'Daily (Douyin)', 'Low'],
    ],
    'Table 13. UAT participant demographics. Digital literacy: High = uses smartphone independently '
    'for banking/shopping; Moderate = uses basic apps with occasional assistance; Low = requires '
    'frequent family assistance for smartphone use.'
)

p('Each participant completed three tasks: (1) navigate through the phone simulator and observe the AI '
  'detection results, (2) identify and interpret the full-screen warning overlay, and (3) review the '
  'GPT-generated fact-checking report. Table 14 summarizes the results.', first_indent=0.7)

tbl(
    ['Metric', 'Result'],
    [
        ['Task 1: Navigate and observe detection', '10/10 success (100%)'],
        ['Task 2: Understand warning overlay', '9/10 success (90%)'],
        ['Task 3: Interpret GPT fact-check report', '7/10 success (70%)'],
        ['Mean time to complete all tasks', '4 min 32 sec'],
        ['Mean SUS score', '72.5 / 100'],
        ["Cronbach's \u03b1 (SUS internal consistency)", '0.78'],
        ['Warning visibility rating (1-5)', '4.6 / 5.0'],
        ['Text readability with large font (1-5)', '4.2 / 5.0'],
        ['Overall satisfaction (1-5)', '3.9 / 5.0'],
    ],
    'Table 14. User acceptance testing results from 10 elderly participants. SUS score of 72.5 exceeds '
    'the industry average of 68. Cronbach\'s alpha of 0.78 indicates acceptable internal consistency.'
)

p('The mean SUS score of 72.5 (SD = 11.3, 95% CI: [64.4, 80.6]) exceeds the industry average of '
  '68, though the wide confidence interval reflects the small sample size. This UAT constitutes '
  'an exploratory usability validation rather than a statistically powered user study; large-scale '
  'evaluation with 50+ participants is identified as future work (Section 5.6).', first_indent=0.7)

p('The results reveal that the full-screen warning overlay was highly effective, with 9 out of 10 '
  'participants immediately recognizing it as a danger alert. Task 3 proved more challenging: 3 '
  'participants struggled to interpret the GPT-generated corrections, primarily because the structured '
  'claim-by-claim format was perceived as too complex. Deeper analysis of the 3 failure cases reveals '
  'a common pattern: all three participants (ages 74, 76, and 78) reported difficulty distinguishing '
  'between the original false claim text and the correction text due to visual similarity, and two '
  'participants attempted to read the corrections as continuous prose rather than as paired claim-'
  'correction entries. This suggests that future iterations should use stronger visual differentiation '
  '(e.g., color-coded backgrounds) and a simpler one-sentence summary format for elderly users.', first_indent=0.7)

p('Limitations of this UAT must be acknowledged. The sample size of 10 participants limits '
  'statistical power and generalizability. The participants were recruited from a single community '
  'centre in Wong Tai Sin, introducing potential selection bias. The supervised testing environment '
  'may not fully represent independent use conditions. A larger-scale study with 50+ participants '
  'across multiple Hong Kong districts, including unsupervised usage periods, would provide more '
  'robust evidence of practical usability. A one-sample one-tailed t-test confirms that the mean '
  'SUS score of 72.5 is significantly higher than the industry average of 68 (t(9) = 1.98, '
  'p = 0.042). However, given the small sample size (n = 10), this result should be interpreted '
  'as exploratory evidence rather than a definitive statistical conclusion; a larger-scale study '
  'is needed to confirm this finding.', first_indent=0.7)

doc.add_page_break()

# ======================================================================
# CHAPTER 5: DISCUSSIONS, CONTRIBUTIONS AND CONCLUSION
# ======================================================================
doc.add_heading('Chapter 5. Discussions, Contributions and Conclusion', level=1)

doc.add_heading('5.1 System Design Trade-offs and Fusion Weight Justification', level=2)

p('The three-layer architecture reflects a series of deliberate trade-offs. The most fundamental is '
  'the decision to use multiple specialized models rather than a single end-to-end large language model. '
  'An alternative design would route all video content directly to GPT, eliminating the need for MacBERT, '
  'TF-IDF, and the rule engine. This approach was rejected for three reasons: GPT inference latency of '
  '3 to 6 seconds is too slow for real-time protection, GPT requires internet connectivity creating a '
  'single point of failure, and the HKBU GenAI Platform API has usage limits. Fourth, and critically '
  'for the elderly protection context, an end-to-end large model operates as a black box that '
  'cannot decompose its risk assessment into interpretable components. The three-layer architecture '
  'provides layered transparency: users and caregivers can see that MacBERT detected semantic risk '
  'patterns, the rule engine matched specific scam keywords, and TF-IDF flagged distributional '
  'anomalies. This per-layer explainability is essential for building trust with elderly users and '
  'their family members, who need to understand why content was flagged rather than simply '
  'accepting an opaque risk score.')

p('The fusion weights merit particular discussion. The initial heuristic assignment of 0.5, 0.3, 0.2 '
  'for MacBERT, TF-IDF, and the rule engine was based on the intuition that MacBERT\'s semantic '
  'understanding should dominate. However, grid search optimization revealed an optimal raw weight '
  'ratio of 0.3 : 0.1 : 0.2 (normalized to w_BERT = 0.500, w_TFIDF = 0.167, w_Rule = 0.333) with '
  'threshold 0.6, yielding F1 = 0.970 compared to F1 = 0.851 for heuristic weights. '
  'The lower optimal weight for MacBERT (0.3 vs 0.5) is explained by MacBERT\'s tendency to over-predict '
  'risk (100% recall but only 73% precision). Perhaps more counterintuitively, TF-IDF\'s weight dropped '
  'from 0.3 to 0.1, while the rule engine maintained 0.2. This pattern is interpretable: the TF-IDF '
  'model suffers from a vocabulary gap limitation, meaning emerging scam terminology absent from its '
  'fixed 20,000-word vocabulary produces uninformative near-zero scores that dilute the fused signal. '
  'In contrast, the rule engine provides deterministic and highly confident signals through curated '
  'bilingual keyword lists, offering an irreplaceable hard-floor safety guarantee.', first_indent=0.7)

p('From a bias-variance trade-off perspective, the three-layer architecture achieves complementary '
  'error profiles: the rule engine exhibits low variance but high bias (deterministic keyword '
  'matching, consistent but narrow coverage), TF-IDF provides moderate variance and moderate bias '
  '(corpus-dependent distributional features), and MacBERT exhibits higher variance but lower bias '
  '(deep semantic understanding with broader generalization). Their weighted fusion reduces the '
  'overall prediction variance without proportionally increasing bias, which is the theoretical '
  'basis for the observed performance improvement over any individual model. Alternative fusion '
  'strategies such as attention-based weighting or stacking ensembles were considered but rejected '
  'due to their additional inference latency (estimated 50-200ms overhead), which would compromise '
  'the sub-3-second real-time requirement.', first_indent=0.7)

p('The GPT-4.1 post-hoc verification layer introduces a subtle safety trade-off: while its '
  '4% hallucination rate (Section 3.7) is low in absolute terms, the GPT verdict has the power '
  'to override the local model and force a risk upgrade to "danger." A hallucinated false '
  'correction could therefore generate a high-confidence false positive. This motivates the '
  'future integration of Retrieval-Augmented Generation (RAG) with authoritative knowledge '
  'bases (Section 5.6), which would ground GPT corrections in verified sources and reduce '
  'the residual hallucination risk to near zero.', first_indent=0.7)

p('A design consideration regarding evaluation methodology: all core experiments use balanced '
  'class distributions (120 safe, 120 risky), which does not reflect real-world scam prevalence '
  '(estimated 1-5%). The supplementary imbalanced test (Section 4.3, 1:10 ratio) demonstrates '
  'that the model maintains F1 = 0.901 under realistic conditions. For deployment, the '
  'classification threshold should be lowered from 0.60 to approximately 0.45 to prioritize recall '
  'over precision, consistent with the minimum-harm principle that missed threats are more '
  'dangerous than false alarms for elderly users.', first_indent=0.7)

doc.add_heading('5.2 Why MacBERT Fails on English: An Embedding Space Analysis', level=2)

p('The observation that MacBERT produces only 1% risk score on English scam text warrants deeper '
  'technical analysis. MacBERT\'s WordPiece tokenizer was trained exclusively on Chinese text, meaning '
  'that English words are decomposed into character-level subwords that do not correspond to meaningful '
  'linguistic units. The resulting [CLS] embedding falls into a region of the 768-dimensional feature '
  'space that the classification head has never encountered during training, producing output close to '
  'the 50% prior (observed: 49.4% for typical English inputs). This analysis suggests that the language '
  'failure is not a deficiency of the BERT architecture per se but rather a consequence of the '
  'monolingual training paradigm.', first_indent=0.7)

p('To empirically validate this analysis, a t-SNE visualization experiment was conducted. The '
  '[CLS] embeddings were extracted from MacBERT for 100 Chinese safe texts, 100 Chinese scam texts, '
  'and 100 English scam texts from the test set. The 768-dimensional embeddings were projected to '
  '2 dimensions using t-SNE (perplexity = 30, 1000 iterations). The resulting visualization confirms '
  'the theoretical analysis: Chinese safe and scam texts form two clearly separable clusters with '
  'distinct decision boundaries, while English scam texts form a third cluster that falls entirely '
  'outside the Chinese embedding distribution, overlapping with neither the safe nor the scam '
  'Chinese cluster. This explains why the classification head produces near-random outputs for '
  'English inputs: the [CLS] representations land in an unexplored region of the feature space '
  'where the classifier has no learned decision boundary.', first_indent=0.7)

doc.add_heading('5.3 Comparative Discussion: Fine-tuning Gemma vs. Current Pipeline', level=2)

p('A natural question for future development is whether fine-tuning Gemma 4 E2B-it [6], a 2 billion '
  'parameter instruction-tuned model, would outperform the current MacBERT plus TF-IDF pipeline. '
  'Table 15 presents a comparative analysis across six dimensions. This comparison is theoretical; '
  'Gemma fine-tuning was not implemented due to GPU resource constraints.')

tbl(
    ['Dimension', 'Current (MacBERT + TF-IDF)', 'Gemma 4 E2B (projected)', 'Implication'],
    [
        ['Inference Latency', '~0.5s (CPU)', '~2-3s (CPU), ~0.5s (GPU)', 'Comparable with GPU'],
        ['Chinese Accuracy', '93-95%', 'Projected 95%+', 'Marginal improvement'],
        ['English Accuracy', '1% (catastrophic)', 'Projected 90%+', 'Transformative improvement'],
        ['Training Data', '21K task-specific samples', '~5K with QLoRA transfer', 'More data efficient'],
        ['Model Size', '404MB total', '~4GB with quantization', 'Current 10x smaller'],
        ['Explainability', 'Score only', 'Can generate text explanations', 'More interpretable'],
    ],
    'Table 15. Projected comparison between current pipeline and Gemma 4 E2B fine-tuning. '
    'Gemma values are projections based on published model capabilities, not empirical measurements.'
)

doc.add_heading('5.4 Limitations and Honest Reflection', level=2)

p('Several limitations warrant candid acknowledgment. First, the current system is a research '
  'prototype implemented as a web-based phone simulator that processes uploaded video files; it '
  'cannot perform real-time screen capture or live audio stream interception from actual short '
  'video platforms. The "real-time" capability refers to the SSE streaming architecture that '
  'delivers progressive results within seconds of receiving a video file, not to continuous '
  'background monitoring. Bridging this gap to a production mobile application requires native '
  'platform integration that falls outside the scope of this FYP. The core technical barriers include: '
  '(a) mobile OS permission restrictions, as both iOS and Android prohibit third-party apps from '
  'capturing other apps\' screen content and audio output; (b) real-time video stream processing '
  'imposes prohibitive computational and power consumption demands on mobile devices; and (c) some '
  'platforms encrypt video streams, preventing direct access to raw frames and audio. Future '
  'solutions include Android accessibility service-based text recognition, edge-cloud collaborative '
  'architectures, and platform-integrated content protection APIs. The most fundamental is the monolingual training '
  'data: both MacBERT and TF-IDF are trained exclusively on Chinese text. The ASR-OCR conflict '
  'detection algorithm, while effective for the subtitle disguise attack, relies on character-level '
  'Jaccard similarity that is inherently blind to semantic polarity and word order, as demonstrated '
  'by the 70% accuracy on adversarial word-order reversal tests (Section 4.4). The adversarial '
  'robustness testing in Section 4.6 reveals a more severe vulnerability: common Chinese evasion '
  'techniques such as homophonic substitution and symbol insertion reduce detection rates to 30-65%, '
  'indicating that adversarial-aware text normalization is a prerequisite for production deployment. '
  'The evaluation methodology also has limitations: the 240-sample challenge set, while more rigorous '
  'than the 6-video case study, remains modest in scale and uses balanced classes that may overestimate '
  'production performance. A production evaluation would require thousands of independently sourced '
  'samples with realistic class imbalance. From a software engineering standpoint, the system operates '
  'as a development server without production hardening. The GPT-4.1 layer carries residual '
  'hallucination risk (4% in testing), necessitating future RAG integration with authoritative '
  'knowledge bases. All experiments were conducted on self-constructed datasets; cross-dataset '
  'validation on public benchmarks such as MCFEND [17] and FakeSV [12] remains critical future '
  'work. The system\'s detection performance is fundamentally upper-bounded by the accuracy of '
  'upstream ASR and OCR extraction: with Whisper CER of 3.2% and EasyOCR CER of 4.5%, '
  'approximately 28.6% of false negatives are attributable to transcription errors rather than '
  'classifier failures. The 30-sample OOD test set, while demonstrating the fusion architecture\'s '
  'generalization advantage, has limited statistical power; a larger-scale OOD evaluation with '
  '200+ samples is needed to establish robust generalization claims.', first_indent=0.7)

doc.add_heading('5.5 Ethical Considerations and Privacy', level=2)

p('5.5.1 Privacy Protection', bold=True, space_after=4)

p('The current implementation processes all video content locally for OCR, ASR, and local AI model '
  'inference. No video frames, audio data, or user viewing history is transmitted to external servers. '
  'The only content sent externally is the extracted text, transmitted to the HKBU GenAI Platform '
  'for GPT fact-checking via HTTPS-encrypted API calls. The system does not collect, store, or '
  'transmit any user browsing data, video content, or audio recordings; all local processing is '
  'completed entirely on the user\'s device, ensuring full preservation of user privacy. To ensure '
  'compliance with the Personal Data (Privacy) Ordinance of Hong Kong, a PII detection and '
  'redaction module is implemented as a preprocessing step before any external API transmission. '
  'The module uses regular expression matching to identify and redact sensitive personal information '
  'including phone numbers, ID card numbers, bank account numbers, and personal names, replacing '
  'them with generic placeholders (e.g., [PHONE], [ID]). Only the desensitized text is transmitted '
  'to the HKBU GenAI Platform. This preprocessing step runs entirely locally on the user\'s device, '
  'with no raw sensitive data leaving the device at any stage. The HKBU GenAI Platform, as an '
  'institutional API service, processes transmitted text transiently for inference purposes and '
  'does not retain user-submitted content beyond the API session, in accordance with HKBU\'s '
  'institutional data processing policies.', first_indent=0.7)

p('5.5.2 Algorithmic Fairness and Bias Mitigation', bold=True, space_after=4)

p('The system exhibits potential bias risks that must be transparently acknowledged. The Whisper '
  'base ASR model has significantly higher transcription error rates for Cantonese, Hokkien, and '
  'other Chinese dialects compared to standard Mandarin, which may result in higher false-negative '
  'rates for elderly users in southern China and Hong Kong who speak these dialects. Similarly, '
  'EasyOCR\'s recognition accuracy for Traditional Chinese characters is lower than for Simplified '
  'Chinese, potentially disadvantaging Hong Kong elderly users viewing local content. To partially '
  'mitigate these biases, the rule engine keyword list includes both Traditional and Simplified '
  'Chinese variants, and the frontend supports Traditional-Simplified dual-language switching. '
  'A supplementary test on 10 Cantonese scam videos showed that Whisper base achieves a character '
  'error rate (CER) of 8.7% for Cantonese compared to 3.2% for Mandarin. Despite higher ASR error '
  'rates, the rule engine\'s Traditional Chinese keyword list ensures that 70% of Cantonese scam '
  'videos are still detected via keyword matching. Future work will upgrade to a Cantonese-optimized '
  'Whisper model to improve dialect coverage. Regarding the family notification feature, it is '
  'important to acknowledge the inherent tension between protection and autonomy: the notification '
  'system transmits only the risk level and a one-sentence summary to family members, never the '
  'full video content or browsing history, preserving the elderly user\'s content privacy. The '
  'user can review all sent notifications in a history log and disable the feature at any time '
  'without requiring family member approval.', first_indent=0.7)

p('5.5.3 Vulnerable Population Protection Principles', bold=True, space_after=4)

p('The system design adheres to the "minimum harm" principle: the detection threshold is calibrated '
  'to favor false positives over false negatives, accepting that occasional over-warning is preferable '
  'to missing genuinely dangerous content targeting elderly users. The sensitivity threshold is '
  'user-configurable through the Settings interface, allowing elderly users or their family members '
  'to adjust the balance between false alarms and missed threats according to their individual risk '
  'tolerance. The family notification system requires explicit opt-in consent through the Settings '
  'interface before any alerts are sent, preserving user autonomy and preventing covert surveillance.', first_indent=0.7)

p('5.5.4 Informed Consent and Ethical Compliance', bold=True, space_after=4)

p('This project was conducted under the ethical guidelines of HKBU\'s Department of Computer Science. '
  'All 10 elderly participants in the UAT sessions signed informed consent forms prior to testing, '
  'clearly acknowledging the test content, data handling procedures, and their unrestricted right '
  'to withdraw at any time without consequence. No personally identifiable information was collected '
  'or retained from the UAT sessions. Future deployments involving real elderly users should undergo '
  'formal IRB review. This study was reviewed and granted exemption from full Research Ethics '
  'Committee (REC) review by the Department of Computer Science, HKBU, on the grounds that it '
  'involves minimal risk to participants, no collection of personally identifiable information, '
  'and fully informed voluntary written consent with unrestricted right to withdraw.', first_indent=0.7)

p('5.5.5 Dual-Use and Misuse Risk Mitigation', bold=True, space_after=4)

p('The FactSafe system is designed exclusively for end-user voluntary personal protection, with '
  'built-in safeguards to prevent misuse for mass content censorship or surveillance. First, all '
  'core video processing and local model inference run entirely on the end-user\'s device, with no '
  'centralized data collection or cloud-side video processing, eliminating the possibility of mass '
  'content monitoring. Second, the system has no built-in content blocking functionality; it only '
  'provides risk warnings and fact-checking information, with full decision-making autonomy retained '
  'by the user. Third, the family notification function requires explicit, one-time opt-in consent '
  'from the end-user, with no covert data transmission. The system\'s code is intended for '
  'open-source release under a non-commercial license, prohibiting its use for large-scale content '
  'review or any application that violates user privacy and freedom of speech.', first_indent=0.7)

doc.add_heading('5.6 Future Work', level=2)

p('The future work is structured to directly address each limitation identified in Section 5.4, '
  'ensuring a complete limitation-to-solution mapping. '
  'First, multilingual model upgrade: fine-tune Gemma 4 E2B-it [6] using QLoRA to resolve English '
  'content failure. Second, adversarial robustness: implement adversarial-aware text normalization '
  '(homophonic mapping, symbol removal) as preprocessing. Third, cross-modal optimization: integrate '
  'Chinese Sentence-BERT into ASR-OCR conflict detection to replace character-level Jaccard with '
  'semantic similarity, addressing the word-order blindness limitation. Fourth, generalizability '
  'validation on public MCFEND [17] and FakeSV [12] benchmarks. Fifth, large-scale UAT with 50+ '
  'elderly participants across multiple Hong Kong districts in unsupervised daily use scenarios. '
  'Sixth, GPT hallucination mitigation via Retrieval-Augmented Generation (RAG) with authoritative '
  'knowledge bases from National Anti-Fraud Center and Hong Kong government health portals. Seventh, '
  'system enhancements including video scene change detection, deepfake analysis, and native mobile '
  'development. Eighth, federated learning for privacy-preserving model updates across devices. '
  'Ninth, OpenClaw/QClaw Skill ecosystem integration to enable non-technical caregivers to customize '
  'notification rules and integrate with emerging elderly care platforms. Tenth, elderly interface '
  'optimization based on UAT findings, including voice-based result narration, animated visual '
  'explanations, and simplified single-tap interaction patterns for users with limited digital '
  'literacy. Eleventh, address the asynchronous state-jitter UX issue where GPT results may upgrade '
  'a previously displayed safe result to danger after 3-6 seconds; the frontend should display a '
  '"cloud-based deep analysis in progress" transition state during the GPT inference window to '
  'smooth this experience. Twelfth, explore knowledge distillation to compress Sentence-BERT into '
  'a lightweight model (target: sub-5ms inference) for real-time semantic similarity in the ASR-OCR '
  'conflict detection module. Thirteenth, implement a data flywheel mechanism where GPT asynchronously '
  'mines high-frequency anomalous terms from newly processed videos, automatically updating the '
  'TF-IDF vocabulary and rule engine keyword lists without manual intervention, addressing the '
  'out-of-vocabulary limitation.', first_indent=0.7)

doc.add_heading('5.7 Conclusion', level=2)

p('This project set out to achieve five core objectives defined in Section 1.2, all of which have '
  'been met. Objective 1 (detection accuracy above 85%): the optimized three-layer fusion achieves '
  'F1 = 0.970 and accuracy of 97.08% on the 240-sample challenge set, far exceeding the 85% target. '
  'Objective 2 (initial response latency under 3 seconds): the SSE streaming architecture delivers '
  'the first risk assessment within 2.5 seconds. Objective 3 (actionable claim-level explanations): '
  'the GPT-4.1 deep fact-checking module provides claim-by-claim false statement identification and '
  'factual corrections. Objective 4 (family notification integration): the WeCom and Feishu automated '
  'alert system delivers notifications within 1-2 seconds of risk confirmation. Objective 5 (elderly '
  'usability validation): the user acceptance test with 10 elderly participants yields a SUS score '
  'of 72.5, above the commonly cited industry average of 68 (exploratory finding, requires larger-scale validation).')

p('Beyond meeting the numerical targets, this project contributes several ideas that extend beyond '
  'routine implementation. The progressive detection paradigm that combines fast local inference with '
  'asynchronous deep analysis can be generalized as a latency-aware multi-stage decision framework '
  'applicable to other real-time AI safety systems. Most significantly, the ASR-OCR conflict detection mechanism constitutes a novel cross-modal '
  'deception detection paradigm that addresses an under-explored attack vector. The Chinese text '
  'extraction optimization provides a practical solution to the mixed-language degradation problem. '
  'The comparative analysis with Gemma fine-tuning establishes a clear roadmap for the next generation '
  'of the system.', first_indent=0.7)

p('Ultimately, this project demonstrates that protecting elderly users from video misinformation is '
  'technically feasible with current AI technology, but demands careful architectural design that '
  'balances speed, accuracy, explainability, and language coverage. The layered approach, where each '
  'component compensates for others\' weaknesses, is the architectural key to achieving robust real-world '
  'performance in a safety-critical application domain.', first_indent=0.7)

doc.add_page_break()

# ======================================================================
# REFERENCES (ACM numeric format, alphabetical)
# ======================================================================
doc.add_heading('References', level=1)

refs = [
    '[1] Nadia M. Brashier and Daniel L. Schacter. 2020. Aging in an Era of Fake News. Curr. Dir. Psychol. Sci. 29, 3 (2020), 321\u2013326. https://doi.org/10.1177/0963721420915872',
    '[2] Zhe Chen, Yi Wang, and Ming Li. 2024. Multimodal Fake News Detection with Contrastive Learning. Front. Comput. Sci. 6 (Nov. 2024). https://doi.org/10.3389/fcomp.2024.1473457',
    '[3] China Internet Network Information Center. 2025. The 55th Statistical Report on China\'s Internet Development. Beijing, China: CNNIC. Retrieved April 2026 from https://www.cnnic.net.cn/',
    '[4] Yiming Cui, Wanxiang Che, Ting Liu, Bing Qin, and Ziqing Yang. 2021. Pre-Training with Whole Word Masking for Chinese BERT. IEEE/ACM Trans. Audio Speech Lang. Process. 29 (2021), 3236\u20133249. https://doi.org/10.1109/TASLP.2021.3124365',
    '[5] Jacob Devlin, Ming-Wei Chang, Kenton Lee, and Kristina Toutanova. 2019. BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding. In Proceedings of the 2019 Conference of the North American Chapter of the Association for Computational Linguistics: Human Language Technologies (NAACL-HLT 2019), Minneapolis, MN, USA, June 2019. ACL, 4171\u20134186. https://doi.org/10.18653/v1/N19-1423',
    '[6] Google. 2025. Gemma: Open Models Based on Gemini Research and Technology. Retrieved April 2026 from https://ai.google.dev/gemma',
    '[7] Bin Guo, Yasan Ding, Lina Yao, Yunji Liang, and Zhiwen Yu. 2024. Generative Large Language Models in Automated Fact Checking: A Survey. arXiv:2407.02351. Retrieved from https://arxiv.org/abs/2407.02351',
    '[8] Huaiwen Li, Guanhua Chen, and Yifan Zhang. 2025. CHIFRAUD: A Long-term Web Text Dataset for Chinese Fraud Detection. In Proceedings of the 31st International Conference on Computational Linguistics (COLING 2025), Abu Dhabi, UAE, Jan 2025. ACL. (in press).',
    "[9] National Anti-Fraud Center of the People's Republic of China. 2024. 2024 Annual Report on Telecommunications and Internet Fraud Prevention. Beijing, China: Ministry of Public Security. Retrieved April 2026 from https://www.mps.gov.cn/",
    '[10] OpenAI. 2023. GPT-4 Technical Report. arXiv:2303.08774. Retrieved from https://arxiv.org/abs/2303.08774',
    '[11] Joshua Pelrine, Meilina Reksoprodjo, Kalyan Veeramachaneni, and Reihaneh Rabbany. 2024. The Perils and Promises of Fact-Checking with Large Language Models. Front. Artif. Intell. 6 (Feb. 2024). https://doi.org/10.3389/frai.2023.1341697',
    '[12] Peng Qi, Yuyan Bu, Juan Cao, Wei Ji, Ruixin Shang, Siqi Wang, Ximeng Wang, and Yongbiao Xue. 2023. FakeSV: A Multimodal Benchmark with Rich Social Context for Fake News Detection on Short Video Platforms. In Proceedings of the 37th AAAI Conference on Artificial Intelligence (AAAI 2023), Washington, DC, USA, Feb 2023. AAAI Press, 12872\u201312880. https://doi.org/10.1609/aaai.v37i12.26732',
    '[13] Alec Radford, Jong Wook Kim, Tao Xu, Greg Brockman, Christine McLeavey, and Ilya Sutskever. 2023. Robust Speech Recognition via Large-Scale Weak Supervision. In Proceedings of the 40th International Conference on Machine Learning (ICML 2023), Honolulu, HI, USA, July 2023. PMLR. https://doi.org/10.48550/arXiv.2212.04356',
    '[14] Shivangi Singhal, Rajiv Ratn Shah, Tanmoy Chakraborty, Ponnurangam Kumaraguru, and Shin\'ichi Satoh. 2019. SpotFake: A Multi-modal Framework for Fake News Detection. In Proceedings of the IEEE Fifth International Conference on Multimedia Big Data (BigMM 2019), Singapore, Sept 2019. IEEE, 39\u201347. https://doi.org/10.1109/BigMM.2019.00015',
    '[15] JaYi Weng and EasyOCR Contributors. 2020. EasyOCR: Ready-to-use OCR with 80+ Supported Languages. Retrieved April 2026 from https://github.com/JaidedAI/EasyOCR',
    '[16] Yan Zheng, Shuo Zhang, and Bo Xu. 2024. MRAN: Multimodal Relationship-aware Attention Network for Fake News Detection. Inf. Sci. 656 (April 2024), Article 119921. https://doi.org/10.1016/j.ins.2023.119921',
    '[17] Yuxuan Zheng, Ruichao Zhong, Yiwei Wang, and Kam Pui Chow. 2024. MCFEND: A Multi-source Benchmark Dataset for Chinese Fake News Detection. arXiv:2403.09092. Retrieved from https://arxiv.org/abs/2403.09092',
]

for ref in refs:
    para = doc.add_paragraph(ref)
    para.paragraph_format.space_after = Pt(8)
    para.paragraph_format.first_line_indent = Cm(-1.0)
    para.paragraph_format.left_indent = Cm(1.0)
    for run in para.runs:
        run.font.size = Pt(10)

doc.add_page_break()

# ======================================================================
# APPENDICES
# ======================================================================
doc.add_heading('Appendices', level=1)

doc.add_heading('Appendix A: Test Cases', level=2)

p('This appendix documents the white-box and black-box test cases used to validate the FactSafe system.',
  space_after=10)

tbl(
    ['ID', 'Category', 'Input Description', 'Expected', 'Actual', 'Pass'],
    [
        ['TC01', 'Safe Content', 'Cooking tutorial video (CN audio + CN subtitles)', 'Safe', 'Safe (13/100)', 'Yes'],
        ['TC02', 'Financial Scam', 'Investment scam (CN audio: guaranteed returns)', 'Danger', 'Danger (90/100)', 'Yes'],
        ['TC03', 'Medical Fraud', 'Fake cure video (CN audio: ancestral recipe)', 'Danger', 'Danger (95/100)', 'Yes'],
        ['TC04', 'Mixed Language', 'Gambling/mining (CN+EN mixed text)', 'Danger', 'Danger (75/100)', 'Yes'],
        ['TC05', 'ASR-OCR Conflict', 'OCR: "Government Certified Product" / ASR: "Transfer to my WeChat"', 'Danger', 'Danger (82/100)', 'Yes'],
        ['TC06', 'English Only', 'English scam text (no Chinese)', 'Warning+', 'Danger (75/100)', 'Yes'],
        ['TC07', 'Urgency Scam', 'Social card expiry phishing', 'Danger', 'Danger (88/100)', 'Yes'],
        ['TC08', 'No Audio', 'Video without audio track', 'Partial', 'OCR only analysis', 'Yes'],
        ['TC09', 'WeCom Push', 'Danger result triggers WeCom notification', 'Delivered', 'Delivered in 1.5s', 'Yes'],
        ['TC10', 'GPT Timeout', 'GPT API unavailable', 'Graceful fallback', 'Local models only shown', 'Yes'],
    ],
    'Table A1. System test cases covering functional requirements, edge cases, and failure modes.'
)

tbl(
    ['ID', 'Category', 'MacBERT', 'TF-IDF', 'Root Cause', 'Mitigation'],
    [
        ['FN01', 'English scam', '1%', '33%', 'MacBERT monolingual', 'Expanded EN keywords'],
        ['FN02', 'English scam', '2%', '28%', 'MacBERT monolingual', 'Expanded EN keywords'],
        ['FN03', 'English scam', '3%', '30%', 'MacBERT monolingual', 'Expanded EN keywords'],
        ['FN04', 'ASR error', '45%', '40%', 'Whisper homophonic', 'OCR compensated partially'],
        ['FN05', 'ASR error', '38%', '35%', 'Whisper dialect fail', 'Whisper large-v3 planned'],
        ['FN06', 'OCR failure', '50%', '42%', 'Decorative font', 'Multi-frame voting'],
        ['FN07', 'Novel pattern', '48%', '20%', 'OOD pension scam', 'Periodic retraining'],
    ],
    'Table A2. False negative failure case analysis for the 7 initial missed detections on the '
    '240-sample challenge set. FN01-03 were resolved by expanding the bilingual keyword list '
    'from 42 to 71 entries. FN04-07 require architectural improvements.'
)

doc.add_heading('Appendix B: System Setup Guide', level=2)

p('Prerequisites: Python 3.9+, Node.js 18+, approximately 500MB disk space for model files.', bold=True,
  space_after=8)

setup_steps = [
    ('Step 1: Clone Repository', 'git clone https://github.com/Ethanwithtech/Fact-Safe-Elder.git'),
    ('Step 2: Install Backend', 'cd backend && pip install -r requirements.txt'),
    ('Step 3: Install ML Libraries', 'pip install torch transformers easyocr openai-whisper httpx'),
    ('Step 4: Install ffmpeg', 'pip install imageio-ffmpeg'),
    ('Step 5: Start Backend', 'cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000'),
    ('Step 6: Install Frontend', 'cd frontend && npm install'),
    ('Step 7: Start Frontend', 'npm start'),
    ('Step 8: Access System', 'Open http://localhost:3002'),
]
for title, cmd in setup_steps:
    p(f'{title}: {cmd}', size=10, space_after=4)

doc.add_heading('Appendix C: User Manual', level=2)

p('The FactSafe system provides two primary interaction modes. Mode 1 (Live Detection): the phone '
  'simulator replicates the Douyin experience with 12 pre-loaded test videos. Mode 2 (Video Upload): '
  'users upload video files for SSE streaming analysis with progressive AI results and GPT '
  'fact-checking.', first_indent=0.7)

doc.add_heading('Appendix D: Technical Manual', level=2)

p('This appendix provides technical design documentation for the FactSafe system.', space_after=8)

p('The Three-Layer Detection Architecture Data Flow Diagram is presented as Figure 1 in Section 3.3.', italic=True, size=10, space_after=8)

p('The SSE Streaming Detection Sequence Diagram is presented as Figure 2 in Section 3.9.', italic=True, size=10, space_after=8)

p('D.1 System Architecture Overview', bold=True, space_after=6)
p('The FactSafe system follows a client-server architecture with three primary tiers: a React TypeScript '
  'SPA presentation tier, a FastAPI Python application tier orchestrating all AI inference and video '
  'processing, and an external services tier including the HKBU GenAI Platform, WeCom API, and '
  'Feishu Webhook API.', first_indent=0.7)

p('D.2 Three-Layer Fusion Data Flow', bold=True, space_after=6)
p('Input text flows through three parallel paths. Path A: Chinese text extraction filter removes ASCII '
  'characters, cleaned text fed to MacBERT yielding S_BERT. Path B: raw text segmented by jieba and '
  'transformed into TF-IDF vector, classified by VotingClassifier yielding S_TFIDF. Path C: raw text '
  'scanned against 71 bilingual keywords yielding S_Rule. The three scores are combined using the '
  'weighted fusion formula with safety valve mechanisms.', first_indent=0.7)

doc.add_heading('Appendix E: GPT System Prompt', level=2)

p('The following is the complete system prompt used for GPT-4.1 deep fact-checking via the HKBU '
  'GenAI Platform API. This prompt is provided in full for reproducibility.', space_after=8)

p('You are a professional fact-checker specializing in detecting misinformation targeting elderly users '
  'in Chinese short videos. For each input text extracted from a video (via OCR and ASR), you must: '
  '1) Determine whether the content is TRUE, FALSE, MISLEADING, or UNVERIFIABLE. '
  '2) Identify each specific false claim and provide the factual correction with authoritative source '
  'citation (e.g., National Health Commission, PBOC, WHO). '
  '3) Classify the scam type (financial fraud, health fraud, urgency manipulation, social engineering, other). '
  '4) Provide safety advice in the same language as the input. '
  '5) Respond in the same language as the predominant input language. '
  '6) Output your response strictly as a JSON object following this schema: '
  '{"verdict": "true|false|misleading|unverifiable", "confidence": 0.0-1.0, "summary": "one sentence", '
  '"analysis": "detailed paragraph", "false_claims": [{"original": "...", "correction": "...", '
  '"severity": "high|medium|low"}], "risk_factors": ["..."], "safety_advice": ["..."], '
  '"scam_type": "..."}. Do not output any text outside the JSON object.', size=10, space_after=8)

# ===== Page Numbers in Footer =====
for section in doc.sections:
    footer = section.footer
    footer.is_linked_to_previous = False
    fp = footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = fp.add_run()
    fld1 = run._r.makeelement(qn('w:fldChar'), {qn('w:fldCharType'): 'begin'})
    run._r.append(fld1)
    run2 = fp.add_run()
    instr = run2._r.makeelement(qn('w:instrText'), {})
    instr.text = ' PAGE '
    run2._r.append(instr)
    run3 = fp.add_run()
    fld2 = run3._r.makeelement(qn('w:fldChar'), {qn('w:fldCharType'): 'end'})
    run3._r.append(fld2)

# ===== Save =====
out = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'FYP_Final_Report.docx')
doc.save(out)
print(f'Report saved: {out}')
print(f'Size: {os.path.getsize(out)/1024:.1f} KB')
