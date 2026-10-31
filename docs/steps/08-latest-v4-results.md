# v4评分补齐前的过程记录

本页记录早期暂停点的运行覆盖和网络问题，不展示中间通过率。最后一轮完整结果见[最终结果](08-v4-completed-results.md)，真实问答见[总报告](../LATEST-TEST-RESULTS.md)。

当时40组基准、40组Agent和30次稳定性问答均已运行，共138轮待评审；其中82轮已有有效评分，55轮因SSL连接问题未决，1轮因定位校验未决。这些是评分环节问题，不能据此判断问答是否正确。后续已按原记录补齐评分，未重新生成答案。

原始过程数据保留在examples/step08/v4及score-completion-r1，用于核查调用、断网、修复和补评过程。

## 已完成的前置验证

- 唯一PDF：229页，29份制度，562个条款片段，61张表格。
- 完整开发v16：12/12，所有适用指标通过；不是正式成绩。
- 人工确认校准标签：16个；评分器一致16/16，最近复测复用完全相同真实评分，无新增校准请求。
- 程序检查：61/61。
- 当前正式测试属于已曝光题库回归，不是独立未见测试。

## 结果位置与复算

项目：E:/xiaoying/AItest。冻结清单：examples/step07/candidate-v4/manifest.json。

- 原始问答：examples/step08/v4/baseline-runs、agent-runs、stability-runs。
- 原始评分：同版本baseline-scores、agent-scores、stability-scores。
- 全量指标：同版本agent-report/metrics.json与baseline-report/metrics.json。
- 评分完整性：同版本evaluation-completeness.json。
- 六类真实执行路径：同版本acceptance-paths.md。

只做本地重算、不发送模型请求：

~~~powershell
cd E:\xiaoying\AItest
python scripts/formal_pipeline.py --version v4 --phase report
~~~

上述为补评前的过程记录。后续评分已补完、人工确认已完成；此页保留数据位置和实际用量，最终通过率见[最终结果](08-v4-completed-results.md)。
## 本轮已记录用量（不是服务账单）

只统计v4，不含之前返修、开发和校准：

|阶段|记录的请求尝试|收到usage的响应|服务报告tokens|
|---|---:|---:|---:|
|真实问答|448|448|1,857,805|
|独立评分|195|85|596,034|

评分另有5轮按完全相同输入复用历史真实评分，没有重复调用。评分请求尝试包含106次SSL错误；缺少usage的请求不在tokens中补造数值，也不据此推定实际收费为0。