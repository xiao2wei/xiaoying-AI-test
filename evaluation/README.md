# 评测数据

开发集dev.json为12组，正式集formal.json为40组。specifications.json是可追溯的起草来源，build_dataset.py将证据从唯一PDF语料精确绑定。manifest.json固定数据哈希及稳定性场景。

正式答案不得进入问答提示、检索索引或回答逻辑。reference required_points用于独立评分器。每组所有轮次都保留，类别分母以组计。

当前原文核对由Codex和程序完成，human_verified=false；不冒充人工复核。评分器校准与正式评分的人工确认另行记录。
