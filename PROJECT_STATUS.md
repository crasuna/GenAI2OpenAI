# 正式开发交接

项目目录：D:/love_luke/GenAI反代
维护仓库：https://github.com/crasuna/GenAI2OpenAI
上游：https://github.com/ShanghaitechGeekPie/GenAI2OpenAI
基线提交：68f98a962a828e6bbd424da446834a6da6db6b85

## 运行

启动：start_local.cmd（只运行一个实例）
验证：verify_live.cmd（优先读取已忽略的 credentials.txt，缺失时隐藏输入）；批量普通文本验证：verify_models.cmd
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
- verify_live.py：检验普通 JSON 与 SSE（包括 [DONE]）；与 verify_models.py 共用本机凭据读取器，不将 Token 写入报告。
- 迁移前本人账号真实普通和流式测试都返回 API_OK，记录见 live-verification.json。迁移后若仅做离线检查，不代表再次验证了学校会话。
- 当前 7 个文本模型均有普通调用成功证据；Kimi 另通过流式和多轮测试。未验证图片、工具调用、Responses、长上下文及推理强度控制。历史 deepseek-v3:671b 曾返回未找到模型，已从当前目录移除。
- Token 已曾出现在聊天中，建议更换，新 Token 不要写入源码、提交或聊天。

## 开发入口

按 main.py 中 chat_completions → get_request_access_token → resolve_model → stream_genai_events → stream_chat_completions_response 阅读。
README.md 是上游文档；本文件和学习与运行说明.md 是本机交接资料。
保留上游 .git 历史；origin 指向 crasuna/GenAI2OpenAI，upstream 指向原作者仓库。现有本机运行修复和回归检查作为本 Fork 的初始维护提交。
旧临时目录保留为备份。后续代码和测试以本目录为准。

## Codex 工作目录

在 Codex 侧栏添加本地项目并选择此文件夹。添加项目不会自动迁移已有聊天的文件权限；若把此聊天移动到项目后仍提示旧工作目录，应在该项目内开始聊天，并让它先读取本文件。
Git 仓库不包含旧聊天记录或会话凭据；用户选择保存在本机的 credentials.txt 已被忽略。

## 模型目录更新（2026-10-28）

依据用户提供的学校目录响应（8 条、1 页），更新 7 个文本模型映射；1 个图像模型仅文档登记。保留 deepseek-pro 调用名，移除旧模型的静态列举；未知模型仍可透传。快照与历史说明见 docs/模型列表.md。本次没有重新验证模型调用或思考参数。

## 本次逐模型测试与凭据选择

2026-10-28 本机逐个进行了 7 次普通文本调用：gpt-6.1-sol、gpt-6-astra、gpt-6-luna、glm-5.3-flash、qwen-3.8、deepseek-pro 均返回 API_OK；kimi-k3 返回 HTTP 500，上游报 message content cannot be empty。本次未验证流式或工具调用，也未修复 Kimi 请求兼容问题。详细结果仅在本机 logs/model-verification.json。

用户明确选择将凭据保存在 Git 忽略的 credentials.txt；两个验证脚本自动读取，服务端仍要求客户端携带凭据。此前文档的“不保存 Token”不再适用于这个用户选择的本机配置。

## Kimi 修复与复测（2026-10-28，晚于上述首次测试）

首次失败源于请求中 chatInfo 为空，而 Kimi 上游将其追加为一条空用户消息。现已针对 Kimi-k3 将最后一条用户消息放入 chatInfo，其余消息作为 messages 历史发送，避免空消息和重复当前问题。其他模型的请求组装方式保持不变。

本地服务已重启。kimi-k3 的普通文本（API_OK）、流式（API_OK 且包含 [DONE]）、多轮历史回忆（BLUE_742）三项真实请求均通过，结果在本机 logs/kimi-verification.json。此前批量报告保留为修复前证据。未验证工具调用、图片或长上下文。

## DSH Desktop 接入（2026-10-28）

本机 DSH NEXT 已配置自定义供应商 shanghaitech-local，协议 OpenAI Chat Completions，地址 http://127.0.0.1:5057/v1，模型 deepseek-pro，显示名称“学校 DeepSeek-V4.1-Flash”。实际在客户端收到“学校 DeepSeek 连接成功。”。DSH 设置和凭据保存在该应用自己的用户目录，不纳入本仓库。

使用前需启动本机反代；反代未运行时 DSH 会报 Connection error。此次仅验证文字回复，不代表 Agent 工具调用或推理强度控制已接通。
