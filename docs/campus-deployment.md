# 校园版运行、存储与部署

## 本地运行

在仓库根目录安装 requirements.txt 后执行 `python run_demo.py`，浏览器打开 `http://127.0.0.1:8080/`。需同时保留三个后台进程和前端进程。当前修改的独立验收预览使用23080端口及单独的数据目录，不复用旧工厂项目数据。

## 云部署

使用本仓库根目录 Dockerfile，启动命令为 `python run_cloud.py`，公开HTTP端口由 PORT 指定，默认10000，健康检查 `/health`。三个内部API只监听容器回环地址，前端经同源 `/api/*` 访问。

必要设置：DEMO_MODE=1、DEMO_WORKSPACES_REQUIRED=1。FACTORY_ANALYSIS_DEMO=1 可开启带明确来源标记的后台模拟。云端永久保存账号和业务记录需配置 DATABASE_URL 指向持久PostgreSQL，或将 DATA_DIR 挂载到持久磁盘。不能将免费容器临时文件系统当作永久存储。

DeepSeek 官方接口采用 https://api.deepseek.com/chat/completions，非思考模式及 JSON 分类。自由输入先分类，匹配模板后仅由本机后台查询及模板回答；不匹配则发送当前问题生成回答，不发送后台观测、人员位置、工单或历史模板回复。快捷按钮不调用模型。官方文档：https://api-docs.deepseek.com/zh-cn/

AI设置：WORKFLOW_MODEL_ENABLED=1、WORKFLOW_MODEL_PROVIDER=deepseek、WORKFLOW_MODEL_NAME=deepseek-flash、WORKFLOW_MODEL_BASE_URL=https://api.deepseek.com、WORKFLOW_RESPONSE_POLICY=classified-template、WORKFLOW_TEMPLATE_FIRST=1。模型密钥仅在平台后台密钥变量 DEEPSEEK_API_KEY 或 WORKFLOW_MODEL_API_KEY 中配置。禁止放到网页、Git、截图或材料中。没有模型配置时模板核查仍可运行，自由问答须检查实际服务状态。

render.yaml 为本校园仓库的新服务示例，服务名 zju-campus-safety-agent；它不代表已创建服务。其他Docker平台使用相同镜像与端口设置。原工厂Render网址不是本版本的验收入口。

## 发布验收顺序

1. 固定源码提交，分别备份SQLite、账号、分析库、演示空间索引与云PostgreSQL；检查备份可恢复。
2. 在新项目创建服务，使用新数据库或经过核对的迁移副本；旧环境保持不变。
3. 验证首页、GIS、三后台健康状态、立即登录及角色切换。
4. 核对“B05状态”与“B05故障影响”的不同答案、引用及模型来源。自由输入由模型分类后走本地模板，快捷按钮直接走模板且不调用模型。
5. 实操草案、确认、维修处理、另一账号复核；验证越权、自审、重复确认及过期观测。
6. 重启服务，读回同编号的工单及操作履历；记录结果后才发布网址。
7. 更新作品介绍和访问说明中的公网入口，保留本地启动与录像作为演示备用。

## 流量与备份

模拟采样和历史帧会持续写入数据库。免费部署前检查后台I/O和对外数据库流量，优先同区域数据库；监控额度，空闲时停止演示采样。SQLite迁移至PostgreSQL需显式转换与逐项核对，不能仅改 DATABASE_URL 后假设旧记录自动出现。Windows DPAPI本地配置依赖原Windows账号，Linux云端需重新设置后台密钥。

## Vercel 容器部署

使用 Container 应用预设与根目录 `Dockerfile.vercel`，不是静态网站导出。项目环境变量必须设置 `PORT=10000`（供 Vercel 路由使用）、`DATABASE_URL`（持久 PostgreSQL）和后台专用 `DEEPSEEK_API_KEY`。保持密钥仅供服务端使用，禁止使用公开前缀。数据库连接使用 TLS。

该镜像启用 `REQUIRE_DURABLE_STORAGE=1`：没有外部数据库时拒绝启动，避免误把临时目录作为永久存储。`/tmp/campus-data` 仅提供容器工作路径，账号、核查、工单和演示空间记录由 PostgreSQL 保存。原本地 SQLite 不会自动迁移，应为校园版创建独立数据库。

`REQUEST_DRIVEN_DEMO=1` 关闭常驻模拟采样任务，每次读取工厂状态时推进模拟并记录观测；运动时间使用跨实例可共享的时钟。工厂状态在操作前刷新，通过事务级数据库锁串行化跨容器读写。手动开启的采样开关是容器内状态，回收后需重新开启。空闲期间不持续采样，历史记录不承诺连续覆盖无人访问的时间段。

2026-10-21 本地适配检查：后台 275 项与 47 项子测试、前端 69 项通过。这些结果不代替容器构建、真实 PostgreSQL、多实例及重启恢复的公网验收。Hobby 有资源额度，Container Runtime 为测试版；应同时保留本地运行与录像备用。官方运行文档：https://vercel.com/docs/functions/runtimes/container
