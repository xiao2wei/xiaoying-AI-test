# Vue 3 问答页面使用说明

这是一页本地问答工作台，按用户确认的第三版样式实现。Vue 负责会话、回答、原文和执行记录的展示；Python HTTP 服务直接调用现有的 `policy_agent.agent.agent()`。真实问答仍使用原来的 DeepSeek、混合检索和引用校验。

## 首次安装与运行

已验证 Windows、Python 3.13.13、Node.js 24.11.1、Chrome。Python 3.11+；Node.js 要求20.19+的20系列或22.12及以上（以package.json的engines为准）。其他操作系统没有做同等实机复现。

先按[README](../README.md)创建Python虚拟环境、安装依赖。然后在仓库根目录执行：

~~~powershell
# 仅首次复制；已有.env请直接编辑，保留现有配置。
Copy-Item .env.example .env
# 在.env中填写自己的DEEPSEEK_API_KEY，不要提交或填写到前端文件里。

# 首次构建检索索引；会下载本地嵌入模型，不调用DeepSeek。
.venv\Scripts\python -m policy_agent.cli build-index

cd frontend
npm ci
npm run build
cd ..

.venv\Scripts\python -m policy_agent.webapp
~~~

打开 **http://127.0.0.1:8000**。保持Python终端运行；Ctrl+C停止服务。启动服务、打开页面和点击示例问题均不调用DeepSeek，只有发送问题才执行Agent。

默认只监听本机127.0.0.1；端口被占用或被Windows保留时，可用 `--port 8080`，并访问对应端口。此次Windows的8765端口被系统拒绝，因此选择8000；无需关闭VPN或修改防火墙。

