# ExpEvaFCHD

**胎儿先天性心脏病风险专家评估框架**

ExpEvaFCHD 将结构化胎儿超声心动图测量与专家病例证据结合，用于筛查支持和报告生成。框架包括确定性字段对齐、相似病例检索、极性受控证据聚合，以及与证据一致的约束生成；基础语言模型参数保持不变。方法来源见[手稿第 30–32 页](references/ExpEvaFCHD_Manuscript.pdf#page=30)。

**本仓库公开版本以伪代码和示例为主，用于展示研究思路、模块关系和数据接口。详细、完整的实现需联系通讯作者获取。** 示例查看器仅展示预先编写的合成 JSON，不执行诊断推理，也不复现论文实验结果。公开范围见 [CODE_AVAILABILITY.md](CODE_AVAILABILITY.md)。

[English README](README.md)

## 对应手稿

**A Large Language Model Paradigm Integrating Expert Diagnostic Data for Fetal Congenital Heart Disease Screening and Prenatal Diagnosis in Low-Resourced Healthcare Settings**

作者：Yingying Zhang、Runze Liu、Yuxuan Guan、Hao Sheng、Jingyi Wang、Xiaoyan Gu、Jiancheng Han、Xuefei Huang、Jia Gu、Yihua He、Haogang Zhu。

本次更新依据随附的[手稿](references/ExpEvaFCHD_Manuscript.pdf)和[补充材料](references/ExpEvaFCHD_Supplementary.pdf)。[CITATION.cff](CITATION.cff) 提供引用信息，未补写未提供的 DOI 或发表状态。

## 仓库内容

| 文件或目录 | 内容 |
|---|---|
| [ExpEvaFCHD_main.py](ExpEvaFCHD_main.py) | 以抽象操作接口组织的推理流程伪代码 |
| [ExpEvaFCHD_eval.py](ExpEvaFCHD_eval.py) | 区分病例、疾病家族、异常陈述和工作流事件的评估伪代码 |
| [configs](configs) | 队列信息、六种模型、实验条件与示例设置 |
| [schemas](schemas) | 公开数据契约与疾病家族定义 |
| [examples](examples) | 人工编写的合成输入、证据、输出与 JSON 查看器 |
| [Structured_Data_Standard_Template.xlsx](templates/Structured_Data_Standard_Template.xlsx) | 结构化数据模板和字段说明 |
| [docs/methods.md](docs/methods.md) | 方法、公式、分支处理和抽象依赖 |
| [docs/data_contract.md](docs/data_contract.md) | 数据、缺失值、标签和输出约定 |
| [docs/evaluation.md](docs/evaluation.md) | 评估指标、统计分析和实验条件 |
| [docs/manuscript_alignment.md](docs/manuscript_alignment.md) | 手稿内容与仓库模块的对应关系 |
| [references](references) | 本次手稿、补充材料和原仓库的 2026 年 1 月疾病分类参考 |

解释性内容集中在文档中，Python 源文件不包含代码注释或文档字符串。

## 查看示例

在仓库目录中使用 Python 3 执行：

```bash
python examples/show_example.py
python examples/show_example.py --case multifamily --section output
python examples/show_example.py --case insufficient --section trace
```

查看器仅使用 Python 标准库，无需安装第三方依赖、下载模型或配置 API。示例中的病例、输出和流程记录均为演示内容，不能视为患者数据或论文实测结果。

两个主文件保留 Python 风格的流程表达。具体临床操作通过外部 `ops` 接口提供，公开包不实现这些操作；直接运行文件会显示用途说明：

```bash
python ExpEvaFCHD_main.py
python ExpEvaFCHD_eval.py
```

原有两个 requirements 文件保留为空文件，与本版本无需第三方依赖的性质一致。

## 与手稿一致的关键内容

方法流程为“结构化对齐 → 数值空间相似病例检索 → 极性受控证据聚合 → 约束生成与证据验证”。手稿给出的检索默认值为 top-10 和最低相似度 0.22。阈值筛选后没有病例时，可退回最高相似度病例，但该低相似度匹配本身不构成异常证据充分性的证明。没有可用数值测量时，输出证据不足状态。具体公式与尚未公开的研究参数见[方法文档](docs/methods.md)。

| 队列 | 独立病例数 | 阳性病例 | 阴性病例 |
|---|---:|---:|---:|
| FetalCardioDB | 50,093 | 7,632 | 42,461 |
| 前瞻性单中心验证 | 1,458 | 340 | 1,118 |
| 多中心验证 | 3,370 | 316 | 3,054 |

以上为手稿队列统计，不代表公开包包含对应患者数据。FetalCardioDB 阳性数由总病例数减阴性数得到。历史数据库覆盖 2016 年 1 月至 2025 年 11 月；两个验证队列均覆盖 2025 年 12 月 1 日至 2026 年 3 月 1 日。多中心队列覆盖中国五省 15 家医院。来源：[手稿第 3–5 页](references/ExpEvaFCHD_Manuscript.pdf#page=3)、[第 29–30 页](references/ExpEvaFCHD_Manuscript.pdf#page=29)。

七个疾病家族覆盖 73 个具体疾病实体。同一阳性病例可属于多个家族，家族计数之和不能作为去重后的阳性病例数。论文的集合预测评价在七个疾病家族层面开展，不能改写为 73 个具体疾病实体均已完成独立验证。病例级筛查、家族集合预测和异常陈述证据支持分别使用各自的统计单位。

模型目录包含 Kimi-K2、DeepSeek-V3.2、GLM-4.5、Llama-3.1-70B、Qwen3-Max 和 GPT-5。补充表 S17 仅给出接入方式和平台来源，未给出精确权重版本、量化配置、解码参数和 API 修订号，因此对应字段保持未指定。来源：[补充表 S17](references/ExpEvaFCHD_Supplementary.pdf#page=42)。

相同证据下的模板报告与完整 Qwen3-Max 系统在两个队列中具有相同的二分类混淆矩阵，但报告质量评分不同；该结论不等于六种模型的预测结果相同。来源：[手稿第 12–14 页](references/ExpEvaFCHD_Manuscript.pdf#page=12)、[补充表 S6](references/ExpEvaFCHD_Supplementary.pdf#page=20) 和 [S16](references/ExpEvaFCHD_Supplementary.pdf#page=41)。

## 完整实现与数据获取

详细、完整的代码实现可在合理请求后向通讯作者获取：

| 通讯作者 | 邮箱 |
|---|---|
| Yihua He | [heyihuaecho@hotmail.com](mailto:heyihuaecho@hotmail.com) |
| Haogang Zhu | [haogangzhu@buaa.edu.cn](mailto:haogangzhu@buaa.edu.cn) |

临床数据的获取遵循相关法规、伦理要求及必要审批。本公开包不包含患者记录、完整专家病例库、生产级提示词、临床规则、拟合后的校准对象、模型访问凭据或病例级实验输出。研究流程中的最终诊断由医师作出。

原仓库 [MIT 许可证](LICENSE) 保持不变，不授予对未公开临床数据、外部模型资产或完整实现的访问权限。本次仓库更新日期为 **2026-11-03**，不代表论文发表日期。更新记录见 [CHANGELOG.md](CHANGELOG.md)。
