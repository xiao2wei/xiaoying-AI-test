# 第三题交付与验收对照

题号：**3，企业知识问答Agent**。仓库：https://github.com/xiao2wei/xiaoying-AI-test 。分支main；最终提交SHA用git rev-parse HEAD查询，并在提交说明中提供。

本项目已具备完整提交材料，六类验收能力均有真实记录。当前按用户新要求以内容正确性为主判定，依据展示不足单独注明；工具未完成单列。旧评分、既有人工确认及全部模型原始输出保留，详细变更见[评分口径说明](CONTENT-POLICY.md)。结果只描述这批已曝光题库，不保证所有新输入正确或评审评分。

## 页面演示入口

新增Vue3本地问答页面，直接复用真实DeepSeek Agent，支持多轮、原文引用与实际过程。[启动与使用说明](WEB-UI.md) · [README中的6张实际截图](../README.md#实际运行截图) · [本次两轮真实问答](../examples/submission/web-ui/README.md)。本地地址http://127.0.0.1:8000，须先按说明启动；GitHub本身不托管带密钥的服务。

## 最后一轮可直接阅读的结果

- **[汇总指标与Agent全部真实一问一答](LATEST-TEST-RESULTS.md)**：40组、51轮，含多轮上下文、实际答案、通过状态和原因。
- [基础RAG全部真实一问一答](reports/v4-baseline-qa.md)：40组、51轮。
- [稳定性每次真实一问一答](reports/v4-stability-qa.md)：30次、36轮。
- [原扣分案例的重新分类与依据说明](FAILED-CASES.md)。

这些内容直接从本轮真实运行文件提取，未改写模型回答，原文引用与工具路径可展开。原JSON继续作为溯源材料，不必先读JSON才能理解结果。

## 交付清单

|考核要求|本项目交付|证据入口|
|---|---|---|
|用户、范围、成功标准|教职工人事制度查询；唯一PDF|[需求](01-requirements.md)|
|可运行CLI与配置|克隆、虚拟环境、依赖、建索引、问答、多轮批处理命令|[README](../README.md)、[配置](../.env.example)|
|代码与工具|原生Python；search、read；真实DeepSeek动作|[Agent](../src/policy_agent/agent.py)、[工具](../src/policy_agent/tools.py)|
|回答、ID、原文、缺口、状态|claims/citations、gaps、status、answer，引用附双页码|[正常实际问答](LATEST-TEST-RESULTS.md#test02)|
|动态循环与至少两条路径|直接回答、发现冲突后补查、无资料改写查询、工具错误后重试|[六类路径](../examples/submission/README.md)|
|执行上限|12轮决策、10次工具尝试，失败和每次批量读取均计数|[限额退出的实际问答](LATEST-TEST-RESULTS.md#test40)|
|六个必验收点|TEST02、13、19、26、31、36，均有输入/输出/Trace|[示例目录](../examples/submission/README.md)|
|替换资料后的行为|同一问题切换唯一PDF中的可见制度范围，真实模型输出改变|[扰动结果](../examples/submission/evidence-change/summary.json)|
|可执行测试|83项Python程序测试、8项浏览器测试全部通过；原61项亦有新环境复现|[当前程序测试](../examples/submission/web-ui/program-tests.json)、[浏览器测试](../examples/submission/web-ui/frontend-tests.json)、[原新环境测试](../examples/submission/reproduction/program-tests.json)|
|离线Mock边界|单独演示三条预设流程；不计入任何模型质量分数|[入口](../scripts/demo_offline.py)、[离线结果](../examples/submission/offline-mock/summary.json)|
|资料与版本日期|原PDF、29份制度、562片段、61表；日期未知则明示|[数据说明](../data/README.md)|
|方案、效果、失败和学习|五份要求文档及每步记录|[方案](02-solution.md)、[评估](03-evaluation.md)、[AI使用](04-ai-usage.md)、[复盘](05-retrospective.md)|
|真实AI评测与人工记录|16标签校准；138轮有效评分；51组56轮用户批量确认|[人工覆盖](../examples/step08/v4/human-reviewed-r1/human-review-coverage.json)|
|实际用时|用户个人工时“未计时”；机器运行时长另列|[用时记录](../examples/submission/time-record.json)|
|凭据与隐私|.env、模型缓存和账户余额响应排除；提交文件密钥扫描|[交付检查](../examples/submission/web-ui/submission-check.json)|
|GitHub可读性|公开仓库，无需另加评审账号；提供最终SHA|[仓库](https://github.com/xiao2wei/xiaoying-AI-test)|

## 质量结果与保留限制

- 新口径正确处理率：Agent100.00%，基础RAG92.50%，稳定性100.00%；包含合理缺口说明、追问和预期安全停止。基础RAG另有3组显式故障注入后未完成，不记作回答错误，也不是第三方网络故障。Recall@5仍为95.83%，最终证据覆盖97.14%，P95为18.55秒。
- 逐项内容核对的13组中，10组内容正确、3组工具未完成。Agent 2轮和稳定性2轮保留依据展示提示。引用支持99.04%、无依据事实0.48%和3个关键缺陷标记均保留为旧口径诊断。
- 最终通过率和六类验收结果见[完整结果](steps/08-v4-completed-results.md)。引用与运行质量指标单独报告，不与答案内容正确性混淆。
- 正式题库已用于返修，当前成绩是回归结果。未验证任意新PDF整套自动切分；资料变化测试只改变同一PDF内可见制度。
- 使用用户提供的真实制度汇编而非合成制度；合成测试问题与故障配置清楚标识。不将大学制度当作当前普遍有效政策。

## 可复现性与新增验证

在无项目.env的隔离副本、全新Python虚拟环境中安装实际版本依赖，pip check通过；重新构建向量索引，61项测试通过，CLI、离线Mock和真实检索成功。为避免重新下载相同嵌入模型，复用了已有模型文件并记录SHA-256；未复用向量索引。这个验证不声称测试了首次模型下载的网络可靠性。

首次复现发现原README在构建索引前运行集成测试，已修正安装顺序；失败尝试和修复记录保留。正式问答算法没有更改；本次另增离线内容判断模块。PDF按封面更名，两个构建脚本只替换路径，PDF字节不变，迁移单与逆向哈希核验可查。新证据变化测试共2次真实Agent任务、12个模型请求，单独统计；其余交付核验没有新增DeepSeek请求。

考核不强制界面；本项目另增Vue3本地页面供交互评审。线上部署、多Agent或生产Runtime未实现，不作为本题缺失交付项。提交历史、材料与日志位于同一仓库；最终提交SHA由Git提供，避免在提交内容中写入其自身SHA。

本次新增[内容口径与文件名更新记录](steps/10-content-policy-and-pdf-name.md)，DeepSeek请求为0。全部真实问答逐字保留，新增判断在独立目录；原始PDF现用封面真实名称，见[资料说明](../data/README.md)。

新增[步骤十二：Vue页面接入与验证](steps/12-vue-web-ui.md)。本次Web集成真实模型请求8次，共29,317 tokens；原正式评测文件与冻结Agent逻辑不变。
