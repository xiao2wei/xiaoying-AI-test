# 六类真实运行与评审入口

以下均为candidate-v4正式集中的既有真实DeepSeek输出；按能力展示，不代表全部40组都成功。整套失败也保存在原目录。每个JSON含输入、实际输出、完整工具观察、后续模型动作及简要决策依据。

|验收点|场景|真实问答与Trace|完整评分|
|---|---|---|---|
|明确答案|TEST02|[TEST02.json](TEST02.json)|[逐轮评分](../step08/v4/score-completion-r1/agent-scores/TEST02.json)|
|文档冲突|TEST13|[TEST13.json](TEST13.json)|[逐轮评分](../step08/v4/score-completion-r1/agent-scores/TEST13.json)|
|资料外问题|TEST19|[TEST19.json](TEST19.json)|[逐轮评分](../step08/v4/score-completion-r1/agent-scores/TEST19.json)|
|相似问题|TEST26|[TEST26.json](TEST26.json)|[逐轮评分](../step08/v4/score-completion-r1/agent-scores/TEST26.json)|
|上下文追问|TEST31|[TEST31.json](TEST31.json)|[逐轮评分](../step08/v4/score-completion-r1/agent-scores/TEST31.json)|
|工具失败|TEST36|[TEST36.json](TEST36.json)|[逐轮评分](../step08/v4/score-completion-r1/agent-scores/TEST36.json)|

## 能体现动态决策的路径

- TEST02：检索并读取具体病假表格，得到所需条件后结束。
- TEST13：检索命中15日和20日两种规定，读取双方后继续检索衔接/废止及解释部门，再补读附则；依据不足时返回needs_confirmation和具体缺口。
- TEST19：首轮候选不支持Wi-Fi问题，模型改写查询，仍无依据时返回insufficient_evidence并说明需要官方接入材料。
- TEST36：第一次search明确返回临时故障；下一次search由真实模型重新选择，成功后read并回答。决策Trace与HTTP自动重试分开记录。

## 同题资料变化检查

[两次真实运行的结果](evidence-change/summary.json)：同一个护理假问题，只显示D19时有据回答；显示D19与D20时读取双方并请求确认。仅切换同一PDF里的可见制度，没有伪造原文，也未将此结果并入40组分母。详见[single_policy](evidence-change/single_policy.json)与[both_policies](evidence-change/both_policies.json)。

## 执行上限与离线流程

[TEST40](../step08/v4/agent-runs/TEST40.json)保留真实受限退出；完整程序测试覆盖批量读取、失败尝试和轮数限制。offline-mock/仅为明确标注的确定性流程演示，包含正常、资料不足、持续故障；不算真实模型效果。

## 其余结果和人工记录

完整输入题库见evaluation/formal.json；40组Agent、40组基准、30次稳定性均在examples/step08/v4/。当前有效评分位于score-completion-r1/；用户确认后的相同分数与复核元数据位于human-reviewed-r1/。旧版本、原始网络失败和复核前清单均为历史证据，不冒充当前状态。

所有程序验证、实际运行、评分与人工确认分开记录；无模型内部推理正文。
