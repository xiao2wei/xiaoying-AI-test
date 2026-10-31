# 步骤四：基础RAG

状态：目标已完成，进入步骤五。

## 目标与实现

固定检索一次，读取5个候选，再调用真实DeepSeek生成答案。采用中文BGE-small-zh-v1.5的真实512维向量和中文双字词BM25，RRF20融合。562个原文片段细分为1138个向量窗口，避免512-token模型截断长条款；窗口映射回完整原文片段，表格由读取工具补全。没有向量数据库服务依赖。

模型为deepseek-flash，禁用思考模式，temperature=0，JSON输出；保存API响应ID、实际返回模型、usage、调用耗时、提示哈希和可见回答，不记录模型内部思维。依赖配置在pyproject.toml。

## 完成检查

|检查|目标|实际|证据|
|---|---|---|---|
|真实API和正常RAG|可用|正常答案及3条精确引用|examples/step04/smoke.json|
|开发组完整运行|12/12|12/12，含全部16个问答轮次|examples/step04/baseline-dev-v1/|
|程序验证|全部通过|14/14累计测试|examples/step04/test-results.txt|
|批处理失败保留|不丢结果|DEV11校验失败保留；其他组继续运行|DEV11.json、batch-summary.json|
|索引可重建|明确命令及指纹|1138×512真实向量，建库45.12秒|data/cache/index/manifest.json|

基准并未宣称达到最终性能阈值。DEV11在首个原文读取故障后仍引用未读取片段，被程序拦截为validation_failed；固定链路不恢复，作为后续Agent对照保留。

## 运行

~~~powershell
python -m pip install -e .
python -m policy_agent.cli build-index
python -m policy_agent.cli ask "人才科研建设专项经费项目最长多久？" --mode baseline
python -m policy_agent.cli batch --mode baseline --out examples/step04/new-run
python -m unittest discover -s tests -v
~~~

.env保存真实key且已忽略提交；.env.example只含占位符。默认模型费用预算10美元；按官方峰值、全部输入缓存未命中的价格计算保守上限，实际账单可能更低，不能把估算写成实际收费。全部usage保存在examples/model-usage.jsonl。当前默认单次请求最多两次传输尝试，尝试均计数。

## 依据与限制

[FastEmbed官方模型清单](https://qdrant.github.io/fastembed/examples/Supported_Models/)；[DeepSeek模型与价格](https://api-docs.deepseek.com/quick_start/pricing/)；[JSON输出](https://api-docs.deepseek.com/guides/json_mode/)。核查日期2026-10-30。

中文向量模型在本地执行，DeepSeek生成在API端执行；没有联网补充制度。程序检查引用文字存在不等于语义支持，后续评分器独立判断。当前检查为Codex与程序完成，无人工评分。
