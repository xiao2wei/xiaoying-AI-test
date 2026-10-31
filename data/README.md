# 数据来源与使用边界

唯一知识来源为用户提供的[《辽宁科技大学制度汇编（2023版第四卷）人事人才篇》](source/辽宁科技大学制度汇编（2023版第四卷）人事人才篇.pdf)，229页、29份制度、562个片段、61张表格。名称按PDF封面逐字核对；封面编印日期为2024年3月，编者为辽宁科技大学党政办公室。SHA-256见processed/manifest.json。

2026-10-31按用户要求，将仓库原名personnel-policies.pdf及桌面乱码原件改为上述真实名称；PDF字节不变，SHA-256为28b2d518c7e9347883640ee0614503bdc3e3039ff01c2c4d7a2bfcb38be41d3e。旧冻结清单保留当时路径，由[evaluation/source-path-migration.json](../evaluation/source-path-migration.json)记录迁移，交付检查验证同一文件。

这里使用实际制度汇编，不将它称为合成FAQ或本项目原创制度。合成测试问题、参考要点、工具故障配置位于evaluation/；正式答案不进入知识库。原资料的著作权归原权利人，本项目未对其另行授予开源许可。仅用来演示题目要求的文档问答与证据追溯，不证明制度现在仍有效。

processed/可用python scripts/prepare_corpus.py重建。每个片段保留文档ID、日期（未知为null）、条款和PDF/印刷页码。表格、跨页与异常检查见quality-report.json和docs/steps/02-knowledge-base.md。

data/cache/是下载模型与向量索引，未提交；运行build-index重建。资料中出现的联系方式属于制度中的机构公开联系字段，未加入真实员工、人事档案、身份证或手机号样本。
