# 步骤九：可复现GitHub交付

## 目标与完成判据

同一仓库提供题目三要求的代码、数据、五份文档、真实示例、可执行测试、安装运行步骤、依赖和配置模板；检查密钥/隐私排除；新环境复现；最后提交并验证远端SHA。用户在2026-10-31已明确授权直接提交推送。

## 已完成的准备和验证

1. 51组56轮复核清单获用户“通过”确认，按同意现有AI判定入库。步骤八完成依据包含用户接受数值差距，保留原14/20门槛结果及失败。
2. README与docs/SUBMISSION.md提供评审入口、准确当前状态、全部必验收点映射和剩余限制；AI使用不虚构个人编码贡献，个人实际工时明确“未计时”。
3. examples/submission/整理六类实际成功示例，复制件SHA与原记录一致；完整40+40+30运行及全部138轮评分也保留，不删失败。
4. 新增显式OFFLINE MOCK入口，三个确定性场景全部完成；无API调用，仅验证读取、引用和上限，不计模型性能。
5. 新增同题资料可见性变化测试：只显示D19时有据回答，同时显示D19与D20时补查并待确认。真实12个模型请求，结果单独保留，不改变正式分母。
6. 新虚拟环境与无.env的隔离副本安装成功，pip check通过；使用已下载的相同模型文件重建向量索引，未复用索引。完整程序61/61、离线流程、CLI帮助和检索检查通过。
7. 首次复现发现完整测试依赖索引而README顺序不对，中止未完成调用并修正为先建索引；保留该次日志和bootstrap-correction.json，没有修改问答算法或补造通过记录。
8. 交付检查确认要求文件、六类真实证据、56轮复核覆盖、源码数据哈希、离线边界、无密钥和无超大文件。原冻结清单中的5个egg-info文件是安装生成元数据，跨目录检查明确排除；其余受控文件逐项核对，原冻结清单不重写。
9. 账户余额原始响应仅本地保留，Git忽略；公开只提交HTTP状态脱敏摘要。.env、模型缓存和工作目录不提交。代码和日志扫描未检出真实密钥或模型内部推理正文。原制度中机构联系字段按来源保留，未添加私人记录。
10. GitHub仓库已检查为公开，main远端与本地起点一致。本机已有xiao2wei登录凭据，仓库启用credential manager后推送dry-run成功；未要求用户在聊天提供GitHub令牌。

## 证据

- examples/submission/reproduction/summary.json、program-tests.json：新环境步骤与结果。
- examples/submission/evidence-change/summary.json：新增真实行为验证。
- examples/submission/submission-check.json：离线交付检查。
- examples/submission/time-record.json：实际程序时长和个人未计时说明。
- evaluation/human-review-v4-confirmation.json：实际人工确认及交付授权来源。

本文件随交付提交保存。最终commit SHA使用git rev-parse HEAD获取，远端用git ls-remote origin refs/heads/main核对；推送成功与最终SHA在对话交付记录中提供，不在提交内容中伪造自引用SHA。未新增界面、部署或多Agent服务。

本次隔离复现成功步骤耗时合计：256.693秒（不含中止的首次测试等待，不等于人工工时）。新增资料变化验证：12个真实模型请求、56322 tokens。

## 按用户反馈补充百分比与可读问答

将主要展示改为Agent任务通过率90%、基础RAG任务通过率85%、稳定性通过率90%；原始分子、分母、判分和冻结数据不变。新增docs/LATEST-TEST-RESULTS.md、两份对照/稳定性可读报告及FAILED-CASES.md，展示全部138轮真实一问一答、引用、动作与失败原因。生成命令为python scripts/render_last_round.py；校验见examples/submission/readable-report-audit.json。此轮仅离线整理，DeepSeek请求为0。

## 后续内容口径与PDF名称更新

用户进一步要求只将内容错误标失败，将符合PDF但依据未给全的答案判正确并说明。本次新统计独立保存，旧严格评分不覆盖；当前正确处理率Agent100.00%、基础RAG92.50%、稳定性100.00%，基础RAG3组工具未完成单列。全部138轮问答仍逐字展示，PDF按封面更名且哈希不变；新增DeepSeek请求0，68项程序测试通过。详见[步骤十](10-content-policy-and-pdf-name.md)。