前端锁定Vue3.5.44、Vite7.3.7、@vitejs/plugin-vue6.0.10，版本见[package.json](../frontend/package.json)和package-lock.json。使用Vue单文件组件和Vite构建，参考[Vue官方快速开始](https://vuejs.org/guide/quick-start.html)与[Vite指南](https://vite.dev/guide/)。没有新增Python服务框架或另一套Agent。

## 怎么使用

1. 输入问题，点击“发送”或按Enter。Shift+Enter换行；中文输入法选字时不会触发发送。
2. 本轮完成后直接继续追问。服务端把前面的实际问答传给同一个Agent；客户端不能上传伪造的助手消息。
3. 点击回答后的引用数字或“查看原文”，展开真实引用，查看制度ID、条款、版本日期、PDF页码与印刷页码。点击“在PDF中查看”打开对应原始PDF页面。
4. 展开“查看执行过程”，查看模型选择的search/read/finish、简要决策理由、工具参数和返回摘要，以及真实调用次数和耗时。过程在本轮结束后展示，当前没有逐Token或逐工具实时推送。
5. “复制回答”复制完整原始回答；“记录”下载当前轮的公开运行记录。此下载不含密钥、请求头或模型内部推理正文。
6. “新建对话”开始独立上下文。左侧“最近对话”可切换；手机上通过左上角菜单访问。示例只填入输入框，不自动发送。

资料不足或需要确认时，页面显示具体缺口及需要补充的材料。工具失败、达到上限或模型服务错误均保留未完成状态，不显示成成功回答。

## 会话、限额与费用

- 每个Web对话最多8轮，每轮最多12轮模型决策、10次工具尝试。HTTP重试与最终核对会计入实际模型请求次数，因此“决策轮数”不等于HTTP请求次数。
- CLI批处理原有“整组共享12轮/10工具预算”的规则不变。Web为了交互式连续追问采用**每轮预算**，属于入口层配置差异；旧正式评测并未在Web预算下重跑。
- 同一服务一次只执行一个问答任务，防止重复并发消费。每次发送带唯一请求ID，相同ID不会执行第二遍；双击发送也只创建一个任务。
- 网络中断时先点“恢复查询”，查询原任务。仅在服务确认该ID从未接收时，用户的恢复操作才提交同一个ID；不会自行换ID重跑。刷新页面也只恢复查询。
- 会话保存在服务内存，闲置60分钟过期，最多30段；服务重启后会话消失。浏览器localStorage只保存当前会话ID和未决请求信息，没有模型密钥或完整历史。会话列表由同一本机服务共享，不是多用户权限系统。
- 完成的原始运行日志保存在 `work/web-runs/<会话ID>/<请求ID>.json`，已被Git忽略。删除最近对话不会删除这些文件。对话ID不是认证凭据。
- 实际API费用沿用原 `.env` 模型、预算配置和模型账本。余额不足、Key无效或预算耗尽时明确报错，不回退到Mock。

## 开发模式

需要分别启动两个终端，均从仓库根目录开始：

~~~powershell
# 终端一：Python API
.venv\Scripts\python -m policy_agent.webapp --dev-origin http://127.0.0.1:5173
~~~

~~~powershell
# 终端二：Vue开发服务
cd frontend
npm ci
npm run dev
~~~

浏览器访问 **http://127.0.0.1:5173**，Vite把/api代理到8000。请与--dev-origin保持同样的主机名，不要混用localhost与127.0.0.1。如果修改Python端口，同步修改 `frontend/vite.config.js` 的proxy目标。正式本地展示推荐前面的build方式，只需一个Python服务。

## 测试与真实截图

~~~powershell
# 根目录：程序测试，不调用DeepSeek；需要已有检索索引。
.venv\Scripts\python scripts/run_tests.py work/web-program-tests.json

# 前端：真实浏览器运行确定性接口夹具，不调用DeepSeek。
cd frontend
npm ci
npm run build
npm test
~~~

Playwright在Windows默认使用已安装的Chrome。其他安装位置可设置环境变量 `PLAYWRIGHT_CHROMIUM_EXECUTABLE`；非Windows也可执行 `npx playwright install chromium` 安装测试浏览器。

[Web验证记录](steps/12-vue-web-ui.md)区分程序测试和真实两轮问答；[实际问答与截图说明](../examples/submission/web-ui/README.md)可直接阅读。截图来自运行中的Vue页面及本次真实DeepSeek输出，没有将预览样式、历史答案或测试夹具当成实时结果。

`frontend/scripts/real-smoke.mjs` 是本次两轮真实验证与截图脚本，**会付费调用模型**，不在npm test中执行。仓库已有real-smoke.json时脚本拒绝重复运行、拒绝覆盖证据。若确需新实验，应先使用独立副本和新的证据目录，不能为了重拍图片重复付费提问；已完成会话可直接重新打开截图。截图中途失败时，可在确认原会话仍在服务内存后，使用 --resume-web-session继续，脚本会核对原问题而不重发已完成轮次。另有capture-existing.mjs仅读取已完成会话重拍，主动阻断所有POST请求；不要通过重新提问来换截图。

## 常见问题

|现象|处理方式|
|---|---|
|提示前端文件不存在|在frontend执行npm ci与npm run build，再打开页面。|
|知识库未就绪|先运行policy_agent.cli build-index；首次需要下载嵌入模型。|
|未配置密钥|在根目录.env配置DEEPSEEK_API_KEY，重启Python服务。|
|HTTP402或预算耗尽|检查账户余额或本地预算设置，处理后重启；不会自动再跑已失败轮次。|
|无法连接本地服务|确认终端仍运行；待网络恢复点击“恢复查询”，不要反复新建任务。|
|对话不存在或已过期|新建对话；旧上下文不会被悄悄重造。|
|无法复制|浏览器禁止剪贴板时可手动选中；本地localhost通常允许。|
|移动端打开方式|使用桌面浏览器的设备模拟查看窄屏；默认服务不监听局域网，手机不能通过电脑IP直接访问。|

这是本机评审演示入口，没有账户登录、跨用户数据隔离或公网部署。已有Host/Origin/CSRF检查、固定资源目录和纯文本渲染用于保护本地入口；不能把它直接当作面向公网的服务。正式部署需要单独设计鉴权、数据持久化和并发运行方案。
