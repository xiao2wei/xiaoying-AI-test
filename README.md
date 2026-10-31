# 小影 AI 笔试第三题：企业知识问答 Agent

面向教职工的人事制度问答 CLI。使用用户指定的唯一 PDF，通过中文混合检索与真实 DeepSeek 决策，输出回答、文档 ID、原文引用、资料缺口和任务状态。

**评审入口：[交付与验收对照表](docs/SUBMISSION.md) → [最后一轮结果与真实一问一答](docs/LATEST-TEST-RESULTS.md) → [未通过案例说明](docs/FAILED-CASES.md)。**

本轮正式 **Agent任务通过率90%**，**基础RAG任务通过率85%**，**关键场景稳定性通过率90%**；138轮问答均有有效 AI 评分。用户接受当前指标，并确认51组、56轮正式复核清单。原定20项数值门槛中14项达标，失败和差距完整保留，不宣称全部用例或所有质量门槛通过。

## 安装与无需密钥的检查

推荐 Windows x64、Python 3.13（本次实际版本3.13.13）。代码声明Python 3.11+；其他平台未完成同等复现。需在仓库内使用可编辑安装，资料和提示词从仓库读取。首次安装需要联网下载依赖；首次真实检索需要下载嵌入模型。

~~~powershell
git clone https://github.com/xiao2wei/xiaoying-AI-test.git
cd xiaoying-AI-test
python -m venv .venv
.venv\Scripts\python -m pip install -c constraints-tested.txt -r requirements.txt
.venv\Scripts\python -m pip check
.venv\Scripts\python scripts/demo_offline.py --out work/local-offline-demo
# 完整程序测试含真实检索集成测试，须先下载嵌入模型并构建索引（不调用DeepSeek）
.venv\Scripts\python -m policy_agent.cli build-index
.venv\Scripts\python scripts/run_tests.py work/local-program-tests.json
~~~

demo_offline.py是明确标注的 **OFFLINE MOCK**：预设模型动作和检索候选，实际执行读取、引用校验与调用上限；不调用API，不下载嵌入模型，不用于证明真实模型效果。无密钥或模型服务不可用时可运行此入口。真实模式不会静默降级为Mock。

## 真实 DeepSeek 问答

~~~powershell
# 首次配置；已有.env请保留。把自己的Key填入.env，切勿提交。
Copy-Item .env.example .env
# data/processed已随仓库提供；从唯一PDF重建可另运行 scripts/prepare_corpus.py
.venv\Scripts\python -m policy_agent.cli build-index
.venv\Scripts\python -m policy_agent.cli ask "人才科研建设专项经费项目最长执行多久？" --mode agent --output work/answer.json
# 基础RAG对照：同一问题增加 --mode baseline
# 多轮会话：前一轮问答由程序传入下一轮，整组共享执行预算
.venv\Scripts\python -m policy_agent.cli batch --dataset examples/inputs/conversation.json --mode agent --out work/conversation
~~~

输出包含status、answer、claims（含doc_id、chunk_id、quote、版本日期和双页码）与gaps。记录文件还含工具参数、观察、下一步动作及简要依据；不保存模型内部推理正文。默认整组最多12轮决策、10次工具尝试；达到上限返回limit_reached及未完成原因。

当前默认回答模型deepseek-flash，独立评分模型deepseek-v4-pro；可在.env配置。模型调用会产生费用。动作通常关闭thinking，最终核对开启thinking且计入预算。模型别名和服务能力可能变化，实测请求/响应模型均保留在Trace。

## 复核已有结果，不产生 API 费用

~~~powershell
.venv\Scripts\python -m policy_agent.metrics --dataset evaluation/formal.json --runs examples/step08/v4/agent-runs --scores examples/step08/v4/human-reviewed-r1/agent-scores --program examples/step07/program-tests-v17.json --stability examples/step08/v4/human-reviewed-r1/stability-observations.json --out work/recomputed-metrics
.venv\Scripts\python scripts/check_submission.py --out work/submission-check.json
~~~

metrics命令只复算数值；人工确认状态和用户接受差距的决定见[正式复核记录](examples/step08/v4/human-reviewed-r1/completion.json)，不由统计程序自动推断。

如确需新增真实批量实验，可运行以下命令；它们会消耗API，不是查看既有结果的必需步骤。使用全新目录以保留历史：

~~~powershell
.venv\Scripts\python -m policy_agent.cli batch --dataset evaluation/dev.json --mode agent --out work/new-agent
.venv\Scripts\python -m policy_agent.evaluation score --dataset evaluation/dev.json --runs work/new-agent --out work/new-scores
~~~

## 数据、结构与技术取舍

- data/source/personnel-policies.pdf：唯一原始资料，229页。29份制度、562个片段、61张表格保留出处。使用真实制度汇编而非合成制度；合成的是测试问题与工具故障。某制度发布日期未知时保留null，不臆造日期。
- src/policy_agent/：原生Python Agent、模型接入、检索/读取、引用校验、独立评测。无Agent框架；框架名称不替代决策证据。
- tests/：确定性程序测试；不计入模型答题正确率。
- evaluation/：12组开发题、40组正式题、校准标签及人工确认。参考答案不进入检索索引或回答提示。
- examples/：真实输入、实际输出、Trace、评分、失败历史与交付复现记录。
- docs/01-requirements.md、02-solution.md、03-evaluation.md、04-ai-usage.md、05-retrospective.md：需求、方案、评估、AI使用与复盘；docs/steps/逐步记录。

检索使用BM25中文二元词与BAAI/bge-small-zh-v1.5本地向量，RRF融合，固定top5。原生循环便于检查动作、工具观察和退出边界。依赖及版本见pyproject.toml与constraints-tested.txt。

## 实测限制与实际用时

- 正式失败为TEST11、TEST18、TEST21、TEST25；稳定性另有3次失败。引用支持率99.04%，无依据事实率0.48%，保留3个关键缺陷场景标记及其原判理由。通过案例不代表其他输入无错误。
- 正式题库自早期版本起已用于返修，当前是已曝光题库的回归结果，不包装成未见测试。
- PDF只证明资料所载条文，不证明制度目前仍有效；不联网补充制度。数据提取的程序/AI检查不等于全文人工逐字校对。
- 项目主要实施日期为2026-10-30至2026-10-31。用户本人明确“未计时”；未虚构个人工时或声称3小时完成。可审计的问答用量和运行时间见examples/submission/time-record.json。
- 代码、资料处理和文档主要由Codex完成；用户负责选题、资料、范围、校准反馈与验收，详见AI使用记录。剩余改进不纳入本轮已接受范围。

未通过场景的具体问题、实际回答和判定原因见[失败案例说明](docs/FAILED-CASES.md)。百分比用于结果展示，样本数量与原始分子、分母保留在评测记录中；未更改评分口径。
