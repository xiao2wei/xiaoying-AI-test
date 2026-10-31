# 数据来源与使用边界

唯一知识来源为用户指定的辽宁科技大学《制度汇编·人事人才篇》PDF，原件副本在source/personnel-policies.pdf；229页、29份制度、562个片段、61张表格。SHA-256见processed/manifest.json。

这里使用实际制度汇编，不将它称为合成FAQ或本项目原创制度。合成测试问题、参考要点、工具故障配置位于evaluation/；正式答案不进入知识库。原资料的著作权归原权利人，本项目未对其另行授予开源许可。仅用来演示题目要求的文档问答与证据追溯，不证明制度现在仍有效。

processed/可用python scripts/prepare_corpus.py重建。每个片段保留文档ID、日期（未知为null）、条款和PDF/印刷页码。表格、跨页与异常检查见quality-report.json和docs/steps/02-knowledge-base.md。

data/cache/是下载模型与向量索引，未提交；运行build-index重建。资料中出现的联系方式属于制度中的机构公开联系字段，未加入真实员工、人事档案、身份证或手机号样本。
