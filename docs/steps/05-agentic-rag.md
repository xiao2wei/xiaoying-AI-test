# 步骤五：真实Agent决策循环

状态：本步骤目标已完成，进入步骤六；尚未宣称开发集质量指标或正式指标达标。

## 完成检查

|目标|实际证据|结果|
|---|---|---|
|模型决定动作后观察并调整|examples/step05/dynamic-paths.json及agent-dev-v2完整Trace|通过|
|六类至少各一组真实路径|DEV01、03、05、07、09、11；另DEV12持续失败停止|通过|
|补查和异常路径|DEV03继续检索附则；DEV11原文临时失败后重试；DEV12停止|通过|
|默认12轮、10工具，批量子调用计数|tests/test_agent.py；真实1轮上限examples/step05/real-limit.json|通过|
|引用存在、读取、状态、故障程序检查|累计19/19测试|examples/step05/test-results.txt|
|真实模型与单元夹具分离|真实记录含API响应ID、usage；tests中的ScriptedClient只验证边界|通过|

## 技术实现

原生Python循环，以JSON声明search、read、finish动作；每轮动作均来自真实DeepSeek，未按问题ID预设路径。search候选不算原文读取；read保留已成功片段及表格。引用校验不通过时把具体错误返回模型，由模型重新决定。对模型与工具设置硬上限，错误也计数。会话使用上轮实际输出，标准答案不进入上下文。工具预算在同组多个轮次间累计。

## 失败与修复

第一版DEV09第二轮已读到正确原文，但模型输出普通答案对象，之后多次省略finish.result，最终到达轮数上限。根因为基础回答提示与动作提示的输出说明冲突，错误反馈又只给invalid_schema。已将回答规范明确为finish.result内部结构，并在反馈中提供完整字段示例。v1保留，v2完整12组回归所有终态符合预期；质量分由后续独立评测决定。

DEV11基础RAG引用未读片段被拦截；Agent观察临时读取错误后重新读取，成功后再回答。程序没有自动重试业务工具，重试决定由模型作出。模型HTTP传输重试属于基础设施恢复，不用来冒充Agent动态决策。

## 运行

~~~powershell
python -m policy_agent.cli ask "教职工考勤统计表每月25日还是26日报？" --mode agent
python -m policy_agent.cli batch --mode agent --out examples/step05/new-run
python -m unittest discover -s tests -v
~~~

所有实现与原文核对由Codex完成；用户尚未人工评分。离线Mock运行入口按用户后续真实接入要求不提供，缺key明确失败；确定性单元测试夹具不得算作性能或真实路径证据。
