# 正式开发交接

项目目录：D:/love_luke/GenAI反代
维护仓库：https://github.com/crasuna/GenAI2OpenAI
上游：https://github.com/ShanghaitechGeekPie/GenAI2OpenAI
基线提交：68f98a962a828e6bbd424da446834a6da6db6b85

## 运行

启动：start_local.cmd（只运行一个实例）
验证：verify_live.cmd（本机隐藏输入本人网页 Token）
地址：http://127.0.0.1:5057/v1
模型：deepseek-pro
凭据：客户端 API key 填本人学校网页 Token；不是任意占位字符串。

独立环境：.venv（由 Python 3.12 重建，不复制旧虚拟环境）。
运行依赖锁定：requirements-runtime.lock。
重建环境：使用 Python 3.11+ 执行 python -m venv .venv，再用该环境 pip install -r requirements-runtime.lock。
离线回归：.venv/Scripts/python.exe tests/check_adapter.py。

## 已实现与边界

- main.py：识别 HTTP 200 SSE 内的上游业务错误，避免当成空成功。
- start_local.py：仅监听本机；拒绝无凭据 API 请求和跨来源浏览器请求；校园域名仅在此进程中直连；移除应用层 Connection 头。
- verify_live.py：检验普通 JSON 与 SSE（包括 [DONE]），不保存 Token。
- 迁移前本人账号真实普通和流式测试都返回 API_OK，记录见 live-verification.json。迁移后若仅做离线检查，不代表再次验证了学校会话。
- 未验证图片、工具调用、Responses、其他模型。项目模型表可能过时；deepseek-v3:671b 已实测返回未找到模型。
- Token 已曾出现在聊天中，建议更换，新 Token 不要写入源码、提交或聊天。

## 开发入口

按 main.py 中 chat_completions → get_request_access_token → resolve_model → stream_genai_events → stream_chat_completions_response 阅读。
README.md 是上游文档；本文件和学习与运行说明.md 是本机交接资料。
保留上游 .git 历史；origin 指向 crasuna/GenAI2OpenAI，upstream 指向原作者仓库。现有本机运行修复和回归检查作为本 Fork 的初始维护提交。
旧临时目录保留为备份。后续代码和测试以本目录为准。

## Codex 工作目录

在 Codex 侧栏添加本地项目并选择此文件夹。添加项目不会自动迁移已有聊天的文件权限；若把此聊天移动到项目后仍提示旧工作目录，应在该项目内开始聊天，并让它先读取本文件。
本目录不包含旧聊天记录或会话凭据。
