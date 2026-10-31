# 步骤六：建立可复核的AI评测

当前状态：待外部条件——实际人工校准标签。其余本步实现、公式验证和开发集评分验证已完成；不得越过人工标签门槛进入步骤七。

## 目标

把真实回答和Trace转成可复算的19项指标；校验计算公式并验证独立AI裁判。步骤一约定需要至少12个人工确认标签，不能由Codex代替真人签字。

## 已完成

- 程序检查：引用存在、实际读取、原文匹配、终态、工具预算、轮数上限；所有批量子调用和错误尝试计数。
- 独立AI评分：回答/决策使用deepseek-flash，评审使用deepseek-v4-pro，独立上下文及固定judge.txt；逐个答案要点和原子事实评分，不只给总分。
- 19项指标、逐组结果、六类统计、原子事实明细、分子分母、N/A、端到端时间和调用数；评分器请求单列，不计入问答成本。
- 7项手算公式测试；累计34/34程序测试通过，见examples/step06/program-tests.json及test-results.txt。
- 12个初始校准样本真实评分与建议标签一致12/12，6个错误均未放行。发现条件合取误判后新增CAL13/CAL14，修正提示后14/14与建议一致，错误样本未放行。
- 最终有效校准采用Pro思考模式，calibration-v4为14/14建议标签一致，尚未获人工标签。
- 校准输入明确标为人为构造的评测夹具，不冒充真实Agent运行；评分器调用是真实DeepSeek。
- 人工标签导入脚本scripts/record_human_labels.py要求实际审核人、确认时间和来源；未得到确认不会填human_label。

## 完成门槛状态

|门槛|当前|证据|
|---|---|---|
|真实独立AI评审|已运行|examples/step06/*scores*/、calibration-v2/|
|计算公式全通过|已完成|34/34累计测试，其中7项指标测试|
|至少12个人工标签|未完成|evaluation/calibration.json的human_label仍为null|
|人工标签一致率≥90%且严重错误不误放|待人工标签；当前仅14/14建议标签一致|calibration-v2/summary.json|
|一条命令生成明细/分类/报告|已实现|policy_agent.evaluation score|
|开发集验证与争议处理|修正EVAL-001后完整重新评分及程序复算已结束，见agent-scores-v6与baseline-scores-v6|docs/defects/EVAL-001.md|

## 本步发现的问题

DEV06原评分把仅追问人才层次当作同时追问协议，违反合取条件。已保留旧题库和评分，将判据拆成含义不变的原子项并补充成对校准样本，详见EVAL-001。新旧评分不覆盖。正式40组哈希保持不变，尚未执行正式评测。

初次召回暂为85%，目标90%；最终证据覆盖95%。DEV03首次传入k=8被工具拒绝，随后模型改为5并补查；M01不隐藏该失败。DEV06漏召回D02第十九条协议依据。质量修复属于后续步骤七，只有本步门槛完成后才进入。

## 复现命令

~~~powershell
python -m policy_agent.evaluation calibrate --out examples/step06/new-calibration
python scripts/run_tests.py examples/step06/program-tests.json
python -m policy_agent.evaluation score --dataset evaluation/dev.json --runs examples/step05/agent-dev-v2 --out examples/step06/new-scores
~~~

最后一条命令同时生成逐题真实评分、score-summary.json、report/metrics.json与report/report.md。已有目录禁止覆盖。

人工复核清单：06-human-calibration-review.md，现14项。前6项及CAL14建议通过，CAL07—13建议不通过；所有标签仍待真人核对。此项是评测资料需求，不是逐步骤项目审批。

## 最终本步验证快照

独立裁判：DeepSeek-v4-pro，thinking enabled；回答和动作模型仍为DeepSeek-flash，thinking disabled。最终校准14/14与建议标签一致，错误样本误放0；human_label均为空。

有效报告：examples/step06/agent-report-v6/report.md及baseline-report-v6/report.md。v6仅对v5真实AI响应修正程序定位校验后复算，没有重新生成答案或伪造AI响应。两套各12组、16轮，未决评分0。

|开发指标|Agent|基础RAG|Agent目标|
|---|---|---|---|
|任务通过|10/12|7/12|12/12|
|初次Recall@5|85%|95%|≥90%|
|最终已读证据覆盖|95%|85%|≥95%|
|可回答题正确率|87.5%|62.5%|≥90%|
|引用支持率|100%|约97.83%|100%|
|事实引用覆盖率|100%|100%|100%|
|无依据事实率|0%|0%|0%|
|端到端P95|7.0453秒|3.7677秒|≤120秒|

以上仅开发集AI评分；不等于正式评测或人工复核成绩。缺陷修复路线已记录在docs/PROGRESS.md。步骤七须在本步人工校准完成后执行；达不到开发目标必须返修，不降低阈值。

相关评测器返修见docs/defects/EVAL-001.md至EVAL-004.md。评分超时、早期错误和中止记录完整保留；费用只能估算有usage回包的请求，不能声称完整实际账单。

## 2026-10-31人工确认与完成结论

用户对原12项建议回复“允许”，对CAL13/CAL14及完整建议标签回复“同意”。已按对话确认录入evaluation/human-labels-20261031.json，保留原话与确认边界；没有声称用户另行逐字审阅PDF。人工确认标签一致14/14，误放0，见calibration-v4/human-confirmed-summary.json。步骤六原定全部门槛完成。用户新增AC18/M20纳入后续开发回归与正式评测，原指标不降低。自动进入步骤七。

## 本轮追加评审返修状态（2026-10-31）

原14项实际人工确认与14/14有效校准继续保留。后续正式评测发现EVAL-005行为规则/元数据解释问题，已修复并添加CAL15/16；两项新标签仍待实际用户反馈。calibration-v6中12项获得有效评分，CAL13—16因真实HTTP402未完成，不能将负例调用失败误算判对；正确摘要为summary-corrected.json，EVAL-006已增加保护。当前步骤六返修验证待余额及标签，不声称新评审版本已达标。
