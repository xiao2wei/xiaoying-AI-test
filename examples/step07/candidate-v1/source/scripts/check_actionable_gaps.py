from policy_agent.evaluation import judge_turn
from policy_agent.common import save
cases=[('vague',False,'资料没有操作步骤，请自行查资料补充。'),('specific',True,'资料没有操作步骤。请提供VPN所属系统或登录入口、使用者身份（教职工或学生），以及该系统的官方密码重置指南或账号服务说明（含发布日期），以便核对操作流程。')]
rows=[]
for name,expected,text in cases:
 gold={'question':'学校VPN忘记密码后如何重置？','expected_status':'insufficient_evidence','required_points':['说明资料没有操作步骤'],'evidence':[]}
 result={'output':{'status':'insufficient_evidence','claims':[],'gaps':[text]},'trace':[]}
 r=judge_turn(gold,result);r.update(case=name,expected_pass=expected,reference_basis='2026-10-31用户明确要求：不能只让用户自行查资料，应具体说明需要额外提供什么',fixture_type='constructed_judge_rule_test_not_agent_performance',matches_reference=r['pass']==expected)
 save('examples/step07/actionable-gap-'+name+'.json',r);rows.append(r);print(name,r['pass'],r['judge_error'],flush=True)
save('examples/step07/actionable-gap-check.json',{'count':len(rows),'matched':sum(r['matches_reference'] for r in rows),'human_sample_labels_claimed':False})
